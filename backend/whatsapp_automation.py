import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class WhatsAppController:
    def __init__(self):
        self.options = Options()
        # IMPORTANT: Replace 'YourUser' with your actual Windows username!
        self.options.add_argument(f"user-data-dir=C:\\Users\\YourUser\\AppData\\Local\\Google\\Chrome\\User Data")
        self.options.add_argument("--profile-directory=Default") 
        self.driver = None

    def start_session(self):
        if not self.driver:
            print("🌐 Booting WhatsApp Web Interface...")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
            self.driver.get("https://web.whatsapp.com")
            # We let WebDriverWait handle the heavy lifting, but give it 5 seconds to initialize
            time.sleep(5) 

    def send_message(self, name, message):
        self.start_session()
        try:
            # Wait up to 30 seconds for the UI to fully load
            wait = WebDriverWait(self.driver, 30) 

            print(f"🔍 Searching for contact: {name}...")
            # 1. Find Search Box (Using resilient fallbacks)
            search_xpath = '//div[@contenteditable="true"][@data-tab="3"] | //div[@title="Search input textbox"]'
            search_box = wait.until(EC.element_to_be_clickable((By.XPATH, search_xpath)))
            search_box.clear()
            search_box.send_keys(name)
            
            # Give WhatsApp 2 seconds to filter the contact list
            time.sleep(2) 
            search_box.send_keys(Keys.ENTER)

            print("⌨️ Typing message...")
            # 2. Find Message Box (Looking specifically inside the chat footer)
            message_xpath = '//*[@id="main"]/footer//div[@contenteditable="true"] | //div[@title="Type a message"]'
            msg_box = wait.until(EC.element_to_be_clickable((By.XPATH, message_xpath)))
            
            # Send message and hit enter
            msg_box.send_keys(message)
            time.sleep(1) # Tiny pause to ensure text renders
            msg_box.send_keys(Keys.ENTER)
            
            print(f"✅ Message successfully sent to {name}")
            return True
            
        except Exception as e:
            print(f"⚠️ WhatsApp Automation Error: {e}")
            return False

    def read_last_message(self):
        self.start_session()
        try:
            wait = WebDriverWait(self.driver, 15)
            # Look for the last message bubble in the active chat
            messages = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "_amky")))
            if messages:
                return messages[-1].text
            return "No messages found."
        except Exception as e:
            print(f"⚠️ Read Error: {e}")
            return "I couldn't read the screen. The chat might be empty."