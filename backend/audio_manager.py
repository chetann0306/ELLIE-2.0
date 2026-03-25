import eel
import threading
import time
from queue import Queue

class AudioManager:
    """
    Manage audio queue to prevent overlapping speech.
    Ensures one response finishes before starting the next.
    """
    
    def __init__(self):
        self.audio_queue = Queue()
        self.is_speaking = False
        self.worker_thread = None
        self.stop_worker = False
    
    def queue_speech(self, text, callback=None):
        """
        Queue text to be spoken.
        Returns: job_id
        """
        if not text or len(text.strip()) < 1:
            return None
            
        job_id = int(time.time() * 1000)  # Use timestamp as ID
        self.audio_queue.put({
            'id': job_id,
            'text': text,
            'callback': callback
        })
        print(f"📝 Queued speech (ID: {job_id}): {text[:50]}...")
        return job_id
    
    def process_queue(self):
        """
        Process audio queue in background.
        Ensures only one speech at a time.
        """
        from backend.command import speak
        
        while not self.stop_worker:
            try:
                if not self.audio_queue.empty():
                    job = self.audio_queue.get(timeout=0.5)
                    self.is_speaking = True
                    print(f"🔊 Processing speech (ID: {job['id']})")
                    
                    try:
                        # Speak with run_async=False to wait for completion
                        speak(job['text'], run_async=False)
                        print(f"✅ Speech completed (ID: {job['id']})")
                        
                        if job['callback']:
                            try:
                                job['callback'](True)
                            except:
                                pass
                    except Exception as e:
                        print(f"❌ Error speaking (ID: {job['id']}): {e}")
                        if job['callback']:
                            try:
                                job['callback'](False)
                            except:
                                pass
                    finally:
                        self.is_speaking = False
                        time.sleep(0.2)  # Small delay between speeches
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"❌ Queue error: {e}")
                self.is_speaking = False
                time.sleep(0.1)
    
    def start(self):
        """Start the audio queue worker."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.stop_worker = False
            self.worker_thread = threading.Thread(target=self.process_queue, daemon=True)
            self.worker_thread.start()
            print("✅ Audio manager started")
    
    def stop(self):
        """Stop the audio queue worker."""
        self.stop_worker = True
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
        print("⛔ Audio manager stopped")
    
    def clear_queue(self):
        """Clear all pending audio."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break
        print("🗑️ Audio queue cleared")
    
    @eel.expose
    def get_speaker_status(self):
        """Get current speaker status."""
        return {
            "is_speaking": self.is_speaking,
            "queue_size": self.audio_queue.qsize()
        }


# Global instance
audio_manager = AudioManager()
audio_manager.start()