"""
Audio cache to prevent repeated initialization issues.
"""

class AudioCache:
    """Cache and manage audio state."""
    
    def __init__(self):
        self.last_spoken_text = None
        self.last_spoken_time = None
        self.engine_failures = 0
        self.max_failures = 3
    
    def record_speech(self, text):
        """Record that we've spoken this text."""
        import time
        self.last_spoken_text = text
        self.last_spoken_time = time.time()
    
    def record_failure(self):
        """Record an engine failure."""
        self.engine_failures += 1
        print(f"⚠️ Engine failure count: {self.engine_failures}")
    
    def reset_failures(self):
        """Reset failure counter."""
        self.engine_failures = 0
    
    def can_speak(self):
        """Check if we can speak (not too many failures)."""
        return self.engine_failures < self.max_failures
    
    def should_retry(self):
        """Check if we should retry speaking."""
        if not self.last_spoken_time:
            return True
        
        import time
        time_diff = time.time() - self.last_spoken_time
        return time_diff > 1.0  # At least 1 second since last speech


# Global instance
audio_cache = AudioCache()