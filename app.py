from flask import Flask, render_template, request, redirect
import mysql.connector

app = Flask(__name__)

@app.route('/')
def home():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    return render_template(
        "index.html",
        students=students
    )

@app.route('/buses')
def buses():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buses")
    bus_data = cursor.fetchall()

    return render_template("buses.html", buses=bus_data)
@app.route('/add_bus', methods=['GET', 'POST'])
def add_bus():

    if request.method == 'POST':

        bus_number = request.form['bus_number']
        driver_name = request.form['driver_name']
        capacity = request.form['capacity']

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Madhu@123",
            database="college_bus_tracking"
        )

        cursor = conn.cursor()

        query = """
        INSERT INTO buses(bus_number, driver_name, capacity)
        VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (bus_number, driver_name, capacity)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect('/buses')

    return render_template('add_bus.html')

@app.route('/routes')
def routes():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM routes")

    route_data = cursor.fetchall()

    return render_template(
        "routes.html",
        routes=route_data
    )
@app.route('/dashboard')
def dashboard():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )


    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM buses")
    buses = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM routes")
    routes = cursor.fetchone()[0]

    return render_template(
        "dashboard.html",
        students=students,
        buses=buses,
        routes=routes
    )

if __name__ == "__main__":
    app.run(debug=True)