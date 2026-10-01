import os

import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

cursor = conn.cursor()

sql = """
INSERT INTO students(student_name, roll_number, phone, route_id)
VALUES (%s, %s, %s, %s)
"""

data = ("Madhu Reddy", "23se02ml166", "8309134148", 1)


cursor.execute(sql, data)

conn.commit()

print("Student Added Successfully!")