"""
Complete audio system with proper TTS handling.
"""
import pyttsx3
import threading
import time
import queue
import sys

class AudioSystem:
    """
    Robust audio system with proper TTS engine management.
    Handles multiple consecutive speeches without audio issues.
    """
    
    def __init__(self):
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.is_speaking = False
        self.lock = threading.Lock()
        self.engine = None
        self.stop_flag = False
        
        # Start the audio worker
        self.start_worker()
    
    def init_engine(self):
        """Initialize fresh TTS engine."""
        try:
            # Clean up existing engine
            if self.engine:
                try:
                    self.engine.stop()
                    del self.engine
                except:
                    pass
            
            # Create new engine
            self.engine = pyttsx3.init()
            
            # Set properties
            self.engine.setProperty("rate", 150)
            self.engine.setProperty("volume", 1.0)
            
            # Set female voice
            voices = self.engine.getProperty("voices") or []
            if voices:
                female_voice = None
                priority_names = ['zira', 'victoria', 'samantha', 'female', 'woman']
                
                for priority_name in priority_names:
                    for voice in voices:
                        if priority_name in voice.name.lower():
                            female_voice = voice
                            break
                    if female_voice:
                        break
                
                if female_voice is None and len(voices) > 1:
                    female_voice = voices[1]
                elif female_voice is None:
                    female_voice = voices[0]
                
                self.engine.setProperty("voice", female_voice.id)
                print(f"✅ Voice set to: {female_voice.name}")
            
            return True
        except Exception as e:
            print(f"❌ Engine init error: {e}")
            self.engine = None
            return False
    
    def queue_speech(self, text):
        """Queue text for speech."""
        if not text or len(text.strip()) < 1:
            return False
        
        self.speech_queue.put(text)
        print(f"📝 Queued: {text[:50]}...")
        return True
    
    def worker_thread_func(self):
        """Worker thread that processes speech queue."""
        print("🎵 Audio worker thread started")
        
        while not self.stop_flag:
            try:
                # Get from queue with timeout
                try:
                    text = self.speech_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                if text is None:  # Stop signal
                    break
                
                self.is_speaking = True
                print(f"🔊 Speaking: {text}")
                
                try:
                    with self.lock:
                        # Initialize engine if needed
                        if self.engine is None:
                            self.init_engine()
                        
                        if self.engine:
                            self.engine.say(text)
                            self.engine.runAndWait()
                            print("✅ Speech completed")
                
                except Exception as e:
                    print(f"❌ Speech error: {e}")
                    # Reset engine on error
                    self.engine = None
                
                finally:
                    self.is_speaking = False
                    time.sleep(0.5)  # Delay between speeches
                    
            except Exception as e:
                print(f"❌ Worker error: {e}")
                self.is_speaking = False
                time.sleep(0.5)
        
        print("🛑 Audio worker thread stopped")
    
    def start_worker(self):
        """Start the audio worker thread."""
        if not self.is_running:
            self.stop_flag = False
            self.is_running = True
            self.worker_thread = threading.Thread(
                target=self.worker_thread_func,
                daemon=True
            )
            self.worker_thread.start()
            print("✅ Audio system started")
    
    def stop_worker(self):
        """Stop the audio worker thread."""
        self.stop_flag = True
        self.speech_queue.put(None)  # Signal to stop
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
        self.is_running = False
        print("⛔ Audio system stopped")
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_worker()
        try:
            if self.engine:
                self.engine.stop()
                del self.engine
        except:
            pass
        self.engine = None
    
    def get_status(self):
        """Get current status."""
        return {
            "is_running": self.is_running,
            "is_speaking": self.is_speaking,
            "queue_size": self.speech_queue.qsize()
        }


# Global instance
audio_system = AudioSystem()