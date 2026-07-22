import mysql.connector
from argon2 import PasswordHasher

ph = PasswordHasher()

# Database Connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Madhu@123",
    database="college_bus_tracking"
)

cursor = conn.cursor()

# Get all students
cursor.execute("SELECT id, password FROM students")
students = cursor.fetchall()

updated = 0

for student_id, password in students:

    # Skip already Argon2 hashed passwords
    if password.startswith("$argon2"):
        continue

    hashed_password = ph.hash(password)

    cursor.execute(
        "UPDATE students SET password=%s WHERE id=%s",
        (hashed_password, student_id)
    )

    updated += 1

conn.commit()

cursor.close()
conn.close()

print(f"✅ {updated} student password(s) converted to Argon2 successfully.")