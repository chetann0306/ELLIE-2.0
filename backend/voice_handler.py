"""
Simple voice handler that uses the audio system.
"""
from backend.audio_system import audio_system
import threading
import time

def speak(text, run_async=True):
    """
    Speak text using the audio system.
    
    Args:
        text: Text to speak
        run_async: If True, queue the speech. If False, wait for completion.
    """
    if not text or len(text.strip()) < 1:
        print("⚠️ Empty text, skipping")
        return False
    
    # Clean text
    text = text.strip()
    
    # Queue the speech
    audio_system.queue_speech(text)
    
    if not run_async:
        # Wait for speech to complete
        max_wait = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = audio_system.get_status()
            if not status['is_speaking'] and status['queue_size'] == 0:
                return True
            time.sleep(0.1)
        
        return True
    
    return True


def speak_queued(text, callback=None):
    """Queue text to be spoken."""
    if not text or len(text.strip()) < 1:
        print("⚠️ Empty text for queued speech")
        return False
    
    text = text.strip()
    result = audio_system.queue_speech(text)
    
    if callback and result:
        # Execute callback in background
        def execute_callback():
            time.sleep(0.5)  # Small delay
            try:
                callback(True)
            except:
                pass
        
        threading.Thread(target=execute_callback, daemon=True).start()
    
    return result