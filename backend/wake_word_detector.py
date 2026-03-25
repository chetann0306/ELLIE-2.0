import eel
import speech_recognition as sr
import threading
import time
from datetime import datetime
from backend.config import WAKE_WORDS

class WakeWordDetector:
    """
    Detects wake words and triggers voice assistant activation.
    Wake words: "hey", "hi", "hello", "hey ellie", "hi ellie", "okay ellie"
    """
    
    def __init__(self, wake_words=None, callback=None):
        self.wake_words = wake_words or WAKE_WORDS
        self.callback = callback
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.listener_thread = None
        self.stop_listening = False
        
    def is_wake_word(self, text):
        """
        Check if recognized text contains wake word.
        Returns: (is_wake_word, cleaned_text)
        """
        if not text:
            return False, ""
        
        lowered = text.lower().strip()
        
        for wake_word in self.wake_words:
            if wake_word in lowered:
                # Remove wake word from text
                cleaned = lowered.replace(wake_word, "").strip()
                return True, cleaned
        
        return False, lowered
    
    def listen_for_wake_word(self):
        """
        Continuously listen for wake word in background.
        """
        self.is_listening = True
        self.stop_listening = False
        
        print("🎤 Wake word detector started. Listening for wake words...")
        print(f"Wake words: {', '.join(self.wake_words)}")
        
        try:
            mic = sr.Microphone()
        except Exception as e:
            print(f"Microphone error: {e}")
            return
        
        with mic as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception as e:
                print(f"Ambient noise adjustment error: {e}")
        
        while not self.stop_listening and self.is_listening:
            try:
                with mic as source:
                    try:
                        # Listen with timeout
                        audio = self.recognizer.listen(
                            source, 
                            timeout=5, 
                            phrase_time_limit=5
                        )
                    except sr.WaitTimeoutError:
                        # Timeout is normal, just continue listening
                        continue
                    except Exception as e:
                        print(f"Listen error: {e}")
                        continue
                
                # Recognize speech
                try:
                    recognized_text = self.recognizer.recognize_google(
                        audio, 
                        language="en-US"
                    )
                    print(f"Recognized: {recognized_text}")
                    
                    # Check for wake word
                    is_wake_word, cleaned_text = self.is_wake_word(recognized_text)
                    
                    if is_wake_word:
                        print(f"✅ Wake word '{recognized_text}' detected!")
                        if self.callback:
                            self.callback(cleaned_text)
                
                except sr.UnknownValueError:
                    # Couldn't understand, continue listening
                    pass
                except sr.RequestError as e:
                    print(f"Recognition service error: {e}")
                    # Continue listening despite error
                    continue
                except Exception as e:
                    print(f"Recognition error: {e}")
                    continue
            
            except Exception as e:
                print(f"Error in wake word listener: {e}")
                time.sleep(1)
        
        print("🛑 Wake word detector stopped.")
        self.is_listening = False
    
    def start(self):
        """Start wake word detection in background thread."""
        if self.is_listening:
            print("Wake word detector already running")
            return
        
        self.listener_thread = threading.Thread(
            target=self.listen_for_wake_word,
            daemon=True
        )
        self.listener_thread.start()
        return True
    
    def stop(self):
        """Stop wake word detection."""
        self.stop_listening = True
        self.is_listening = False
        print("Stopping wake word detector...")
    
    def restart(self):
        """Restart wake word detection."""
        self.stop()
        time.sleep(1)
        self.start()


# Global instance
wake_word_detector = None

@eel.expose
def start_wake_word_detection():
    """
    Start wake word detection from frontend.
    Returns: {success: bool, message: str}
    """
    global wake_word_detector
    
    try:
        if wake_word_detector is None:
            from backend.command import takeAllCommands, process_recognized_command
            
            def on_wake_word_detected(text):
                """Callback when wake word is detected."""
                print(f"✅ Wake word callback triggered with: '{text}'")
                try:
                    # Notify frontend
                    eel.ShowSiriWave()()
                    
                    # If there's remaining text after wake word, process it
                    if text and len(text.strip()) > 0:
                        print(f"Processing command: '{text}'")
                        process_recognized_command(text)
                    else:
                        # Just trigger listening
                        print("Listening for command...")
                        takeAllCommands()
                except Exception as e:
                    print(f"Error in wake word callback: {e}")
            
            wake_word_detector = WakeWordDetector(callback=on_wake_word_detected)
        
        if not wake_word_detector.is_listening:
            wake_word_detector.start()
            return {"success": True, "message": "Wake word detection started. Say 'Hey Ellie', 'Hi Ellie', or 'Hello'"}
        else:
            return {"success": False, "message": "Wake word detection already running"}
    
    except Exception as e:
        error_msg = f"Error starting wake word detection: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {"success": False, "error": error_msg}


@eel.expose
def stop_wake_word_detection():
    """
    Stop wake word detection from frontend.
    Returns: {success: bool, message: str}
    """
    global wake_word_detector
    
    try:
        if wake_word_detector and wake_word_detector.is_listening:
            wake_word_detector.stop()
            return {"success": True, "message": "Wake word detection stopped"}
        else:
            return {"success": False, "message": "Wake word detection not running"}
    
    except Exception as e:
        error_msg = f"Error stopping wake word detection: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


@eel.expose
def is_wake_word_running():
    """
    Check if wake word detection is running.
    Returns: {running: bool}
    """
    global wake_word_detector
    
    if wake_word_detector:
        return {"running": wake_word_detector.is_listening}
    return {"running": False}


@eel.expose
def set_wake_words(wake_words_list):
    """
    Update wake words list.
    Example: ["hey", "hi", "hello", "hey ellie", "hi ellie"]
    """
    global wake_word_detector
    
    try:
        if wake_word_detector:
            wake_word_detector.wake_words = wake_words_list
            print(f"Wake words updated to: {wake_words_list}")
            return {"success": True, "message": f"Wake words updated: {', '.join(wake_words_list)}"}
        else:
            # Initialize if not exists
            from backend.command import takeAllCommands, process_recognized_command
            
            def on_wake_word_detected(text):
                try:
                    eel.ShowSiriWave()()
                    if text and len(text.strip()) > 0:
                        process_recognized_command(text)
                    else:
                        takeAllCommands()
                except Exception as e:
                    print(f"Error in callback: {e}")
            
            wake_word_detector = WakeWordDetector(wake_words_list, on_wake_word_detected)
            return {"success": True, "message": f"Wake words set: {', '.join(wake_words_list)}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def get_wake_words():
    """
    Get current wake words list.
    """
    global wake_word_detector
    
    if wake_word_detector:
        return {
            "success": True,
            "wake_words": wake_word_detector.wake_words
        }
    return {
        "success": False,
        "wake_words": WAKE_WORDS
    }