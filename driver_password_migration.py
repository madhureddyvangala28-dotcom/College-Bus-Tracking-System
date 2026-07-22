import mysql.connector
from argon2 import PasswordHasher

ph = PasswordHasher()

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Madhu@123",
    database="college_bus_tracking"
)

cursor = conn.cursor()

cursor.execute("SELECT id, password FROM drivers")
drivers = cursor.fetchall()

updated = 0

for driver_id, password in drivers:

    # Skip already Argon2 hashed passwords
    if password.startswith("$argon2"):
        continue

    hashed_password = ph.hash(password)

    cursor.execute(
        "UPDATE drivers SET password=%s WHERE id=%s",
        (hashed_password, driver_id)
    )

    updated += 1

conn.commit()

cursor.close()
conn.close()

print(f"✅ {updated} driver password(s) converted to Argon2 successfully.")