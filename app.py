from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
import mysql.connector
import os
from werkzeug.utils import secure_filename
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()


app = Flask(__name__)
app.secret_key = "college_bus_tracking_secret"

# =====================================================
# STUDENT IMAGE CONFIGURATION
# =====================================================

UPLOAD_FOLDER = "static/images/students"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# =====================================================
# IMAGE VALIDATION
# =====================================================

def allowed_file(filename):

    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def get_db_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )
@app.route("/")
def home():

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    cursor.execute("SELECT COUNT(*) FROM students")
    students_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM drivers")
    drivers_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM buses")
    buses_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM routes")
    routes_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        active_page="home",
        students_count=students_count,
        drivers_count=drivers_count,
        buses_count=buses_count,
        routes_count=routes_count
    )
# =====================================================
# STUDENT LIST
# =====================================================

@app.route("/admin/students")
def students():

    search = request.args.get("search", "")
    route = request.args.get("route", "")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            s.id,
            s.student_name,
            s.roll_number,
            s.phone,
            s.profile_image,
            s.route_id,
            r.route_name
        FROM students s
        LEFT JOIN routes r
            ON s.route_id = r.route_id
        WHERE 1=1
    """

    values = []

    # -------------------------
    # Search
    # -------------------------

    if search:

        query += """
            AND (
                s.student_name LIKE %s
                OR s.roll_number LIKE %s
            )
        """

        values.append(f"%{search}%")
        values.append(f"%{search}%")

    # -------------------------
    # Route Filter
    # -------------------------

    if route:

        query += " AND s.route_id=%s"

        values.append(route)

    # -------------------------
    # Order
    # -------------------------

    query += """
        ORDER BY s.student_name ASC
    """

    cursor.execute(query, values)

    students = cursor.fetchall()

    # -------------------------
    # Load Routes for Filter
    # -------------------------

    cursor.execute("""
        SELECT
            route_id,
            route_name
        FROM routes
        ORDER BY route_name
    """)

    routes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(

        "admin/students/students.html",

        students=students,

        routes=routes,

        search=search,

        route=route,

        active_page="students"

    )

# =====================================================
# ADD STUDENT
# =====================================================

@app.route("/admin/add_student", methods=["GET", "POST"])
def add_student():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ----------------------------
    # Load Routes
    # ----------------------------

    cursor.execute("""
        SELECT
            route_id,
            route_name
        FROM routes
        ORDER BY route_name
    """)

    routes = cursor.fetchall()

    # ----------------------------
    # SAVE STUDENT
    # ----------------------------

    if request.method == "POST":

        student_name = request.form["student_name"].strip()
        roll_number = request.form["roll_number"].strip().upper()
        phone = request.form["phone"].strip()
        route_id = request.form["route_id"]
        password = request.form["password"].strip()

        # ----------------------------
        # Basic Validation
        # ----------------------------

        if student_name == "":
            flash("Student Name is required.", "danger")
            return render_template(
                "admin/students/add_student.html",
                routes=routes,
                active_page="students"
            )

        if roll_number == "":
            flash("Roll Number is required.", "danger")
            return render_template(
                "admin/students/add_student.html",
                routes=routes,
                active_page="students"
            )

        if len(phone) != 10 or not phone.isdigit():
            flash("Phone Number must contain exactly 10 digits.", "danger")
            return render_template(
                "admin/students/add_student.html",
                routes=routes,
                active_page="students"
            )

        if len(password) < 4:
            flash("Password must contain at least 4 characters.", "danger")
            return render_template(
                "admin/students/add_student.html",
                routes=routes,
                active_page="students"
            )

        # ----------------------------
        # Duplicate Roll Number
        # ----------------------------

        cursor.execute(
            "SELECT id FROM students WHERE roll_number=%s",
            (roll_number,)
        )

        if cursor.fetchone():

            flash("Roll Number already exists.", "danger")

            return render_template(
                "admin/students/add_student.html",
                routes=routes,
                active_page="students"
            )

        # ----------------------------
        # Duplicate Phone Number
        # ----------------------------

        cursor.execute(
            "SELECT id FROM students WHERE phone=%s",
            (phone,)
        )

        if cursor.fetchone():

            flash("Phone Number already exists.", "danger")

            return render_template(
                "admin/students/add_student.html",
                routes=routes,
                active_page="students"
            )

        # ----------------------------
        # Upload Image
        # ----------------------------

        filename = "student.png"

        if "profile_image" in request.files:

            file = request.files["profile_image"]

            if file and file.filename != "":

                if allowed_file(file.filename):

                    filename = secure_filename(file.filename)

                    file.save(
                        os.path.join(
                            app.config["UPLOAD_FOLDER"],
                            filename
                        )
                    )

                else:

                    flash(
                        "Only JPG, JPEG and PNG images are allowed.",
                        "danger"
                    )

                    return render_template(
                        "admin/students/add_student.html",
                        routes=routes,
                        active_page="students"
                    )

        # ----------------------------
        # Insert Student
        # ----------------------------

        cursor.execute("""
            INSERT INTO students
            (
                student_name,
                roll_number,
                phone,
                route_id,
                password,
                profile_image
            )
            VALUES
            (%s,%s,%s,%s,%s,%s)
        """,
        (
            student_name,
            roll_number,
            phone,
            route_id,
            password,
            filename
        ))

        conn.commit()

        flash(
            "Student Added Successfully!",
            "success"
        )

        cursor.close()
        conn.close()

        return redirect(url_for("students"))

    # ----------------------------
    # GET REQUEST
    # ----------------------------

    cursor.close()
    conn.close()

    return render_template(
        "admin/students/add_student.html",
        routes=routes,
        active_page="students"
    )

# =====================================================
# EDIT STUDENT
# =====================================================

@app.route("/admin/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ----------------------------
    # Load Student
    # ----------------------------

    cursor.execute("""
        SELECT *
        FROM students
        WHERE id=%s
    """, (id,))

    student = cursor.fetchone()

    if not student:

        cursor.close()
        conn.close()

        flash("Student not found.", "danger")

        return redirect(url_for("students"))

    # ----------------------------
    # Load Routes
    # ----------------------------

    cursor.execute("""
        SELECT
            route_id,
            route_name
        FROM routes
        ORDER BY route_name
    """)

    routes = cursor.fetchall()

    # ----------------------------
    # UPDATE STUDENT
    # ----------------------------

    if request.method == "POST":

        student_name = request.form["student_name"].strip()
        roll_number = request.form["roll_number"].strip().upper()
        phone = request.form["phone"].strip()
        route_id = request.form["route_id"]

        password = request.form["password"].strip()

        # ----------------------------
        # Validation
        # ----------------------------

        if student_name == "":

            flash("Student Name is required.", "danger")

            return render_template(
                "admin/students/edit_student.html",
                student=student,
                routes=routes,
                active_page="students"
            )

        if roll_number == "":

            flash("Roll Number is required.", "danger")

            return render_template(
                "admin/students/edit_student.html",
                student=student,
                routes=routes,
                active_page="students"
            )

        if len(phone) != 10 or not phone.isdigit():

            flash("Phone Number must contain exactly 10 digits.", "danger")

            return render_template(
                "admin/students/edit_student.html",
                student=student,
                routes=routes,
                active_page="students"
            )

        # ----------------------------
        # Duplicate Roll Number
        # ----------------------------

        cursor.execute("""

            SELECT id

            FROM students

            WHERE roll_number=%s
            AND id!=%s

        """, (roll_number, id))

        if cursor.fetchone():

            flash(
                "Roll Number already exists.",
                "danger"
            )

            return render_template(
                "admin/students/edit_student.html",
                student=student,
                routes=routes,
                active_page="students"
            )

        # ----------------------------
        # Duplicate Phone
        # ----------------------------

        cursor.execute("""

            SELECT id

            FROM students

            WHERE phone=%s
            AND id!=%s

        """, (phone, id))

        if cursor.fetchone():

            flash(
                "Phone Number already exists.",
                "danger"
            )

            return render_template(
                "admin/students/edit_student.html",
                student=student,
                routes=routes,
                active_page="students"
            )

        # ----------------------------
        # Keep Old Image
        # ----------------------------

        filename = student["profile_image"]

        # ----------------------------
        # Upload New Image
        # ----------------------------

        if "profile_image" in request.files:

            file = request.files["profile_image"]

            if file and file.filename != "":

                if allowed_file(file.filename):

                    filename = secure_filename(file.filename)

                    file.save(
                        os.path.join(
                            app.config["UPLOAD_FOLDER"],
                            filename
                        )
                    )

                else:

                    flash(
                        "Only JPG, JPEG and PNG images are allowed.",
                        "danger"
                    )

                    return render_template(
                        "admin/students/edit_student.html",
                        student=student,
                        routes=routes,
                        active_page="students"
                    )

        # ----------------------------
        # Keep Existing Password
        # ----------------------------

        if password == "":

            password = student["password"]

        # ----------------------------
        # Update Database
        # ----------------------------

        cursor.execute("""

            UPDATE students

            SET

                student_name=%s,

                roll_number=%s,

                phone=%s,

                route_id=%s,

                password=%s,

                profile_image=%s

            WHERE id=%s

        """,
        (

            student_name,

            roll_number,

            phone,

            route_id,

            password,

            filename,

            id

        ))

        conn.commit()

        flash(
            "Student Updated Successfully!",
            "success"
        )

        cursor.close()
        conn.close()

        return redirect(url_for("students"))

    cursor.close()
    conn.close()

    return render_template(

        "admin/students/edit_student.html",

        student=student,

        routes=routes,

        active_page="students"

    )

# =====================================================
# STUDENT PROFILE
# =====================================================

@app.route("/admin/student_profile/<int:id>")
def admin_student_profile(id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            s.id,
            s.student_name,
            s.roll_number,
            s.phone,
            s.password,
            s.profile_image,
            s.route_id,
            r.route_name,
            r.source,
            r.destination
        FROM students s

        LEFT JOIN routes r
        ON s.route_id = r.route_id

        WHERE s.id=%s
    """,(id,))

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    if not student:

        flash("Student not found.","danger")

        return redirect(url_for("students"))

    return render_template(

        "admin/students/student_profile.html",

        student=student,

        active_page="students"

    )
# =====================================================
# DELETE STUDENT
# =====================================================

@app.route("/admin/delete_student/<int:id>")
def delete_student(id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get student image
    cursor.execute("""
        SELECT profile_image
        FROM students
        WHERE id=%s
    """, (id,))

    student = cursor.fetchone()

    if not student:

        cursor.close()
        conn.close()

        flash("Student not found.", "danger")
        return redirect(url_for("students"))

    # Delete uploaded image (not default image)

    if student["profile_image"] is not None and student["profile_image"] != "student.png":

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            student["profile_image"]
        )

        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete student record

    cursor.execute("""
        DELETE FROM students
        WHERE id=%s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Student Deleted Successfully!", "success")

    return redirect(url_for("students"))
# =====================================================
# DRIVERS PAGE
# =====================================================

@app.route("/admin/drivers")
def drivers():

    search = request.args.get("search", "")
    status = request.args.get("status", "")

    conn = get_db_connection()      # Use common database function
    cursor = conn.cursor(buffered=True)

    query = """
        SELECT *
        FROM drivers
        WHERE 1=1
    """

    values = []

    # Search by Driver Name or License Number
    if search:

        query += """
            AND (
                driver_name LIKE %s
                OR license_number LIKE %s
            )
        """

        values.append(f"%{search}%")
        values.append(f"%{search}%")

    # Filter by Status
    if status:

        query += " AND status=%s"

        values.append(status)

    cursor.execute(query, values)

    drivers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/driver/drivers.html",
        active_page="drivers",
        drivers=drivers,
        search=search,
        status=status
    )
# =====================================================
# DRIVER PROFILE
# =====================================================

@app.route("/driver_profile/<int:id>")
def driver_profile(id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.id,
            d.driver_name,
            d.license_number,
            d.phone,
            d.status,
            d.password,
            b.bus_number,
            r.route_name,
            b.capacity
        FROM drivers d
        LEFT JOIN buses b
            ON d.bus_number = b.bus_number
        LEFT JOIN routes r
            ON d.route_id = r.route_id
        WHERE d.id=%s
    """,(id,))

    driver = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "admin/driver/driver_profile.html",
        driver=driver
    )
# ==========================================
# ADD DRIVER
# ==========================================

@app.route("/admin/add_driver", methods=["GET", "POST"])
def add_driver():

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "GET":

        cursor.execute("""
            SELECT bus_id, bus_number
            FROM buses
            ORDER BY bus_number
        """)
        buses = cursor.fetchall()

        cursor.execute("""
            SELECT route_id, route_name
            FROM routes
            ORDER BY route_id
        """)
        routes = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "admin/driver/add_driver.html",
            buses=buses,
            routes=routes
        )

    driver_name = request.form["driver_name"]
    license_number = request.form["license_number"]
    phone = request.form["phone"]
    bus_number = request.form["bus_number"]
    route_id = request.form["route_id"]
    status = request.form["status"]
    password = request.form["password"]

    cursor.execute("""
        INSERT INTO drivers
        (driver_name,license_number,phone,bus_number,route_id,status,password)
        VALUES(%s,%s,%s,%s,%s,%s,%s)
    """,
    (
        driver_name,
        license_number,
        phone,
        bus_number,
        route_id,
        status,
        password
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Driver Added Successfully", "success")

    return redirect(url_for("drivers"))
# =====================================================
# EDIT DRIVER
# =====================================================

@app.route("/edit_driver/<int:id>", methods=["GET", "POST"])
def edit_driver(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "GET":

        # Driver Details
        cursor.execute("""
            SELECT *
            FROM drivers
            WHERE id=%s
        """, (id,))
        driver = cursor.fetchone()

        # Bus List
        cursor.execute("""
            SELECT bus_number
            FROM buses
            ORDER BY bus_number
        """)
        buses = cursor.fetchall()

        # Route List
        cursor.execute("""
            SELECT route_id, route_name
            FROM routes
            ORDER BY route_id
        """)
        routes = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            "admin/driver/edit_driver.html",
            driver=driver,
            buses=buses,
            routes=routes
        )

    driver_name = request.form["driver_name"]
    license_number = request.form["license_number"]
    phone = request.form["phone"]
    bus_number = request.form["bus_number"]
    route_id = request.form["route_id"]
    status = request.form["status"]
    password = request.form["password"]

    cursor.execute("""
        UPDATE drivers
        SET
            driver_name=%s,
            license_number=%s,
            phone=%s,
            bus_number=%s,
            route_id=%s,
            status=%s,
            password=%s
        WHERE id=%s
    """,
    (
        driver_name,
        license_number,
        phone,
        bus_number,
        route_id,
        status,
        password,
        id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Driver Updated Successfully", "success")

    return redirect(url_for("drivers"))

    # ----------------------------------------
    # GET DRIVER DETAILS
    # ----------------------------------------

    query = """
        SELECT
            id,
            driver_name,
            license_number,
            phone,
            bus_number,
            route_id,
            status
        FROM drivers
        WHERE id=%s
    """

    cursor.execute(query, (id,))

    driver = cursor.fetchone()

    cursor.close()
    conn.close()

    if not driver:
        flash("Driver not found.", "danger")
        return redirect("/admin/drivers")

    return render_template(
        "admin/driver/edit_driver.html",
        driver=driver,
        active_page="drivers"
    )
# =====================================================
# DELETE DRIVER
# =====================================================

@app.route("/admin/delete_driver/<int:id>")
def delete_driver(id):

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    query = "DELETE FROM drivers WHERE id=%s"

    cursor.execute(query, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Driver deleted successfully.", "success")

    return redirect("/admin/drivers")


# =====================================================
# BUS LIST PAGE
# =====================================================

@app.route("/admin/buses")
def buses():

    search = request.args.get("search", "")
    route = request.args.get("route", "")

    conn = get_db_connection()

    # IMPORTANT: dictionary=True
    cursor = conn.cursor(buffered=True, dictionary=True)

    query = """
        SELECT
            bus_id,
            bus_number,
            driver_name,
            capacity,
            route_id
        FROM buses
        WHERE 1=1
    """

    values = []

    if search:
        query += " AND bus_number LIKE %s"
        values.append(f"%{search}%")

    if route:
        query += " AND route_id=%s"
        values.append(route)

    query += " ORDER BY route_id"

    cursor.execute(query, values)

    buses = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/bus/buses.html",
        buses=buses,
        search=search,
        route=route,
        active_page="buses"
    )

# =====================================================
# ADD BUS
# =====================================================

@app.route("/admin/add_bus", methods=["GET", "POST"])
def add_bus():

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)

    # Load Drivers
    cursor.execute("""
        SELECT
            driver_name,
            bus_number
        FROM drivers
        ORDER BY driver_name
    """)
    drivers = cursor.fetchall()

    # Load Routes
    cursor.execute("""
        SELECT
            route_id,
            route_name
        FROM routes
        ORDER BY route_id
    """)
    routes = cursor.fetchall()

    if request.method == "POST":

        bus_number = request.form["bus_number"]
        driver_name = request.form["driver_name"]
        capacity = request.form["capacity"]
        route_id = request.form["route_id"]

        cursor.execute("""
            INSERT INTO buses
            (
                bus_number,
                driver_name,
                capacity,
                route_id
            )
            VALUES
            (
                %s,%s,%s,%s
            )
        """,
        (
            bus_number,
            driver_name,
            capacity,
            route_id
        ))

        conn.commit()

        flash("Bus Added Successfully", "success")

        cursor.close()
        conn.close()

        return redirect(url_for("buses"))

    cursor.close()
    conn.close()

    return render_template(
        "admin/bus/add_bus.html",
        drivers=drivers,
        routes=routes
    )

# =====================================================
# EDIT BUS
# =====================================================

@app.route("/admin/edit_bus/<int:bus_id>", methods=["GET", "POST"])
def edit_bus(bus_id):

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)

    # Load Bus Details
    cursor.execute("""
        SELECT *
        FROM buses
        WHERE bus_id=%s
    """, (bus_id,))

    bus = cursor.fetchone()

    # Load Drivers
    cursor.execute("""
        SELECT
            driver_name,
            bus_number
        FROM drivers
        ORDER BY driver_name
    """)

    drivers = cursor.fetchall()

    # Load Routes
    cursor.execute("""
        SELECT
            route_id,
            route_name
        FROM routes
        ORDER BY route_id
    """)

    routes = cursor.fetchall()

    if request.method == "POST":

        bus_number = request.form["bus_number"]
        driver_name = request.form["driver_name"]
        capacity = request.form["capacity"]
        route_id = request.form["route_id"]

        cursor.execute("""
            UPDATE buses
            SET
                bus_number=%s,
                driver_name=%s,
                capacity=%s,
                route_id=%s
            WHERE bus_id=%s
        """,
        (
            bus_number,
            driver_name,
            capacity,
            route_id,
            bus_id
        ))

        conn.commit()

        flash("Bus Updated Successfully", "success")

        cursor.close()
        conn.close()

        return redirect(url_for("buses"))

    cursor.close()
    conn.close()

    return render_template(
        "admin/bus/edit_bus.html",
        bus=bus,
        drivers=drivers,
        routes=routes
    )

# =====================================================
# BUS PROFILE
# =====================================================

@app.route("/admin/bus_profile/<int:bus_id>")
def bus_profile(bus_id):

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)

    cursor.execute("""
        SELECT
            b.bus_id,
            b.bus_number,
            b.driver_name,
            b.capacity,
            r.route_name,
            r.source,
            r.destination,
            r.distance,
            r.estimated_time,
            r.status           
        FROM buses b
        LEFT JOIN routes r
        ON b.route_id = r.route_id
        WHERE b.bus_id = %s
    """, (bus_id,))

    bus = cursor.fetchone()

    cursor.close()
    conn.close()

    if not bus:
        flash("Bus not found.", "danger")
        return redirect(url_for("buses"))

    return render_template(
        "admin/bus/bus_profile.html",
        bus=bus,
        active_page="buses"
    )


# =====================================================
# DELETE BUS
# =====================================================

@app.route("/admin/delete_bus/<int:bus_id>")
def delete_bus(bus_id):

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    # Check if bus exists
    cursor.execute("""
        SELECT bus_id
        FROM buses
        WHERE bus_id=%s
    """, (bus_id,))

    bus = cursor.fetchone()

    if bus is None:

        flash("Bus not found.", "danger")

        cursor.close()
        conn.close()

        return redirect(url_for("buses"))

    # Delete Bus
    cursor.execute("""
        DELETE FROM buses
        WHERE bus_id=%s
    """, (bus_id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Bus deleted successfully.", "success")

    return redirect(url_for("buses"))

# =====================================================
# ROUTE LIST PAGE
# =====================================================

@app.route("/admin/routes")
def routes():

    search = request.args.get("search", "")
    status = request.args.get("status", "")

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)

    query = """
        SELECT
            route_id,
            route_name,
            source,
            destination,
            distance,
            estimated_time,
            status
        FROM routes
        WHERE 1=1
    """

    values = []

    if search:
        query += " AND route_name LIKE %s"
        values.append(f"%{search}%")

    if status:
        query += " AND status=%s"
        values.append(status)

    query += " ORDER BY route_id"

    cursor.execute(query, values)
    routes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/routes/routes.html",
        routes=routes,
        search=search,
        status=status,
        active_page="routes"
    )
# =====================================================
# ROUTE PROFILE
# =====================================================

@app.route("/admin/route_profile/<int:route_id>")
def route_profile(route_id):

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True, dictionary=True)

    cursor.execute("""
        SELECT *
        FROM routes
        WHERE route_id=%s
    """, (route_id,))

    route = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "admin/routes/route_profile.html",
        route=route,
        active_page="routes"
    )
# =====================================================
# ADD ROUTE
# =====================================================

@app.route("/admin/add_route", methods=["GET", "POST"])
def add_route():

    if request.method == "POST":

        route_name = request.form["route_name"]
        source = request.form["source"]
        destination = request.form["destination"]
        distance = request.form["distance"]
        estimated_time = request.form["estimated_time"]
        status = request.form["status"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO routes
            (
                route_name,
                source,
                destination,
                distance,
                estimated_time,
                status
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            route_name,
            source,
            destination,
            distance,
            estimated_time,
            status
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Route Added Successfully!", "success")

        return redirect(url_for("routes"))

    return render_template(
        "admin/routes/add_route.html",
        active_page="routes"
    )

# =====================================================
# EDIT ROUTE
# =====================================================

@app.route("/admin/edit_route/<int:route_id>", methods=["GET","POST"])
def edit_route(route_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":

        route_name = request.form["route_name"]
        source = request.form["source"]
        destination = request.form["destination"]
        distance = request.form["distance"]
        estimated_time = request.form["estimated_time"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE routes
            SET
                route_name=%s,
                source=%s,
                destination=%s,
                distance=%s,
                estimated_time=%s,
                status=%s
            WHERE route_id=%s
        """,
        (
            route_name,
            source,
            destination,
            distance,
            estimated_time,
            status,
            route_id
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Route Updated Successfully!", "success")

        return redirect(url_for("routes"))

    cursor.execute("""
        SELECT *
        FROM routes
        WHERE route_id=%s
    """,(route_id,))

    route = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "admin/routes/edit_route.html",
        route=route,
        active_page="routes"
    )
# =====================================================
# DELETE ROUTE
# =====================================================

@app.route("/admin/delete_route/<int:route_id>")
def delete_route(route_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM routes
        WHERE route_id=%s
    """,(route_id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Route Deleted Successfully!", "success")

    return redirect(url_for("routes"))

# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin/dashboard")
def dashboard():

    # ----------------------------------------
    # Protect Admin Dashboard
    # ----------------------------------------
    if "admin_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    # ----------------------------------------
    # Students Count
    # ----------------------------------------
    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]

    # ----------------------------------------
    # Drivers Count
    # ----------------------------------------
    cursor.execute("SELECT COUNT(*) FROM drivers")
    driver_count = cursor.fetchone()[0]

    # ----------------------------------------
    # Buses Count
    # ----------------------------------------
    cursor.execute("SELECT COUNT(*) FROM buses")
    bus_count = cursor.fetchone()[0]

    # ----------------------------------------
    # Routes Count
    # ----------------------------------------
    cursor.execute("SELECT COUNT(*) FROM routes")
    route_count = cursor.fetchone()[0]

    # ----------------------------------------
    # Available Drivers
    # ----------------------------------------
    cursor.execute(
        "SELECT COUNT(*) FROM drivers WHERE status=%s",
        ("Available",)
    )
    available_count = cursor.fetchone()[0]

    # ----------------------------------------
    # Drivers On Trip
    # ----------------------------------------
    cursor.execute(
        "SELECT COUNT(*) FROM drivers WHERE status=%s",
        ("On Trip",)
    )
    trip_count = cursor.fetchone()[0]

    # ----------------------------------------
    # Drivers On Leave
    # ----------------------------------------
    cursor.execute(
        "SELECT COUNT(*) FROM drivers WHERE status=%s",
        ("On Leave",)
    )
    leave_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        "admin/dashboard/dashboard.html",
        active_page="dashboard",
        student_count=student_count,
        driver_count=driver_count,
        bus_count=bus_count,
        route_count=route_count,
        available_count=available_count,
        trip_count=trip_count,
        leave_count=leave_count
    )
# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    role = request.form.get("role")
    username = request.form.get("username").strip()
    password = request.form.get("password")

    # =====================================================
    # HIDDEN ADMIN LOGIN
    # =====================================================
    if username.lower() == "admin":

        cursor.execute("""
            SELECT *
            FROM admins
            WHERE username=%s
        """, (username,))

        admin = cursor.fetchone()

        if admin:
            try:
                ph.verify(admin["password"], password)

                session.clear()

                session["admin_id"] = admin["id"]
                session["admin_name"] = admin["admin_name"]
                session["admin_role"] = admin["role"]

                cursor.close()
                conn.close()

                return redirect(url_for("dashboard"))

            except VerifyMismatchError:
                pass

        flash("Invalid Admin Username or Password.", "danger")

        cursor.close()
        conn.close()

        return redirect(url_for("login"))

    # =====================================================
    # STUDENT LOGIN
    # =====================================================
    if role == "student":

        cursor.execute("""
            SELECT *
            FROM students
            WHERE roll_number=%s
        """, (username,))

        student = cursor.fetchone()

        if student:
            try:
                ph.verify(student["password"], password)

                session.clear()

                session["student_id"] = student["id"]
                session["student_name"] = student["student_name"]
                session["profile_image"] = student["profile_image"]

                cursor.close()
                conn.close()

                return redirect(url_for("student_dashboard"))

            except VerifyMismatchError:
                pass

        flash("Please check your Roll Number and Password.", "danger")

    # =====================================================
    # DRIVER LOGIN
    # =====================================================
    elif role == "driver":

        cursor.execute("""
            SELECT *
            FROM drivers
            WHERE license_number=%s
        """, (username,))

        driver = cursor.fetchone()

        if driver:
            try:
                ph.verify(driver["password"], password)

                session.clear()

                session["driver_id"] = driver["id"]
                session["driver_name"] = driver["driver_name"]

                cursor.close()
                conn.close()

                return redirect(url_for("driver_dashboard"))

            except VerifyMismatchError:
                pass

        flash("Please check your License Number and Password.", "danger")

    cursor.close()
    conn.close()

    return redirect(url_for("login"))
# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/login")

    return redirect("/admin/dashboard")

# ==========================================
# STUDENT DASHBOARD
# ==========================================

@app.route("/student_dashboard")
def student_dashboard():

    if "student_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    # ------------------------------
    # Student Details
    # ------------------------------

    cursor.execute("""
        SELECT
            student_name,
            roll_number,
            phone,
            route_id,
            profile_image
        FROM students
        WHERE id=%s
    """, (session["student_id"],))

    student = cursor.fetchone()

    # ------------------------------
    # Today's Bus Status
    # ------------------------------

    cursor.execute("""
SELECT

    s.student_name,
    s.roll_number,

    b.bus_number,
    b.driver_name,

    r.route_name,

    lbl.current_stop,
    lbl.speed,

    TIME_FORMAT(lbl.eta,'%h:%i %p') AS eta,

    CASE
        WHEN lbl.speed > 0 THEN 'On Time'
        ELSE 'Delayed'
    END AS status

FROM students s

LEFT JOIN student_bus_assignment sba
       ON s.id = sba.student_id

LEFT JOIN buses b
       ON sba.bus_id = b.bus_id

LEFT JOIN routes r
       ON b.route_id = r.route_id

LEFT JOIN live_bus_location lbl
       ON b.bus_id = lbl.bus_id

WHERE s.id = %s

LIMIT 1
""", (session["student_id"],))
    bus_status = cursor.fetchone()

    cursor.close()
    conn.close()
    return render_template(
        "student/student_dashboard.html",
        student=student,
        bus_status=bus_status,
        active_page="dashboard"
    )
# ==========================================
# STUDENT PROFILE (Student Portal)
# ==========================================

@app.route("/student/student_profile")
def student_profile():

    if "student_id" not in session:
        return redirect("/login")

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )

    cursor = conn.cursor(dictionary=True, buffered=True)

    query = """
         SELECT
        student_name,
        roll_number,
        phone,
        email,
        department,
        semester,
        parent_name,
        parent_phone,
        address,
        route_id,
        profile_image
        FROM students
        WHERE id=%s
    """

    cursor.execute(query, (session["student_id"],))

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "student/student_profile.html",
        student=student,
        active_page="profile"
    )
# ==========================================
# CHANGE PASSWORD PAGE
# ==========================================

@app.route("/student/change_password")
def change_password():

    if "student_id" not in session:
        return redirect("/login")

    return render_template(
        "student/change_password.html",
        active_page="change_password"
    )
# ==========================================
# UPDATE PASSWORD
# ==========================================

@app.route("/student/update_password", methods=["POST"])
def update_password():

    if "student_id" not in session:
        return redirect("/login")

    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    # -----------------------------
    # Basic Validation
    # -----------------------------
    if not current_password or not new_password or not confirm_password:

        flash("All fields are required.", "danger")
        return redirect(url_for("change_password"))

    if new_password != confirm_password:

        flash("New Password and Confirm Password do not match.", "danger")
        return redirect(url_for("change_password"))

    if len(new_password) < 8:

        flash("Password must be at least 8 characters long.", "danger")
        return redirect(url_for("change_password"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT password
        FROM students
        WHERE id=%s
    """, (session["student_id"],))

    student = cursor.fetchone()

    if not student:

        cursor.close()
        conn.close()

        flash("Student not found.", "danger")
        return redirect(url_for("change_password"))

    # -----------------------------
    # Verify Current Password
    # -----------------------------
    try:
        ph.verify(student["password"], current_password)

    except VerifyMismatchError:

        cursor.close()
        conn.close()

        flash("Current password is incorrect.", "danger")
        return redirect(url_for("change_password"))

    # -----------------------------
    # Prevent Reusing Same Password
    # -----------------------------
    try:
        ph.verify(student["password"], new_password)

        cursor.close()
        conn.close()

        flash("New password must be different from the current password.", "danger")
        return redirect(url_for("change_password"))

    except VerifyMismatchError:
        pass

    # -----------------------------
    # Hash New Password (Argon2)
    # -----------------------------
    hashed_password = ph.hash(new_password)

    cursor.execute("""
        UPDATE students
        SET password=%s
        WHERE id=%s
    """, (hashed_password, session["student_id"]))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Password changed successfully.", "success")

    return redirect(url_for("change_password"))
# ==========================================
# EDIT PROFILE PAGE
# ==========================================

@app.route("/student/edit_profile")
def edit_profile():

    if "student_id" not in session:
        return redirect("/login")

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )

    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        id,
        student_name,
        roll_number,
        phone,
        email,
        department,
        semester,
        parent_name,
        parent_phone,
        address,
        profile_image
    FROM students
    WHERE id=%s
    """

    cursor.execute(query, (session["student_id"],))

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "student/edit_profile.html",
        student=student
    )
# ==========================================
# UPDATE PROFILE
# ==========================================

@app.route("/student/update_profile", methods=["POST"])
def update_profile():

    if "student_id" not in session:
        return redirect("/login")

    # -------------------------
    # Get Form Data
    # -------------------------

    student_name = request.form.get("student_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    department = request.form.get("department", "").strip()
    semester = request.form.get("semester", "").strip()
    parent_name = request.form.get("parent_name", "").strip()
    parent_phone = request.form.get("parent_phone", "").strip()
    address = request.form.get("address", "").strip()

    profile_image = request.files.get("profile_image")

    # -------------------------
    # Validation
    # -------------------------

    if student_name == "" or phone == "":
        flash("Student Name and Phone are required.", "danger")
        return redirect(url_for("edit_profile"))

    # -------------------------
    # Database Connection
    # -------------------------

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Madhu@123",
        database="college_bus_tracking"
    )

    cursor = conn.cursor(dictionary=True)

    # -------------------------
    # Get Current Image
    # -------------------------

    cursor.execute(
        "SELECT profile_image FROM students WHERE id=%s",
        (session["student_id"],)
    )

    student = cursor.fetchone()

    old_image = None

    if student:
        old_image = student["profile_image"]

    image_name = old_image

    # -------------------------
    # Upload New Image
    # -------------------------

    if (
        profile_image
        and profile_image.filename != ""
        and allowed_file(profile_image.filename)
    ):

        filename = secure_filename(profile_image.filename)

        image_name = f"{session['student_id']}_{filename}"

        save_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            image_name
        )

        profile_image.save(save_path)

        # Delete old image
        if (
            old_image
            and old_image != "student.png"
        ):

            old_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                old_image
            )

            if os.path.exists(old_path):
                os.remove(old_path)

    # -------------------------
    # Update Database
    # -------------------------

    update_query = """
        UPDATE students
        SET
            student_name=%s,
            phone=%s,
            email=%s,
            department=%s,
            semester=%s,
            parent_name=%s,
            parent_phone=%s,
            address=%s,
            profile_image=%s
        WHERE id=%s
    """

    values = (
        student_name,
        phone,
        email,
        department,
        semester,
        parent_name,
        parent_phone,
        address,
        image_name,
        session["student_id"]
    )

    cursor.execute(update_query, values)

    conn.commit()

    cursor.close()
    conn.close()

    # -------------------------
    # Update Session
    # -------------------------

    session["student_name"] = student_name
    session["profile_image"] = image_name

    # -------------------------
    # Success Message
    # -------------------------

    flash("Profile updated successfully!", "success")

    return redirect(url_for("student_profile"))
# ==========================================
# STUDENT LIVE BUS TRACKING
# ==========================================

@app.route("/student/live_tracking")
def student_live_tracking():

    if "student_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT

            s.student_name,

            b.bus_number,

            b.driver_name,

            r.route_name,

            lbl.latitude,

            lbl.longitude,

            lbl.current_stop,

            lbl.speed,

            TIME_FORMAT(lbl.eta,'%h:%i %p') AS eta,

            CASE
                WHEN lbl.speed > 0 THEN 'Moving'
                ELSE 'Stopped'
            END AS status

        FROM students s

        LEFT JOIN student_bus_assignment sba
               ON s.id=sba.student_id

        LEFT JOIN buses b
               ON sba.bus_id=b.bus_id

        LEFT JOIN routes r
               ON b.route_id=r.route_id

        LEFT JOIN live_bus_location lbl
               ON b.bus_id=lbl.bus_id

        WHERE s.id=%s

        LIMIT 1

    """,(session["student_id"],))

    tracking = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "student/live_tracking.html",
        tracking=tracking,
        active_page="live_tracking"
    )

# ==========================================
# LIVE LOCATION API
# ==========================================

@app.route("/student/live_location")
def student_live_location():

    if "student_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT

            lbl.latitude,
            lbl.longitude,
            lbl.current_stop,
            lbl.speed,

            TIME_FORMAT(lbl.eta,'%h:%i %p') AS eta,

            b.bus_number,
            b.driver_name

        FROM students s

        JOIN student_bus_assignment sba
            ON s.id=sba.student_id

        JOIN buses b
            ON sba.bus_id=b.bus_id

        JOIN live_bus_location lbl
            ON b.bus_id=lbl.bus_id

        WHERE s.id=%s

        LIMIT 1
    """,(session["student_id"],))

    data=cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(data)
# =====================================================
# STUDENT MY BUS
# =====================================================

@app.route("/student/bus")
def student_bus():

    # --------------------------------
    # Check Student Login
    # --------------------------------

    if "student_id" not in session:

        flash("Please login first.", "danger")

        return redirect(url_for("login"))

    # --------------------------------
    # Database Connection
    # --------------------------------

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --------------------------------
    # Student Details
    # --------------------------------

    cursor.execute("""
        SELECT
            student_name,
            roll_number,
            profile_image
        FROM students
        WHERE id=%s
    """, (session["student_id"],))

    student = cursor.fetchone()

    # --------------------------------
    # Bus Information
    # --------------------------------

    cursor.execute("""

        SELECT

            b.bus_number,
            b.capacity,
            b.driver_name,

            r.route_name,
            r.source,
            r.destination,
            r.distance,
            r.estimated_time,

            lbl.current_stop,
            lbl.speed,

            TIME_FORMAT(lbl.eta,'%h:%i %p') AS eta,

            CASE
                WHEN lbl.speed > 0 THEN 'On Time'
                ELSE 'Delayed'
            END AS bus_status

        FROM student_bus_assignment sba

        INNER JOIN buses b
            ON sba.bus_id = b.bus_id

        LEFT JOIN routes r
            ON b.route_id = r.route_id

        LEFT JOIN live_bus_location lbl
            ON b.bus_id = lbl.bus_id

        WHERE sba.student_id=%s

        LIMIT 1

    """, (session["student_id"],))

    bus = cursor.fetchone()

    cursor.close()
    conn.close()

    # --------------------------------
    # No Bus Assigned
    # --------------------------------

    if not bus:

        flash("No bus assigned yet.", "warning")

    # --------------------------------
    # Load Page
    # --------------------------------

    return render_template(

        "student/student_bus.html",

        student=student,

        bus=bus,

        active_page="bus"

    )
# =====================================================
# STUDENT ROUTE DETAILS
# =====================================================

@app.route("/student/route")
def student_route():

    # --------------------------------
    # Check Student Login
    # --------------------------------

    if "student_id" not in session:

        flash("Please login first.", "danger")

        return redirect(url_for("login"))

    # --------------------------------
    # Database Connection
    # --------------------------------

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --------------------------------
    # Student Details
    # --------------------------------

    cursor.execute("""
        SELECT
            student_name,
            roll_number,
            profile_image
        FROM students
        WHERE id=%s
    """, (session["student_id"],))

    student = cursor.fetchone()

    # --------------------------------
    # Route Details
    # --------------------------------

    cursor.execute("""

        SELECT

            r.route_name,
            r.source,
            r.destination,
            r.distance,
            r.estimated_time,
            r.status,

            b.bus_number,
            b.driver_name,
            b.capacity

        FROM student_bus_assignment sba

        INNER JOIN buses b
            ON sba.bus_id = b.bus_id

        INNER JOIN routes r
            ON b.route_id = r.route_id

        WHERE sba.student_id=%s

        LIMIT 1

    """, (session["student_id"],))

    route = cursor.fetchone()

    cursor.close()
    conn.close()

    # --------------------------------
    # No Route Assigned
    # --------------------------------

    if not route:

        flash("No route assigned yet.", "warning")

    # --------------------------------
    # Load Page
    # --------------------------------

    return render_template(

        "student/student_route.html",

        student=student,

        route=route,

        active_page="route"

    )
# =====================================================
# STUDENT NOTIFICATIONS
# =====================================================

@app.route("/student/notifications")
def student_notifications():

    # --------------------------------
    # Check Student Login
    # --------------------------------

    if "student_id" not in session:

        flash("Please login first.", "danger")

        return redirect(url_for("login"))

    # --------------------------------
    # Database Connection
    # --------------------------------

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    # --------------------------------
    # Student Details
    # --------------------------------

    cursor.execute("""

        SELECT

            student_name,
            roll_number,
            profile_image

        FROM students

        WHERE id=%s

    """, (session["student_id"],))

    student = cursor.fetchone()

    # --------------------------------
    # Notifications
    # --------------------------------

    cursor.execute("""

        SELECT

            id,
            title,
            message,
            notification_type,
            created_at

        FROM notifications

        ORDER BY created_at DESC

    """)

    notifications = cursor.fetchall()

    cursor.close()

    conn.close()

    # --------------------------------
    # Load Page
    # --------------------------------

    return render_template(

        "student/student_notifications.html",

        student=student,

        notifications=notifications,

        active_page="notifications"

    )
# ==========================================================
# STUDENT - TRAVEL HISTORY
# ==========================================================

@app.route("/travel-history")
def travel_history():

    if "student_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("student_login"))

    student_id = session["student_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # =====================================================
    # STUDENT PROFILE
    # =====================================================

    cursor.execute("""
        SELECT

            s.student_name,
            s.roll_number,
            s.profile_image,

            b.bus_number,
            b.driver_name,

            r.route_name

        FROM students s

        LEFT JOIN buses b
            ON s.bus_id = b.bus_id

        LEFT JOIN routes r
            ON s.route_id = r.route_id

        WHERE s.id = %s
    """, (student_id,))

    student = cursor.fetchone()

    # =====================================================
    # TRAVEL HISTORY
    # =====================================================

    cursor.execute("""
        SELECT

            th.id,
            th.travel_date,
            th.boarding_time,
            th.drop_time,
            th.status,

            b.bus_number,

            r.route_name,
            r.source,
            r.destination

        FROM travel_history th

        LEFT JOIN buses b
            ON th.bus_id = b.bus_id

        LEFT JOIN routes r
            ON b.route_id = r.route_id

        WHERE th.student_id = %s

        ORDER BY
            th.travel_date DESC,
            th.boarding_time DESC
    """, (student_id,))

    travel_history = cursor.fetchall()

    # =====================================================
    # SUMMARY
    # =====================================================

    total_trips = len(travel_history)

    completed_trips = sum(
        1
        for trip in travel_history
        if trip["status"] == "Completed"
    )

    last_trip_date = (
        travel_history[0]["travel_date"]
        if travel_history
        else None
    )

    route_counter = {}

    for trip in travel_history:

        route = trip.get("route_name")

        if route:
            route_counter[route] = route_counter.get(route, 0) + 1

    favourite_route = (
        max(route_counter, key=route_counter.get)
        if route_counter
        else None
    )

    cursor.close()
    conn.close()

    return render_template(
        "student/travel_history.html",

        student=student,

        travel_history=travel_history,

        total_trips=total_trips,

        completed_trips=completed_trips,

        last_trip_date=last_trip_date,

        favourite_route=favourite_route
    )
# ==========================================================
# STUDENT EMERGENCY PAGE
# ==========================================================
@app.route("/student/emergency")
def student_emergency():

    # ------------------------------------------
    # Check Student Login
    # ------------------------------------------
    if "student_id" not in session:
        return redirect(url_for("student_login"))

    # ------------------------------------------
    # Database Connection
    # ------------------------------------------
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ------------------------------------------
    # Fetch Logged-in Student Details
    # ------------------------------------------
    cursor.execute("""
        SELECT *
        FROM students
        WHERE id = %s
    """, (session["student_id"],))

    student = cursor.fetchone()

    # ------------------------------------------
    # Fetch Assigned Route and Driver Details
    # ------------------------------------------
    cursor.execute("""
        SELECT r.*
        FROM routes r
        JOIN students s
        ON r.route_id = s.route_id
        WHERE s.id = %s
    """, (session["student_id"],))

    route = cursor.fetchone()

    # ------------------------------------------
    # Close Database Connection
    # ------------------------------------------
    cursor.close()
    conn.close()

    # ------------------------------------------
    # Load Emergency Page
    # ------------------------------------------
    return render_template(
        "student/emergency.html",
        student=student,
        route=route
    )
# ==========================================================
# STUDENT SETTINGS PAGE
# ==========================================================
@app.route("/student/settings")
def student_settings():

    # ------------------------------------------
    # Check Student Login
    # ------------------------------------------
    if "student_id" not in session:
        return redirect(url_for("student_login"))

    # ------------------------------------------
    # Database Connection
    # ------------------------------------------
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ------------------------------------------
    # Fetch Logged-in Student Details
    # ------------------------------------------
    cursor.execute("""
        SELECT *
        FROM students
        WHERE id = %s
    """, (session["student_id"],))

    student = cursor.fetchone()

    # ------------------------------------------
    # Fetch Assigned Route Details
    # ------------------------------------------
    cursor.execute("""
        SELECT r.*
        FROM routes r
        JOIN students s
            ON r.route_id = s.route_id
        WHERE s.id = %s
    """, (session["student_id"],))

    route = cursor.fetchone()

    # ------------------------------------------
    # Close Database Connection
    # ------------------------------------------
    cursor.close()
    conn.close()

    # ------------------------------------------
    # Load Settings Page
    # ------------------------------------------
    return render_template(
        "student/settings.html",
        student=student,
        route=route
    )

# ==========================================
# DRIVER DASHBOARD
# ==========================================

@app.route("/driver_dashboard")
def driver_dashboard():

    if "driver_id" not in session:
        return redirect("/login")

    return f"""
    <h1>Welcome {session['driver_name']}</h1>
    <h2>Driver Dashboard - Coming Soon 🚍</h2>
    """


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully.", "success")

    return redirect("/login")


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)