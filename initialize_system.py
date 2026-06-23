import sqlite3
import os

DB_PATH = "ellie_core.db"

def init_master_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🛠️ Creating unified database: ellie_core.db...")

    # 1. Contacts Table (from your old setup_db.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            name VARCHAR(200), 
            Phone VARCHAR(255), 
            email VARCHAR(255) NULL
        )
    ''')

    # 2. Reminders Table (from your old reminders.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            reminder_time TEXT NOT NULL,
            reminder_date TEXT NOT NULL,
            repeat_type TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            job_id TEXT UNIQUE
        )
    ''')

    # 3. NEW: Security Logs Table (For your presentation upgrade!)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            auth_status TEXT NOT NULL, -- 'SUCCESS' or 'FAILED'
            identified_as TEXT NOT NULL, -- 'chetan', 'unknown', or 'password'
            snapshot_path TEXT NULL -- Path to intruder photo if failed
        )
    ''')

    # Insert test contacts securely
    cursor.execute("SELECT COUNT(*) FROM contacts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO contacts (name, Phone) VALUES ('chaitanya', '+919876543210')")
        cursor.execute("INSERT INTO contacts (name, Phone) VALUES ('boss', '+919876543210')")
        print("✅ Default test contacts inserted.")

    conn.commit()
    conn.close()
    print("✨ Master database ellie_core.db initialized successfully with all tables!")

if __name__ == "__main__":
    init_master_database()