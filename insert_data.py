import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Madhu@123",
    database="college_bus_tracking"
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