import os
import eel
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.feature import *
from backend.command import *
from backend.audio_system import audio_system
from backend.voice_handler import speak, speak_queued
from backend.wake_word_detector import start_wake_word_detection
from backend.voice_config import voice_config
from backend.reminders import reminder_manager
from backend.wikipedia_browser import *
from backend.gmail_handler import *
from backend.weather_jaipur import *

from backend.news_handler import *

eel.init('frontend')

print("\n" + "="*70)
print("🚀 ELLIE VOICE ASSISTANT STARTING UP")
print("="*70 + "\n")

# Initialize components
print("✅ Audio system initialized")

# Start wake word detection
#try:
#    start_wake_word_detection()
#    print("✅ Wake word detection started")
#except Exception as e:
#    print(f"⚠️ Wake word detection error: {e}")

# Open browser
print("🌐 Opening browser...")
os.system('start msedge.exe --app="http://127.0.0.1:8000/index.html"')

try:
    play_assistant_sound()
except Exception as e:
    print(f"⚠️ Could not play startup sound: {e}")

print("\n" + "="*70)
print("✨ ELLIE IS READY!")
print("🎤 Say 'Hey Ellie' to get started")
print("📝 Or type a command and press Enter")
print("="*70 + "\n")

# Start server
try:
    eel.start('index.html', mode=None, host='localhost', block=True)
except KeyboardInterrupt:
    print("\n👋 Shutting down ELLIE...")
    audio_system.cleanup()
except Exception as e:
    print(f"❌ Error: {e}")
    audio_system.cleanup()