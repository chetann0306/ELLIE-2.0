import pyttsx3
import eel

class VoiceConfiguration:
    """
    Manage voice settings for Ellie.
    """
    
    def __init__(self):
        self.engine = pyttsx3.init()
        self.current_voice = "female"
        self.speech_rate = 170
        self.volume = 1.0
        self.available_voices = self._get_available_voices()
        self._set_female_voice()
    
    def _get_available_voices(self):
        """Get list of all available voices."""
        try:
            voices = self.engine.getProperty("voices") or []
            voice_list = []
            
            for voice in voices:
                voice_info = {
                    "id": voice.id,
                    "name": voice.name,
                    "gender": voice.gender if hasattr(voice, 'gender') else "Unknown",
                    "age": voice.age if hasattr(voice, 'age') else "Unknown",
                    "languages": voice.languages if hasattr(voice, 'languages') else ["Unknown"]
                }
                voice_list.append(voice_info)
            
            return voice_list
        except Exception as e:
            print(f"Error getting voices: {e}")
            return []
    
    def _set_female_voice(self):
        """Set female voice as default."""
        try:
            voices = self.engine.getProperty("voices") or []
            
            # First try to find by name
            for voice in voices:
                if 'female' in voice.name.lower() or 'woman' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.engine.setProperty("voice", voice.id)
                    print(f"Set female voice: {voice.name}")
                    return
            
            # If not found by name, use index 1 (usually female on Windows)
            if len(voices) > 1:
                self.engine.setProperty("voice", voices[1].id)
                print(f"Set female voice: {voices[1].name}")
            else:
                print("Only one voice available")
        
        except Exception as e:
            print(f"Error setting female voice: {e}")
    
    def set_voice_by_name(self, voice_name):
        """Set voice by name."""
        try:
            voices = self.engine.getProperty("voices") or []
            
            for voice in voices:
                if voice_name.lower() in voice.name.lower():
                    self.engine.setProperty("voice", voice.id)
                    print(f"Voice set to: {voice.name}")
                    return True
            
            print(f"Voice '{voice_name}' not found")
            return False
        except Exception as e:
            print(f"Error setting voice: {e}")
            return False
    
    def set_speech_rate(self, rate):
        """Set speech rate (speed)."""
        try:
            self.engine.setProperty("rate", rate)
            self.speech_rate = rate
            print(f"Speech rate set to: {rate}")
            return True
        except Exception as e:
            print(f"Error setting speech rate: {e}")
            return False
    
    def set_volume(self, volume):
        """Set volume (0.0 to 1.0)."""
        try:
            if 0.0 <= volume <= 1.0:
                self.engine.setProperty("volume", volume)
                self.volume = volume
                print(f"Volume set to: {volume}")
                return True
            else:
                print("Volume must be between 0.0 and 1.0")
                return False
        except Exception as e:
            print(f"Error setting volume: {e}")
            return False
    
    def speak(self, text, is_async=True):
        """Speak text with current voice settings."""
        try:
            if not text:
                return False
            
            self.engine.say(text)
            
            if is_async:
                self.engine.startLoop(iterations=1, debug=False)
            else:
                self.engine.runAndWait()
            
            return True
        except Exception as e:
            print(f"Error speaking: {e}")
            return False
    
    def speak_async(self, text):
        """Speak text asynchronously."""
        import threading
        thread = threading.Thread(target=self.speak, args=(text, False), daemon=True)
        thread.start()
    
    @eel.expose
    def get_available_voices(self):
        """Get list of available voices for UI."""
        return self.available_voices
    
    @eel.expose
    def get_current_voice(self):
        """Get current voice settings."""
        return {
            "current_voice": self.current_voice,
            "speech_rate": self.speech_rate,
            "volume": self.volume
        }
    
    @eel.expose
    def update_voice_settings(self, voice_name, speech_rate, volume):
        """Update voice settings."""
        results = {
            "voice_changed": self.set_voice_by_name(voice_name),
            "rate_changed": self.set_speech_rate(speech_rate),
            "volume_changed": self.set_volume(volume)
        }
        
        if all(results.values()):
            return {"success": True, "message": "Voice settings updated"}
        else:
            return {"success": False, "message": "Some settings could not be updated"}

# Create global voice configuration instance
voice_config = VoiceConfiguration()