import sqlite3

# This creates a new database file named ellie.db
conn = sqlite3.connect("ellie.db")
cursor = conn.cursor()

# Create the contacts table
cursor.execute('''CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name VARCHAR(200), Phone VARCHAR(255), email VARCHAR(255) NULL)''')

# Insert a test contact (Replace with your actual friend's name and number)
# Make sure to include the country code!
cursor.execute("INSERT INTO contacts (name, Phone) VALUES ('chaitanya', '+919876543210')")
cursor.execute("INSERT INTO contacts (name, Phone) VALUES ('boss', '+919876543210')")

conn.commit()
conn.close()
print("✅ Database ellie.db created successfully with test contacts!")