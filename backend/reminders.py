import sqlite3
import json
import os
from datetime import datetime, timedelta
import threading
import eel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "reminders.db")

def init_db():
    """Initialize the reminders database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
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
    conn.commit()
    conn.close()

class ReminderManager:
    def __init__(self):
        init_db()
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self._load_active_reminders()
    
    def _load_active_reminders(self):
        """Load all active reminders from database and schedule them."""
        reminders = self.get_all_reminders()
        for reminder in reminders:
            if reminder['is_active']:
                self._schedule_reminder(reminder)
    
    def _schedule_reminder(self, reminder):
        """Schedule a reminder using APScheduler."""
        try:
            job_id = f"reminder_{reminder['id']}"
            remind_time = reminder['reminder_time']
            repeat_type = reminder.get('repeat_type', 'once')
            
            hour, minute = map(int, remind_time.split(':'))
            
            if repeat_type == 'once':
                # One-time reminder
                trigger = CronTrigger(hour=hour, minute=minute)
            elif repeat_type == 'daily':
                trigger = CronTrigger(hour=hour, minute=minute)
            elif repeat_type == 'weekly':
                trigger = CronTrigger(hour=hour, minute=minute, day_of_week='0-6')
            else:
                return
            
            self.scheduler.add_job(
                self._trigger_reminder,
                trigger=trigger,
                args=[reminder],
                id=job_id,
                replace_existing=True
            )
            print(f"Scheduled reminder: {reminder['title']}")
        except Exception as e:
            print(f"Error scheduling reminder: {e}")
    
    def _trigger_reminder(self, reminder):
        """Called when reminder time is reached."""
        try:
            message = f"Reminder: {reminder['title']}"
            if reminder.get('description'):
                message += f". {reminder['description']}"
            
            # Send to frontend
            try:
                eel.DisplayReminderNotification(message)()
            except Exception:
                pass
            
            # Speak the reminder
            try:
                from backend.command import speak
                speak(message, run_async=True)
            except Exception:
                pass
            
            print(f"Reminder triggered: {message}")
        except Exception as e:
            print(f"Error triggering reminder: {e}")
    
    @eel.expose
    def add_reminder(self, title, description="", time_str="12:00", date_str=None, repeat_type="once"):
        """Add a new reminder."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            created_at = datetime.now().isoformat()
            job_id = f"reminder_{int(datetime.now().timestamp())}"
            
            c.execute('''
                INSERT INTO reminders (title, description, reminder_time, reminder_date, repeat_type, is_active, created_at, job_id)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ''', (title, description, time_str, date_str or datetime.now().strftime("%Y-%m-%d"), repeat_type, created_at, job_id))
            
            conn.commit()
            reminder_id = c.lastrowid
            conn.close()
            
            # Schedule it
            reminder = self.get_reminder(reminder_id)
            self._schedule_reminder(reminder)
            
            return {"success": True, "id": reminder_id, "message": f"Reminder '{title}' set for {time_str}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @eel.expose
    def get_all_reminders(self):
        """Get all reminders."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT * FROM reminders ORDER BY reminder_time ASC')
            columns = [desc[0] for desc in c.description]
            reminders = [dict(zip(columns, row)) for row in c.fetchall()]
            conn.close()
            return reminders
        except Exception as e:
            print(f"Error fetching reminders: {e}")
            return []
    
    @eel.expose
    def get_reminder(self, reminder_id):
        """Get a specific reminder."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT * FROM reminders WHERE id = ?', (reminder_id,))
            columns = [desc[0] for desc in c.description]
            row = c.fetchone()
            conn.close()
            return dict(zip(columns, row)) if row else None
        except Exception as e:
            print(f"Error fetching reminder: {e}")
            return None
    
    @eel.expose
    def delete_reminder(self, reminder_id):
        """Delete a reminder."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
            conn.commit()
            conn.close()
            
            # Remove from scheduler
            job_id = f"reminder_{reminder_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            return {"success": True, "message": "Reminder deleted"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @eel.expose
    def snooze_reminder(self, reminder_id, minutes=5):
        """Snooze a reminder for N minutes."""
        try:
            reminder = self.get_reminder(reminder_id)
            current_time = datetime.now()
            snooze_time = current_time + timedelta(minutes=minutes)
            
            new_time = snooze_time.strftime("%H:%M")
            new_date = snooze_time.strftime("%Y-%m-%d")
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                UPDATE reminders 
                SET reminder_time = ?, reminder_date = ?
                WHERE id = ?
            ''', (new_time, new_date, reminder_id))
            conn.commit()
            conn.close()
            
            # Reschedule
            updated_reminder = self.get_reminder(reminder_id)
            self._schedule_reminder(updated_reminder)
            
            return {"success": True, "message": f"Reminder snoozed for {minutes} minutes"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Initialize reminder manager
reminder_manager = ReminderManager()