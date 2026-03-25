import os

ASSISTANT_NAME = "ELLIE"
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "iT6DkeK5u1nd92HiZUCU2obwI8RoMJ4f")
MISTRAL_MODEL = "mistral-tiny"

# Audio Settings
CHAT_TEMPERATURE = 0.7
TTS_RATE = 150  # Words per minute (150 is clear)
TTS_VOLUME = 1.0  # 0.0 to 1.0
MAX_RESPONSE_LENGTH = 200  # Characters per chunk

# Wake Word Settings
WAKE_WORDS = ["hey ellie", "hi ellie", "okay ellie", "hey", "hi", "hello"]
WAKE_WORD_SENSITIVITY = 0.8  # 0.0 to 1.0

ASSISTANT_NAME = "ELLIE"
SYSTEM_PASSWORD = "aakriti"