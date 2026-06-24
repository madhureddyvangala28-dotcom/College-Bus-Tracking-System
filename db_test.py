import mysql.connector
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Madhu@123",
    database="college_bus_tracking"
)
if conn.is_connected():
    print("Database Connected Successfully!")