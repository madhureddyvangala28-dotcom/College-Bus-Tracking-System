import os

import mysql.connector
from argon2 import PasswordHasher

ph = PasswordHasher()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
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