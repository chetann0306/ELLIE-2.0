import eel
import speech_recognition as sr
import threading
from datetime import datetime, timedelta
import os
import json
import requests
from backend.config import ASSISTANT_NAME, TTS_RATE
import sys
import re
from backend.auth.recoganize import AuthenticateFace
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.wake_word_detector import (
    start_wake_word_detection,
    stop_wake_word_detection,
    is_wake_word_running,
    set_wake_words,
    get_wake_words
)
from backend.response_optimizer import optimize_response, split_long_response
from backend.voice_handler import speak, speak_queued
from backend.audio_system import audio_system

# Import reminder manager
try:
    from backend.reminders import reminder_manager
except Exception as e:
    print(f"Warning: Could not import reminders: {e}")
    reminder_manager = None


def ai_chat_response(prompt: str) -> str:
    """
    Local offline Phi-3 inference using llama_cpp.
    Optimized for audio output and blazing fast speed.
    """
    import os
    from llama_cpp import Llama
    from backend.config import CHAT_TEMPERATURE

    # 1. Point to the new Phi-3 model inside the models folder
    model_path = os.path.join(os.path.dirname(__file__), "models", "Phi-3-mini-4k-instruct-q4_k_m.gguf")

    if not os.path.exists(model_path):
        return "My local model is missing. Please place the Phi-3 file in the backend/models folder."

    global local_llm
    if 'local_llm' not in globals():
        print("🧠 Loading local Phi-3 model...")
        try:
            local_llm = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_gpu_layers=-1,  # CRITICAL: Forces it to use your GPU for instant speed
                n_threads=8,
                n_batch=128,
                verbose=False
            )
            print("✅ Phi-3 Model loaded successfully!")
        except Exception as e:
            print(f"❌ Model loading error: {e}")
            return "My local model failed to load. Please check your system."

    try:
        system_prompt = "You are Ellie, a helpful desktop voice assistant. Be concise, short, and friendly. Use simple language. Don't repeat responses twice."
        
        # 2. Use the strict Phi-3 Prompt Formatting
        messages = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>\n"

        # 3. Generate the response
        output = local_llm(
            prompt=messages,
            max_tokens=75,                 # Keeps it short and punchy so Ellie speaks faster
            temperature=CHAT_TEMPERATURE,
            stop=["<|end|>", "<|user|>"]   # Phi-3 specific stop tags
        )

        reply = output["choices"][0]["text"].strip()
        
        # Optimize response for audio using your existing function
        reply = optimize_response(reply)
        
        print("🤖 Ellie:", reply)
        return reply if reply else "I'm here, but I didn't catch that."

    except Exception as e:
        print(f"❌ Local Phi-3 error: {e}")
        return "I'm having trouble thinking right now. Please try again."
    
@eel.expose
def list_microphones():
    try:
        names = sr.Microphone.list_microphone_names()
        print("Available microphones:", names)
        return names
    except Exception as e:
        print("Error listing microphones:", e)
        return []


def _safely_call_frontend_display(msg):
    try:
        eel.DisplayMessage(msg)()
    except Exception:
        pass


def _safely_call_frontend_showhood():
    try:
        eel.ShowHood()()
    except Exception:
        pass


@eel.expose
def takeCommand(device_index=None):
    """
    Single listen/recognize cycle. Returns dict:
      { success: True, text: "..." } or { success: False, error: "..." }
    """
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True

    try:
        if device_index is not None:
            try:
                di = int(device_index)
            except Exception:
                di = None
            if di is not None:
                mic = sr.Microphone(device_index=di)
            else:
                mic = sr.Microphone()
        else:
            mic = sr.Microphone()
    except Exception as e:
        err = f"Microphone initialization error: {e}"
        print(err)
        return {"success": False, "error": err}

    with mic as source:
        try:
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1.2)
            recognizer.pause_threshold = 0.8
            print("Listening (timeout=8s, phrase_time_limit=8s)...")
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            msg = "No speech detected (timeout)."
            print(msg)
            return {"success": False, "error": msg}
        except Exception as e:
            msg = f"Microphone listening error: {e}"
            print(msg)
            return {"success": False, "error": msg}

    try:
        print("Recognizing...")
        text = recognizer.recognize_google(audio, language="en-US")
        print("Recognized text:", text)
        return {"success": True, "text": text}
    except sr.UnknownValueError:
        msg = "Could not understand audio."
        print(msg)
        return {"success": False, "error": msg}
    except sr.RequestError as e:
        msg = f"Recognition service failed: {e}"
        print(msg)
        return {"success": False, "error": msg}
    except Exception as e:
        msg = f"Unexpected recognition error: {e}"
        print(msg)
        return {"success": False, "error": msg}


def set_reminder_voice(query):
    """Parse voice commands for reminders."""
    if reminder_manager is None:
        return {"success": False, "error": "Reminder system not available"}
    
    lowered = query.lower()
    
    try:
        # Extract time patterns
        time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', lowered)
        minutes_match = re.search(r'in\s+(\d+)\s+minutes?', lowered)
        
        # Extract title/description
        title_match = re.search(r'remind(?:er)?\s+(?:for|about|me\s+about)?\s*(.+?)(?:\s+at\s+\d|\s+in\s+\d|$)', lowered)
        title = title_match.group(1).strip() if title_match else "Reminder"
        
        # Clean up title
        title = title.replace("me about", "").replace("me for", "").strip()
        if not title or title.lower() in ["reminder", "a reminder"]:
            title = "Important Reminder"
        
        time_str = "12:00"
        
        if minutes_match:
            minutes = int(minutes_match.group(1))
            future_time = datetime.now() + timedelta(minutes=minutes)
            time_str = future_time.strftime("%H:%M")
        elif time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3) or ""
            
            if period.lower() == "pm" and hour != 12:
                hour += 12
            elif period.lower() == "am" and hour == 12:
                hour = 0
            
            time_str = f"{hour:02d}:{minute:02d}"
        
        result = reminder_manager.add_reminder(
            title=title,
            time_str=time_str,
            repeat_type="once"
        )
        
        if result['success']:
            message = f"Reminder set: {title} at {time_str}"
            speak_queued(message)
            return {"success": True, "message": message}
        else:
            speak_queued("Failed to set reminder")
            return {"success": False, "error": result['error']}
    
    except Exception as e:
        error_msg = f"Error setting reminder: {str(e)}"
        print(error_msg)
        speak_queued("Could not set reminder")
        return {"success": False, "error": error_msg}


def handle_gmail_command(query):
    """Handle Gmail opening command."""
    try:
        from backend.gmail_handler import open_gmail
        
        result = open_gmail()
        
        if result['success']:
            message = "Opening Gmail in your default browser"
            speak_queued(message)
            return {
                "success": True,
                "action": "gmail",
                "message": message
            }
        else:
            error_msg = result.get('error', 'Could not open Gmail')
            speak_queued(error_msg)
            return {"success": False, "error": error_msg}
    
    except Exception as e:
        error_msg = f"Gmail error: {str(e)}"
        print(error_msg)
        speak_queued("Could not open Gmail")
        return {"success": False, "error": error_msg}


def handle_weather_command(query):
    """Handle weather query."""
    try:
        from backend.weather_jaipur import get_jaipur_weather, get_weather_custom_location
        
        lowered = query.lower()
        
        # Check if asking for specific location
        location_match = re.search(r'weather in\s+(\w+)', lowered)
        
        if location_match:
            location = location_match.group(1).strip()
            result = get_weather_custom_location(location)
        else:
            # Default to Jaipur
            result = get_jaipur_weather()
        
        if result['success']:
            message = result.get('message', 'Could not get weather')
            speak_queued(message)
            return {
                "success": True,
                "action": "weather",
                "temperature": result.get('temperature'),
                "condition": result.get('condition'),
                "location": result.get('location'),
                "message": message
            }
        else:
            error_msg = result.get('error', 'Could not fetch weather')
            speak_queued(error_msg)
            return {"success": False, "error": error_msg}
    
    except Exception as e:
        error_msg = f"Weather error: {str(e)}"
        print(error_msg)
        speak_queued("Could not fetch weather information")
        return {"success": False, "error": error_msg}


def handle_news_command(query):
    """Handle news query and open in Google News."""
    try:
        from backend.news_handler import (
            open_google_news, 
            open_google_news_search, 
            open_google_news_category
        )
        
        lowered = query.lower()
        
        # Check if asking for specific category
        categories = ["world", "business", "technology", "entertainment", "sports", "science", "health"]
        
        category_found = None
        for category in categories:
            if category in lowered:
                category_found = category
                break
        
        # Check if asking for India news
        if "india" in lowered and "india news" in lowered:
            result = open_google_news_search("India news")
            if result['success']:
                message = "Opening Google News search for India news"
                speak_queued(message)
                return {
                    "success": True,
                    "action": "news",
                    "url": result['url'],
                    "message": message
                }
        
        # If specific category found
        elif category_found:
            result = open_google_news_category(category_found)
            if result['success']:
                message = f"Opening Google News - {category_found} section"
                speak_queued(message)
                return {
                    "success": True,
                    "action": "news",
                    "url": result['url'],
                    "message": message
                }
        
        # Check if asking for search
        elif any(phrase in lowered for phrase in ("news about", "news on", "search news")):
            search_term = lowered
            for phrase in ("news about", "news on", "search news"):
                if phrase in search_term:
                    search_term = search_term.split(phrase, 1)[1].strip()
                    break
            
            if search_term and len(search_term) > 2:
                result = open_google_news_search(search_term)
                if result['success']:
                    message = f"Searching Google News for {search_term}"
                    speak_queued(message)
                    return {
                        "success": True,
                        "action": "news",
                        "url": result['url'],
                        "message": message
                    }
        
        # Default: Open Google News home
        result = open_google_news()
        if result['success']:
            message = "Opening Google News"
            speak_queued(message)
            return {
                "success": True,
                "action": "news",
                "message": message
            }
        else:
            error_msg = result.get('error', 'Could not open Google News')
            speak_queued(error_msg)
            return {"success": False, "error": error_msg}
    
    except Exception as e:
        error_msg = f"News error: {str(e)}"
        print(error_msg)
        speak_queued("Could not open news")
        return {"success": False, "error": error_msg}


def handle_wikipedia_browser_command(query):
    """Handle Wikipedia search and open in browser."""
    try:
        from backend.wikipedia_browser import search_and_open_wikipedia
        
        # Extract search term
        search_triggers = ("search wikipedia for", "wikipedia", "search for", "look up", "find on wikipedia")
        search_term = query
        
        for trigger in search_triggers:
            if trigger in query.lower():
                search_term = query.lower().split(trigger, 1)[1].strip()
                break
        
        if not search_term:
            search_term = query
        
        result = search_and_open_wikipedia(search_term)
        
        if result['success']:
            message = f"Opening Wikipedia page for {result['title']}"
            speak_queued(message)
            return {
                "success": True,
                "action": "wikipedia_browser",
                "title": result['title'],
                "url": result['url'],
                "message": message
            }
        else:
            error_msg = result.get('error', 'Could not find Wikipedia page')
            speak_queued(error_msg)
            return {"success": False, "error": error_msg}
    
    except Exception as e:
        error_msg = f"Wikipedia error: {str(e)}"
        print(error_msg)
        speak_queued("Could not search Wikipedia")
        return {"success": False, "error": error_msg}


@eel.expose
def speak_exposed(text, run_async=True):
    """Exposed speak function for frontend."""
    speak(text, run_async)
    return {"success": True}


@eel.expose
def get_speaker_status():
    """Get audio system status."""
    return audio_system.get_status()


@eel.expose
def takeAllCommands(device_index=None):
    """High-level entry used by frontend. Processes all voice commands."""
    res = takeCommand(device_index=device_index)
    print("takeAllCommands result:", res)

    if not res or not isinstance(res, dict):
        return {"success": False, "error": "No response from recognizer"}

    if not res.get("success"):
        return res

    recognized_text = res.get("text", "")
    if not recognized_text:
        return {"success": False, "error": "Empty recognition result"}

    lowered = recognized_text.lower()
    assistant_lower = ASSISTANT_NAME.lower() if ASSISTANT_NAME else ""
    if assistant_lower and assistant_lower in lowered:
        lowered = lowered.replace(assistant_lower, " ").strip()

    # ============== DATE COMMAND ==============
    date_triggers = ("what is the date", "tell me the date", "what's the date", "today's date", "date today", "tell me today's date", "give me the date")
    if any(phrase in lowered for phrase in date_triggers) or ("date" in lowered and "time" not in lowered):
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        reply = f"Today's date is {date_str}."
        try:
            speak_queued(reply)
        except Exception:
            pass
        _safely_call_frontend_display(reply)
        _safely_call_frontend_showhood()
        return {"success": True, "text": recognized_text, "action": "date", "reply": reply}

    # ============== TIME COMMAND ==============
    time_triggers = ("what time is it", "tell me the time", "current time", "time now", "what's the time", "give me the time", "what is the time")
    if any(phrase in lowered for phrase in time_triggers) or ("time" in lowered and "date" not in lowered):
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        reply = f"The time is {time_str}."
        try:
            speak_queued(reply)
        except Exception:
            pass
        _safely_call_frontend_display(reply)
        _safely_call_frontend_showhood()
        return {"success": True, "text": recognized_text, "action": "time", "reply": reply}

    # ============== GMAIL COMMAND ==============
    gmail_triggers = ("open gmail", "check gmail", "check my gmail", "open mail", "gmail")
    if any(phrase in lowered for phrase in gmail_triggers):
        result = handle_gmail_command(recognized_text)
        if result['success']:
            _safely_call_frontend_display(result['message'])
            _safely_call_frontend_showhood()
            return {
                "success": True,
                "text": recognized_text,
                "action": "gmail",
                "reply": result.get('message')
            }

    # ============== WEATHER COMMAND ==============
    weather_triggers = ("weather", "what's the weather", "what is the weather", "tell me the weather", "weather in")
    if any(phrase in lowered for phrase in weather_triggers):
        result = handle_weather_command(recognized_text)
        if result['success']:
            _safely_call_frontend_display(result['message'])
            _safely_call_frontend_showhood()
            return {
                "success": True,
                "text": recognized_text,
                "action": "weather",
                "temperature": result.get('temperature'),
                "condition": result.get('condition'),
                "location": result.get('location'),
                "reply": result.get('message')
            }

    # ============== NEWS COMMAND ==============
    news_triggers = ("tell me the news", "latest news", "news update", "news", "india news")
    if any(phrase in lowered for phrase in news_triggers):
        result = handle_news_command(recognized_text)
        if result['success']:
            _safely_call_frontend_display(f"Found news")
            _safely_call_frontend_showhood()
            return {
                "success": True,
                "text": recognized_text,
                "action": "news",
                "message": result.get('message'),
                "reply": result.get('message')
            }

    # ============== REMINDER COMMAND ==============
    reminder_triggers = ("set reminder", "remind me", "set a reminder", "add reminder")
    if any(phrase in lowered for phrase in reminder_triggers):
        result = set_reminder_voice(recognized_text)
        if result['success']:
            _safely_call_frontend_display(result['message'])
            _safely_call_frontend_showhood()
            return {"success": True, "text": recognized_text, "action": "reminder", "reply": result['message']}
        else:
            error_reply = "Could not set reminder"
            _safely_call_frontend_display(error_reply)
            _safely_call_frontend_showhood()
            return {"success": False, "text": recognized_text, "action": "reminder", "error": result.get('error')}

    # ============== WIKIPEDIA COMMAND ==============
    wikipedia_triggers = ("search wikipedia", "wikipedia", "look up", "find on wikipedia", "search for on wikipedia")
    if any(phrase in lowered for phrase in wikipedia_triggers):
        result = handle_wikipedia_browser_command(recognized_text)
        if result['success']:
            _safely_call_frontend_display(f"Wikipedia: {result['title']}")
            _safely_call_frontend_showhood()
            return {
                "success": True,
                "text": recognized_text,
                "action": "wikipedia_browser",
                "title": result.get('title'),
                "url": result.get('url'),
                "reply": result.get('message')
            }
    elif "send message" in lowered or "whatsapp" in lowered:
        from backend.whatsapp_handler import findContact, listen_for_message, send_whatsapp_message
        
        # 1. Look up the person in the database
        phone, name = findContact(recognized_text)
        
        if phone != 0:
            # 2. Ask what to send
            ask_msg = f"What message should I send to {name}?"
            try:
                speak_queued(ask_msg)
            except:
                pass
            _safely_call_frontend_display(ask_msg)
            
            # 3. Listen for the payload via the handler
            msg_payload = listen_for_message()
            
            if msg_payload:
                try:
                    speak_queued(f"Sending message to {name}...")
                except:
                    pass
                _safely_call_frontend_display(f"Sending message to {name}...")
                
                # 4. Automate WhatsApp
                result = send_whatsapp_message(phone, msg_payload, name)
                try:
                    speak_queued(result)
                except:
                    pass
                _safely_call_frontend_display(result)
                _safely_call_frontend_showhood()
            else:
                try:
                    speak_queued("I didn't catch that. Message cancelled.")
                except:
                    pass
                _safely_call_frontend_display("Message cancelled.")
        else:
            try:
                speak_queued(f"Sorry, I couldn't find {name} in your contacts.")
            except:
                pass
            _safely_call_frontend_display("Contact not found.")

    # ============== CAMERA / VISION COMMANDS ==============
    vision_triggers = ("what is in front of me", "what do you see", "what's in front of me")
    if any(phrase in lowered for phrase in vision_triggers):
        from backend.vision_handler import detect_objects
        
        reply_start = "Let me take a look..."
        try:
            speak_queued(reply_start)
        except Exception:
            pass
        _safely_call_frontend_display(reply_start)
        
        vision_result = detect_objects()
        
        try:
            speak_queued(vision_result)
        except Exception:
            pass
        _safely_call_frontend_display(vision_result)
        _safely_call_frontend_showhood()
        
        return {
            "success": True, 
            "text": recognized_text, 
            "action": "vision_objects", 
            "reply": vision_result
        }

    face_triggers = ("who am i", "recognize me")
    if any(phrase in lowered for phrase in face_triggers):
        from backend.vision_handler import recognize_face
        
        reply_start = "Scanning faces..."
        try:
            speak_queued(reply_start)
        except Exception:
            pass
        _safely_call_frontend_display(reply_start)
        
        face_result = recognize_face()
        
        try:
            speak_queued(face_result)
        except Exception:
            pass
        _safely_call_frontend_display(face_result)
        _safely_call_frontend_showhood()
        
        return {
            "success": True, 
            "text": recognized_text, 
            "action": "vision_faces", 
            "reply": face_result
        }

    # ============== OPEN/LAUNCH COMMAND ==============
    intent_found = any(kw in lowered for kw in ("open ", "launch ", "start "))
    if intent_found:
        try:
            from backend import feature
        except Exception as e:
            print("Failed to import backend.feature:", e)
            reply = "This is not present"
            try:
                speak_queued(reply)
            except Exception:
                pass
            _safely_call_frontend_display(reply)
            _safely_call_frontend_showhood()
            return {"success": True, "text": recognized_text, "action": "failed", "target": None, "error": "internal import error"}

        try:
            open_result = feature.openCommand(recognized_text)
            if not isinstance(open_result, dict):
                open_result = {"status": "failed", "target": None, "error": "feature.openCommand returned non-dict"}

            if open_result.get("status") == "opened" and open_result.get("target"):
                reply = f"Opening {open_result.get('target')}"
                try:
                    speak_queued(reply)
                except Exception:
                    pass
                _safely_call_frontend_display(reply)
                _safely_call_frontend_showhood()
                return {
                    "success": True,
                    "text": recognized_text,
                    "action": "opened",
                    "target": open_result.get("target"),
                    "reply": reply
                }
            else:
                reply = "This is not present"
                try:
                    speak_queued(reply)
                except Exception:
                    pass
                _safely_call_frontend_display(reply)
                _safely_call_frontend_showhood()
                return {
                    "success": True,
                    "text": recognized_text,
                    "action": "failed",
                    "target": open_result.get("target"),
                    "error": open_result.get("error", ""),
                    "reply": reply
                }
        except Exception as e:
            print("Error calling feature.openCommand:", e)
            reply = "This is not present"
            try:
                speak_queued(reply)
            except Exception:
                pass
            _safely_call_frontend_display(reply)
            _safely_call_frontend_showhood()
            return {"success": True, "text": recognized_text, "action": "failed", "target": None, "error": str(e), "reply": reply}

    # ============== DEFAULT: AI CHAT RESPONSE ==============
    reply = ai_chat_response(recognized_text)
    try:
        speak_queued(reply)  
    except Exception:
        pass
    _safely_call_frontend_display(reply)
    _safely_call_frontend_showhood()
    return {"success": True, "text": recognized_text, "action": "chat", "reply": reply}

@eel.expose
def process_recognized_command(recognized_text):
    """Process a recognized command text from wake word detector."""
    try:
        if not recognized_text or len(recognized_text.strip()) < 1:
            return {"success": False, "error": "Empty input"}
        
        recognized_text = recognized_text.strip()
        lowered = recognized_text.lower()
        assistant_lower = ASSISTANT_NAME.lower() if ASSISTANT_NAME else ""
        
        if assistant_lower and assistant_lower in lowered:
            lowered = lowered.replace(assistant_lower, " ").strip()

        print(f"\n{'='*60}")
        print(f"🔍 PROCESSING COMMAND: '{recognized_text}'")
        print(f"{'='*60}\n")

        # ============== DATE COMMAND ==============
        date_triggers = ("what is the date", "tell me the date", "what's the date", "today's date", "date today", "tell me today's date", "give me the date")
        if any(phrase in lowered for phrase in date_triggers) or ("date" in lowered and "time" not in lowered):
            now = datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            reply = f"Today's date is {date_str}."
            try:
                speak_queued(reply)
            except Exception:
                pass
            _safely_call_frontend_display(reply)
            _safely_call_frontend_showhood()
            return {"success": True, "text": recognized_text, "action": "date", "reply": reply}

        # ============== TIME COMMAND ==============
        time_triggers = ("what time is it", "tell me the time", "current time", "time now", "what's the time", "give me the time", "what is the time")
        if any(phrase in lowered for phrase in time_triggers) or ("time" in lowered and "date" not in lowered):
            now = datetime.now()
            time_str = now.strftime("%I:%M %p").lstrip("0")
            reply = f"The time is {time_str}."
            try:
                speak_queued(reply)
            except Exception:
                pass
            _safely_call_frontend_display(reply)
            _safely_call_frontend_showhood()
            return {"success": True, "text": recognized_text, "action": "time", "reply": reply}

        # ============== GMAIL COMMAND ==============
        gmail_triggers = ("open gmail", "check gmail", "check my gmail", "open mail", "gmail")
        if any(phrase in lowered for phrase in gmail_triggers):
            result = handle_gmail_command(recognized_text)
            if result['success']:
                _safely_call_frontend_display(result['message'])
                _safely_call_frontend_showhood()
                return {
                    "success": True,
                    "text": recognized_text,
                    "action": "gmail",
                    "reply": result.get('message')
                }

        # ============== WEATHER COMMAND ==============
        weather_triggers = ("weather", "what's the weather", "what is the weather", "tell me the weather", "weather in")
        if any(phrase in lowered for phrase in weather_triggers):
            result = handle_weather_command(recognized_text)
            if result['success']:
                _safely_call_frontend_display(result['message'])
                _safely_call_frontend_showhood()
                return {
                    "success": True,
                    "text": recognized_text,
                    "action": "weather",
                    "temperature": result.get('temperature'),
                    "condition": result.get('condition'),
                    "location": result.get('location'),
                    "reply": result.get('message')
                }

        # ============== NEWS COMMAND ==============
        news_triggers = ("tell me the news", "latest news", "news update", "news", "india news")
        if any(phrase in lowered for phrase in news_triggers):
            result = handle_news_command(recognized_text)
            if result['success']:
                _safely_call_frontend_display(f"Found news")
                _safely_call_frontend_showhood()
                return {
                    "success": True,
                    "text": recognized_text,
                    "action": "news",
                    "message": result.get('message'),
                    "reply": result.get('message')
                }

        # ============== REMINDER COMMAND ==============
        reminder_triggers = ("set reminder", "remind me", "set a reminder", "add reminder")
        if any(phrase in lowered for phrase in reminder_triggers):
            result = set_reminder_voice(recognized_text)
            if result['success']:
                _safely_call_frontend_display(result['message'])
                _safely_call_frontend_showhood()
                return {"success": True, "text": recognized_text, "action": "reminder", "reply": result['message']}
            else:
                error_reply = "Could not set reminder"
                _safely_call_frontend_display(error_reply)
                _safely_call_frontend_showhood()
                return {"success": False, "text": recognized_text, "action": "reminder", "error": result.get('error')}

        # ============== WIKIPEDIA COMMAND ==============
        wikipedia_triggers = ("what is", "tell me about", "search wikipedia", "wikipedia", "search for")
        if any(phrase in lowered for phrase in wikipedia_triggers):
            result = handle_wikipedia_browser_command(recognized_text)
            if result['success']:
                _safely_call_frontend_display(f"Wikipedia: {result['title']}")
                _safely_call_frontend_showhood()
                return {
                    "success": True,
                    "text": recognized_text,
                    "action": "wikipedia_browser",
                    "title": result.get('title'),
                    "url": result.get('url'),
                    "reply": result.get('message')
                }

        # ============== OPEN/LAUNCH COMMAND ==============
        intent_found = any(kw in lowered for kw in ("open ", "launch ", "start "))
        if intent_found:
            try:
                from backend import feature
            except Exception as e:
                print("Failed to import backend.feature:", e)
                reply = "This is not present"
                try:
                    speak_queued(reply)
                except Exception:
                    pass
                _safely_call_frontend_display(reply)
                _safely_call_frontend_showhood()
                return {"success": True, "text": recognized_text, "action": "failed", "target": None, "error": "internal import error"}

            try:
                open_result = feature.openCommand(recognized_text)
                if not isinstance(open_result, dict):
                    open_result = {"status": "failed", "target": None, "error": "feature.openCommand returned non-dict"}

                if open_result.get("status") == "opened" and open_result.get("target"):
                    reply = f"Opening {open_result.get('target')}"
                    try:
                        speak_queued(reply)
                    except Exception:
                        pass
                    _safely_call_frontend_display(reply)
                    _safely_call_frontend_showhood()
                    return {
                        "success": True,
                        "text": recognized_text,
                        "action": "opened",
                        "target": open_result.get("target"),
                        "reply": reply
                    }
                else:
                    reply = "This is not present"
                    try:
                        speak_queued(reply)
                    except Exception:
                        pass
                    _safely_call_frontend_display(reply)
                    _safely_call_frontend_showhood()
                    return {
                        "success": True,
                        "text": recognized_text,
                        "action": "failed",
                        "target": open_result.get("target"),
                        "error": open_result.get("error", ""),
                        "reply": reply
                    }
            except Exception as e:
                print("Error calling feature.openCommand:", e)
                reply = "This is not present"
                try:
                    speak_queued(reply)
                except Exception:
                    pass
                _safely_call_frontend_display(reply)
                _safely_call_frontend_showhood()
                return {"success": True, "text": recognized_text, "action": "failed", "target": None, "error": str(e), "reply": reply}

        # ============== DEFAULT: AI CHAT RESPONSE ==============
        print(f"🤖 Processing as AI chat: '{recognized_text}'")
        reply = ai_chat_response(recognized_text)
        try:
            speak_queued(reply)  
        except Exception as e:
            print(f"⚠️ Error speaking: {e}")
        _safely_call_frontend_display(reply)
        _safely_call_frontend_showhood()
        return {"success": True, "text": recognized_text, "action": "chat", "reply": reply}

    except Exception as e:
        error_msg = f"Error processing command: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": error_msg}


@eel.expose
def wake_listener():
    """Start the wake word detection listener."""
    try:
        result = start_wake_word_detection()
        if result['success']:
            print("Wake word listener activated")
            return result
        else:
            print(f"Wake word listener error: {result.get('message')}")
            return result
    except Exception as e:
        error_msg = f"Wake listener error: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}
    
    # Add this import at the top with the others in backend/command.py
from backend.config import SYSTEM_PASSWORD

# ... (rest of your command.py code) ...

# Add this at the very bottom of backend/command.py
@eel.expose
def verify_password(input_password):
    try:
        # Import right inside the function to avoid circular import errors
        from backend.config import SYSTEM_PASSWORD 
        
        # Convert both to lowercase and remove hidden spaces
        clean_input = str(input_password).strip().lower()
        clean_system = str(SYSTEM_PASSWORD).strip().lower()
        
        if clean_input == clean_system:
            print("✅ Password verified successfully")
            return True
        else:
            print(f"❌ Password mismatch. Expected: '{clean_system}', Got: '{clean_input}'")
            return False
            
    except Exception as e:
        print(f"⚠️ Password verification error: {e}")
        return False

@eel.expose
def verify_face():
    print("📷 Initializing camera for Face Recognition...")
    try:
        # This calls your script. It will open a cv2 window and return 1 if matched.
        result = AuthenticateFace() 
        
        if result == 1:
            print("🔓 Face Match: System Unlocked!")
            return True
        else:
            print("🔒 Face not recognized or camera window closed.")
            return False
            
    except Exception as e:
        print(f"❌ Face auth error: {e}")
        return False    