"""
Improved TTS Manager with better engine lifecycle management.
"""
import pyttsx3
import threading
import time

class TTSManager:
    """Manage TTS engine lifecycle properly."""
    
    def __init__(self):
        self.engine = None
        self.lock = threading.Lock()
        self.is_speaking = False
        self.init_engine()
    
    def init_engine(self):
        """Initialize or reinitialize the TTS engine."""
        try:
            with self.lock:
                # Clean up old engine if exists
                if self.engine:
                    try:
                        self.engine.stop()
                    except:
                        pass
                    self.engine = None
                
                # Create new engine
                self.engine = pyttsx3.init()
                
                # Configure engine
                self.engine.setProperty("rate", 150)
                self.engine.setProperty("volume", 1.0)
                
                # Set female voice
                voices = self.engine.getProperty("voices") or []
                if voices:
                    female_voice = None
                    
                    # Priority: Zira > Victoria > Samantha > Female > Any
                    priority_names = ['zira', 'hazel', 'victoria', 'samantha', 'female', 'woman']
                    
                    for priority_name in priority_names:
                        for voice in voices:
                            if priority_name in voice.name.lower():
                                female_voice = voice
                                break
                        if female_voice:
                            break
                    
                    if female_voice is None and len(voices) > 1:
                        female_voice = voices[1]
                    
                    if female_voice is None:
                        female_voice = voices[0]
                    
                    self.engine.setProperty("voice", female_voice.id)
                    print(f"✅ TTS Engine initialized with: {female_voice.name}")
                
                return True
        except Exception as e:
            print(f"❌ TTS Engine initialization failed: {e}")
            self.engine = None
            return False
    
    def speak(self, text):
        """Speak the text with the engine."""
        if not text or len(text.strip()) < 1:
            return False
        
        try:
            with self.lock:
                if self.engine is None:
                    print("⚠️ Engine is None, reinitializing...")
                    if not self.init_engine():
                        return False
                
                self.is_speaking = True
                print(f"🔊 Speaking: {text}")
                
                self.engine.say(text)
                self.engine.runAndWait()
                
                print("✅ Speech completed")
                return True
                
        except Exception as e:
            print(f"❌ TTS speak error: {e}")
            # Try to reinitialize engine on error
            self.init_engine()
            return False
        finally:
            self.is_speaking = False
    
    def stop(self):
        """Stop speaking."""
        try:
            with self.lock:
                if self.engine:
                    self.engine.stop()
                    self.is_speaking = False
        except:
            pass
    
    def cleanup(self):
        """Clean up resources."""
        try:
            with self.lock:
                if self.engine:
                    self.engine.stop()
                    self.engine = None
        except:
            pass


# Global instance
tts_manager = TTSManager()