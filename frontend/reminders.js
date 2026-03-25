$(document).ready(function () {
  // Set default time to current time
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  $('#reminderTime').val(`${hours}:${minutes}`);

  // Form submission
  $('#reminderForm').on('submit', function (e) {
    e.preventDefault();
    
    const title = $('#reminderTitle').val().trim();
    const description = $('#reminderDesc').val().trim();
    const time = $('#reminderTime').val();
    const repeat = $('#reminderRepeat').val();
    
    if (!title) {
      alert('Please enter a reminder title');
      return;
    }
    
    if (typeof eel !== "undefined" && eel.add_reminder) {
      try {
        eel.add_reminder(title, description, time, null, repeat)(function (result) {
          if (result.success) {
            setSiriMessage(`Reminder set: ${title} at ${time}`);
            closeReminderModal();
            loadReminders();
            
            // Speak confirmation
            if ('speechSynthesis' in window) {
              const u = new SpeechSynthesisUtterance(`Reminder set for ${title} at ${time}`);
              window.speechSynthesis.cancel();
              window.speechSynthesis.speak(u);
            }
          } else {
            alert('Error: ' + result.error);
          }
        });
      } catch (err) {
        console.error("Error setting reminder:", err);
      }
    } else {
      alert("Reminder backend not available");
    }
  });

  // Load reminders on page load
  loadReminders();
  setInterval(loadReminders, 60000); // Refresh every minute
});

function openReminderModal() {
  $('#reminderModal').show();
  $('#reminderTitle').focus();
}

function closeReminderModal() {
  $('#reminderModal').hide();
  $('#reminderForm')[0].reset();
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  $('#reminderTime').val(`${hours}:${minutes}`);
}

function toggleRemindersList() {
  $('#remindersList').toggle();
  if ($('#remindersList').is(':visible')) {
    loadReminders();
  }
}

function loadReminders() {
  if (typeof eel === "undefined" || !eel.get_all_reminders) {
    return;
  }
  
  try {
    eel.get_all_reminders()(function (reminders) {
      const active = reminders.filter(r => r.is_active);
      const content = $('#remindersListContent');
      content.empty();
      
      if (active.length === 0) {
        content.html('<p style="color: #999;">No active reminders</p>');
        return;
      }
      
      active.forEach(reminder => {
        const reminderEl = $(`
          <div style="background-color: #222; padding: 10px; margin-bottom: 10px; border-radius: 5px; border-left: 3px solid #1e90ff;">
            <div>
              <strong style="color: #1e90ff;">${reminder.title}</strong>
              <br><small style="color: #aaa;">${reminder.reminder_time} ${reminder.repeat_type !== 'once' ? '(' + reminder.repeat_type + ')' : ''}</small>
              ${reminder.description ? '<br><small style="color: #ccc;">' + reminder.description + '</small>' : ''}
            </div>
            <div style="margin-top: 8px; display: flex; gap: 5px;">
              <button onclick="snoozeReminder(${reminder.id})" style="padding: 5px 10px; background-color: #1e90ff; border: none; border-radius: 3px; color: white; cursor: pointer; font-size: 11px; flex: 1;">Snooze</button>
              <button onclick="deleteReminder(${reminder.id})" style="padding: 5px 10px; background-color: #ff4444; border: none; border-radius: 3px; color: white; cursor: pointer; font-size: 11px; flex: 1;">Delete</button>
            </div>
          </div>
        `);
        content.append(reminderEl);
      });
    });
  } catch (err) {
    console.error("Error loading reminders:", err);
  }
}

function deleteReminder(id) {
  if (!confirm('Delete this reminder?')) return;
  
  if (typeof eel !== "undefined" && eel.delete_reminder) {
    try {
      eel.delete_reminder(id)(function (result) {
        if (result.success) {
          setSiriMessage('Reminder deleted');
          loadReminders();
        }
      });
    } catch (err) {
      console.error("Error deleting reminder:", err);
    }
  }
}

function snoozeReminder(id) {
  if (typeof eel !== "undefined" && eel.snooze_reminder) {
    try {
      eel.snooze_reminder(id, 5)(function (result) {
        if (result.success) {
          setSiriMessage('Reminder snoozed for 5 minutes');
          loadReminders();
        }
      });
    } catch (err) {
      console.error("Error snoozing reminder:", err);
    }
  }
}

// Frontend handler for reminder notifications
eel.expose(DisplayReminderNotification);
function DisplayReminderNotification(message) {
  // Show notification in Siri message
  setSiriMessage(message);
  
  // Play notification sound
  try {
    const audio = new Audio('/frontend/assets/audio/start_sound.mp3');
    audio.play();
  } catch (e) {
    console.warn("Could not play notification sound:", e);
  }
  
  // Show browser notification if supported
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('Ellie Reminder', {
      body: message,
      icon: '/frontend/assets/img/logo.ico'
    });
  }
}