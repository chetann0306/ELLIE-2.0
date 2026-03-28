import sqlite3
import subprocess
import time
import pyautogui
from urllib.parse import quote
import speech_recognition as sr

DB_PATH = "ellie.db"

def remove_words(input_string, words_to_remove): 
    words = input_string.split()
    filtered_words = [word for word in words if word.lower() not in words_to_remove]
    return ' '.join(filtered_words)

def findContact(query):
    # Strip out trigger words so we are only left with the person's name
    words_to_remove = ['ellie', 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'whatsapp', 'video']
    search_name = remove_words(query, words_to_remove).strip().lower()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Look for the name in the database
        cursor.execute("SELECT Phone FROM contacts WHERE LOWER(name) LIKE ?", ('%' + search_name + '%',))
        results = cursor.fetchall()
        conn.close()

        if len(results) == 0:
            return 0, search_name

        mobile_number_str = str(results[0][0])
        # Add India country code if it's missing
        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str

        return mobile_number_str, search_name
    except Exception as e:
        print(f"Database error: {e}")
        return 0, search_name

def listen_for_message():
    """Temporarily turns on the mic to record the actual message you want to send."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Listening for WhatsApp message payload...")
        r.pause_threshold = 1
        audio = r.listen(source, timeout=8, phrase_time_limit=15)
    try:
        message = r.recognize_google(audio, language='en-US')
        print(f"Captured message: {message}")
        return message
    except Exception as e:
        print(f"Could not understand audio: {e}")
        return None

def send_whatsapp_message(phone, message, name):
    try:
        # Encode the text so it can be passed safely into a URL
        encoded_message = quote(message)
        whatsapp_url = f"whatsapp://send?phone={phone}&text={encoded_message}"
        
        # Open the WhatsApp Desktop App
        full_command = f'start "" "{whatsapp_url}"'
        subprocess.run(full_command, shell=True)
        
        print("Waiting for WhatsApp to load...")
        time.sleep(5) # Wait 5 seconds for the app to open and the chat to load
        
        # Simulate pressing the "Enter" key to send the message
        pyautogui.press('enter')
        
        return f"Message sent successfully to {name}"
    except Exception as e:
        print(f"WhatsApp Error: {e}")
        return f"Failed to send message to {name}."