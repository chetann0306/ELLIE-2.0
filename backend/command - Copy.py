import eel
import speech_recognition as sr
import threading
from datetime import datetime
import os
import json
import requests
from backend.config import ASSISTANT_NAME
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

_tts_engine = None
_tts_lock = threading.Lock()


def _init_tts():
    global _tts_engine
    if _tts_engine is not None:
        return _tts_engine
    if pyttsx3 is None:
        return None
    try:
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty("rate", 170)
        voices = _tts_engine.getProperty("voices") or []
        if voices:
            _tts_engine.setProperty("voice", voices[0].id)
    except Exception as e:
        print("TTS init failed:", e)
        _tts_engine = None
    return _tts_engine


def speak(text, run_async=True):
    """Speak the given text using pyttsx3 (if available)."""
    if not text:
        return

    def _do(t):
        try:
            engine = _init_tts()
            if engine is None:
                print("TTS not available. Text:", t)
                return
            with _tts_lock:
                engine.say(t)
                engine.runAndWait()
        except Exception as e:
            print("TTS speak error:", e)

    if run_async:
        threading.Thread(target=_do, args=(text,), daemon=True).start()
    else:
        _do(text)

def ai_chat_response(prompt: str) -> str:
    """
    Local offline Mistral inference using llama_cpp.
    Automatically loads GGUF model once and reuses it.
    """
    import os
    from llama_cpp import Llama
    from backend.config import CHAT_TEMPERATURE

    model_path = os.path.join(os.path.dirname(__file__), "mistral-7b-instruct-v0.1.Q4_K_M.gguf")

    if not os.path.exists(model_path):
        print("Mistral model not found at:", model_path)
        return "My local model is missing. Please place the mistral-7b-instruct-v0.1.Q4_K_M.gguf file in the backend folder."

 
    global local_llm
    if 'local_llm' not in globals():
        print("Loading local Mistral model...")
        local_llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=8,
            n_batch=128,
            verbose=False
        )
        print("Model loaded successfully!")

    try:

        system_prompt = "You are Ellie, a helpful desktop voice assistant. Be concise, short, and friendly."
        messages = f"{system_prompt}\nUser: {prompt}\nEllie:"

        output = local_llm(
            prompt=messages,
            max_tokens=256,
            temperature=CHAT_TEMPERATURE,
            stop=["User:", "ELLIE:", "Ellie:"]
        )

        reply = output["choices"][0]["text"].strip()
        print("🤖 Ellie:", reply)
        return reply if reply else "I'm here, but I didn’t catch that."

    except Exception as e:
        print("💥 Local Mistral error:", e)
        return "I'm having trouble thinking right now."


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


@eel.expose
def takeAllCommands(device_index=None):
    """
    High-level entry used by frontend.
    - Handle date/time
    - Handle open/launch/start (calls backend.feature.openCommand)
    - Otherwise call AI for a conversational reply
    Returns a structured dict with fields:
      success, text, action in {"date","time","opened","failed","chat",None}, reply, target
    """
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

    date_triggers = ("what is the date", "tell me the date", "what's the date", "today's date", "date today", "tell me today's date", "give me the date")
    time_triggers = ("what time is it", "tell me the time", "current time", "time now", "what's the time", "give me the time","what is the time")

    if any(phrase in lowered for phrase in date_triggers) or ("date" in lowered and "time" not in lowered):
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        reply = f"Today's date is {date_str}."
        try:
            speak(reply)
        except Exception:
            pass
        _safely_call_frontend_display(reply)
        _safely_call_frontend_showhood()
        return {"success": True, "text": recognized_text, "action": "date", "reply": reply}

    if any(phrase in lowered for phrase in time_triggers) or ("time" in lowered and "date" not in lowered):
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        reply = f"The time is {time_str}."
        try:
            speak(reply)
        except Exception:
            pass
        _safely_call_frontend_display(reply)
        _safely_call_frontend_showhood()
        return {"success": True, "text": recognized_text, "action": "time", "reply": reply}

    intent_found = any(kw in lowered for kw in ("open ", "launch ", "start "))
    if intent_found:
        try:
            from backend import feature
        except Exception as e:
            print("Failed to import backend.feature:", e)
            reply = "This is not present"
            try:
                speak(reply)
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
                    speak(reply)
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
                    speak(reply)
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
                speak(reply)
            except Exception:
                pass
            _safely_call_frontend_display(reply)
            _safely_call_frontend_showhood()
            return {"success": True, "text": recognized_text, "action": "failed", "target": None, "error": str(e), "reply": reply}

    reply = ai_chat_response(recognized_text)
    try:
        speak(reply)  
    except Exception:
        pass
    _safely_call_frontend_display(reply)
    _safely_call_frontend_showhood()
    return {"success": True, "text": recognized_text, "action": "chat", "reply": reply}
