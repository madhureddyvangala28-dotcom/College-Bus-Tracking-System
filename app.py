from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os
import json
import random
import smtplib
import uuid
import qrcode
import secrets
import base64
import firebase_admin

from dotenv import load_dotenv

load_dotenv()
from firebase_admin import credentials, messaging
from io import BytesIO
from base64 import b64encode
from email.message import EmailMessage
from werkzeug.utils import secure_filename
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta


# ================================
# FIREBASE ADMIN INITIALIZATION
# ================================

FIREBASE_SERVICE_ACCOUNT = os.path.join(
    os.path.dirname(__file__),
    "firebase",
    "firebase-service-account.json"
)

FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT_JSON"
)

if not firebase_admin._apps:

    if FIREBASE_SERVICE_ACCOUNT_JSON:
        # Railway / production
        firebase_credentials = json.loads(
            FIREBASE_SERVICE_ACCOUNT_JSON
        )

        cred = credentials.Certificate(
            firebase_credentials
        )

        print("Firebase credentials loaded from environment variable")

    else:
        # Local development
        cred = credentials.Certificate(
            FIREBASE_SERVICE_ACCOUNT
        )

        print("Firebase credentials loaded from local JSON file")

    firebase_admin.initialize_app(cred)

    print("Firebase Admin SDK initialized successfully")
# ==========================================
# SEND FIREBASE PUSH NOTIFICATION
# ==========================================

def send_push_notification(fcm_token, title, body):

    try:

        message = messaging.Message(

            notification=messaging.Notification(
                title=title,
                body=body
            ),

            token=fcm_token

        )

        response = messaging.send(message)

        print(
            "Firebase notification sent successfully:",
            response
        )

        return True

    except Exception as error:

        print(
            "Firebase notification error:",
            error
        )

        return False
    
# ==========================================
# SEND PUSH NOTIFICATION TO STUDENT
# ==========================================

def send_push_to_student(student_id, title, body):

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)

        # Get all registered devices/tokens
        # for this student
        cursor.execute("""
            SELECT fcm_token
            FROM student_fcm_tokens
            WHERE student_id = %s
        """, (student_id,))

        tokens = cursor.fetchall()

        if not tokens:

            print(
                f"No FCM token found for student ID: {student_id}"
            )

            return False

        success_count = 0

        # Send notification to every registered device
        for token_row in tokens:

            fcm_token = token_row["fcm_token"]

            if send_push_notification(
                fcm_token,
                title,
                body
            ):

                success_count += 1

        print(
            f"Push notifications sent successfully: "
            f"{success_count}"
        )

        return success_count > 0

    except Exception as error:

        print(
            "Error sending push notification to student:",
            error
        )

        return False

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
            
# ==========================================================
# SEND TARGETED EMERGENCY NOTIFICATION
# ==========================================================

def send_targeted_emergency_notification(
    emergency_id,
    admin_id
):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # ==================================================
        # GET EMERGENCY DETAILS
        # ==================================================

        cursor.execute("""
            SELECT
                ea.id,
                ea.driver_id,
                ea.emergency_type,
                ea.bus_id,
                ea.route_id,
                ea.latitude,
                ea.longitude,
                ea.message,
                d.driver_name,
                d.bus_number,
                r.route_name
            FROM emergency_alerts ea

            LEFT JOIN drivers d
                ON ea.driver_id = d.id

            LEFT JOIN routes r
                ON ea.route_id = r.route_id

            WHERE ea.id = %s
        """, (emergency_id,))

        emergency = cursor.fetchone()


        if not emergency:

            return {
                "success": False,
                "message": "Emergency alert not found."
            }


        # ==================================================
        # CHECK BUS
        # ==================================================

        bus_id = emergency["bus_id"]


        if not bus_id:

            return {
                "success": False,
                "message": "Emergency does not have an assigned bus."
            }


        # ==================================================
        # CREATE NOTIFICATION
        # ==================================================

        title = (
            f"🚨 {emergency['emergency_type']} - "
            f"Bus Emergency"
        )


        message = (
            f"Emergency reported by "
            f"{emergency['driver_name'] or 'Driver'}. "
            f"Bus: {emergency['bus_number'] or 'Unknown'}. "
            f"Route: {emergency['route_name'] or 'Unknown'}. "
            f"{emergency['message'] or ''}"
        )


        cursor.execute("""
            INSERT INTO notifications
            (
                title,
                message,
                notification_type,
                target_audience,
                created_by,
                status
            )
            VALUES
            (
                %s,
                %s,
                'Emergency',
                'Targeted',
                %s,
                'Active'
            )
        """, (
            title,
            message,
            admin_id
        ))


        notification_id = cursor.lastrowid


        # ==================================================
        # FIND STUDENTS ON AFFECTED BUS
        # ==================================================

        cursor.execute("""
            SELECT id
            FROM students
            WHERE bus_id = %s
        """, (bus_id,))

        students = cursor.fetchall()


        student_ids = []


        # ==================================================
        # CREATE STUDENT NOTIFICATIONS
        # ==================================================

        for student in students:

            student_id = student["id"]

            student_ids.append(student_id)

            cursor.execute("""
                INSERT INTO student_notifications
                (
                    student_id,
                    notification_id,
                    is_read
                )
                VALUES
                (
                    %s,
                    %s,
                    0
                )
            """, (
                student_id,
                notification_id
            ))


        # ==================================================
        # FIND PARENTS OF THOSE STUDENTS
        # ==================================================

        cursor.execute("""
            SELECT
                DISTINCT p.parent_id
            FROM parents p
            INNER JOIN students s
                ON p.student_id = s.id
            WHERE s.bus_id = %s
        """, (bus_id,))

        parents = cursor.fetchall()


        parent_ids = []


        # ==================================================
        # CREATE PARENT NOTIFICATIONS
        # ==================================================

        for parent in parents:

            parent_id = parent["parent_id"]

            parent_ids.append(parent_id)

            cursor.execute("""
                INSERT INTO parent_notifications
                (
                    parent_id,
                    notification_id,
                    is_read
                )
                VALUES
                (
                    %s,
                    %s,
                    0
                )
            """, (
                parent_id,
                notification_id
            ))


        # ==================================================
        # COMMIT DATABASE CHANGES
        # ==================================================

        conn.commit()


        # ==================================================
        # SEND FIREBASE TO STUDENTS ON THAT BUS
        # ==================================================

        student_push_count = 0


        cursor.execute("""
            SELECT DISTINCT
                sft.fcm_token
            FROM student_fcm_tokens sft

            INNER JOIN students s
                ON sft.student_id = s.id

            WHERE s.bus_id = %s
              AND sft.fcm_token IS NOT NULL
              AND sft.fcm_token != ''
        """, (bus_id,))

        student_tokens = cursor.fetchall()


        for token_row in student_tokens:

            fcm_token = token_row["fcm_token"]

            try:

                send_push_notification(
                    fcm_token,
                    title,
                    message
                )

                student_push_count += 1

                print(
                    "Emergency Firebase sent to Student successfully."
                )

            except Exception as push_error:

                print(
                    "Student Emergency Firebase Error:",
                    str(push_error)
                )


        # ==================================================
        # SEND FIREBASE TO PARENTS OF THAT BUS
        # ==================================================

        parent_push_count = 0


        cursor.execute("""
            SELECT DISTINCT
                pft.fcm_token
            FROM parent_fcm_tokens pft

            INNER JOIN parents p
                ON pft.parent_id = p.parent_id

            INNER JOIN students s
                ON p.student_id = s.id

            WHERE s.bus_id = %s
              AND pft.fcm_token IS NOT NULL
              AND pft.fcm_token != ''
        """, (bus_id,))

        parent_tokens = cursor.fetchall()


        for token_row in parent_tokens:

            fcm_token = token_row["fcm_token"]

            try:

                send_push_notification(
                    fcm_token,
                    title,
                    message
                )

                parent_push_count += 1

                print(
                    "Emergency Firebase sent to Parent successfully."
                )

            except Exception as push_error:

                print(
                    "Parent Emergency Firebase Error:",
                    str(push_error)
                )


        # ==================================================
        # RETURN RESULT
        # ==================================================

        return {
            "success": True,
            "notification_id": notification_id,
            "students_notified": len(student_ids),
            "parents_notified": len(parent_ids),
            "student_push_sent": student_push_count,
            "parent_push_sent": parent_push_count
        }


    except Exception as error:

        conn.rollback()

        print(
            "Targeted Emergency Notification Error:",
            str(error)
        )

        return {
            "success": False,
            "message": str(error)
        }


    finally:

        cursor.close()
        conn.close()
# =====================================================
# PASSWORD HASHER
# =====================================================

ph = PasswordHasher()


# =====================================================
# FLASK APP
# =====================================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

# =====================================================
# EMAIL OTP CONFIGURATION
# =====================================================

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
# =====================================================
# STUDENT IMAGE CONFIGURATION
# =====================================================

UPLOAD_FOLDER = "static/images/students"

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)




# =====================================================
# SEND PASSWORD RESET OTP EMAIL
# =====================================================

def send_reset_otp_email(email, otp, name):

    try:

        message = EmailMessage()

        message["Subject"] = "Password Reset OTP - College Bus Tracking System"

        message["From"] = EMAIL_ADDRESS

        message["To"] = email


        message.set_content(f"""
Hello {name},

You requested to reset your password for the College Bus Tracking System.

Your OTP is:

{otp}

This OTP is valid for 5 minutes.

Do not share this OTP with anyone.

Thank you,
College Bus Tracking System
""")


        # Gmail SMTP Connection
        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as smtp:

            smtp.login(
                EMAIL_ADDRESS,
                EMAIL_APP_PASSWORD
            )

            smtp.send_message(message)


        print("\n" + "=" * 55)
        print("          OTP EMAIL SENT SUCCESSFULLY")
        print("=" * 55)
        print("Email :", email)
        print("=" * 55 + "\n")


        return True


    except Exception as e:

        print("\n" + "=" * 55)
        print("             OTP EMAIL ERROR")
        print("=" * 55)
        print("ERROR:", e)
        print("=" * 55 + "\n")

        raise e
# =====================================================
# IMAGE VALIDATION
# =====================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower() in ALLOWED_EXTENSIONS
    )


# =====================================================
# DATABASE CONNECTION
# =====================================================

def get_db_connection():

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
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
# ADMIN - DRIVER PROFILE
# =====================================================

@app.route("/driver_profile/<int:id>")
def admin_driver_profile(id):

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
        WHERE d.id = %s
    """, (id,))

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

# ==========================================
# ADMIN - BUS STOPS
# ==========================================

@app.route("/admin/bus_stops")
def admin_bus_stops():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            bus_stops.*,
            routes.route_name
        FROM bus_stops
        LEFT JOIN routes
        ON bus_stops.route_id = routes.route_id
        ORDER BY
            bus_stops.route_id,
            bus_stops.stop_order
    """)

    stops = cursor.fetchall()
    
    cursor.execute("""
        SELECT *
        FROM routes
        ORDER BY route_name
    """)
    routes = cursor.fetchall()
        

    cursor.close()
    conn.close()

    return render_template(
        "admin/bus_stops.html",
        stops=stops,
        routes=routes
    )
    
# ==========================================
# ADD BUS STOP
# ==========================================

@app.route("/admin/add_bus_stop", methods=["POST"])
def add_bus_stop():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    route_id = request.form["route_id"]
    stop_name = request.form["stop_name"]
    stop_order = request.form["stop_order"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bus_stops
        (
            route_id,
            stop_name,
            stop_order
        )
        VALUES
        (%s,%s,%s)
    """,
    (
        route_id,
        stop_name,
        stop_order
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Bus Stop Added Successfully.","success")

    return redirect(url_for("admin_bus_stops"))

# ==========================================
# UPDATE BUS STOP
# ==========================================

@app.route("/admin/update_bus_stop", methods=["POST"])
def update_bus_stop():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    stop_id = request.form["stop_id"]
    route_id = request.form["route_id"]
    stop_name = request.form["stop_name"]
    stop_order = request.form["stop_order"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bus_stops
        SET
            route_id=%s,
            stop_name=%s,
            stop_order=%s
        WHERE id=%s
    """,
    (
        route_id,
        stop_name,
        stop_order,
        stop_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Bus Stop Updated Successfully.","success")

    return redirect(url_for("admin_bus_stops"))

# ==========================================
# DELETE BUS STOP
# ==========================================

@app.route("/admin/delete_bus_stop/<int:stop_id>")
def delete_bus_stop(stop_id):

    if "admin_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM bus_stops
        WHERE id=%s
    """, (stop_id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Bus Stop Deleted Successfully.","success")

    return redirect(url_for("admin_bus_stops"))

# ==========================================
# ROUTE & STOP COORDINATE MANAGER
# ==========================================

@app.route("/admin/route_coordinate_manager")
def route_coordinate_manager():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Load all routes
    cursor.execute("""
        SELECT *
        FROM routes
        ORDER BY route_name
    """)

    routes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/route_coordinate_manager.html",
        routes=routes
    )
    
# ==========================================
# GET ROUTE STOPS
# ==========================================

@app.route("/admin/get_route_stops/<int:route_id>")
def get_route_stops(route_id):

    if "admin_id" not in session:
        return {"status":"error"}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""

        SELECT *

        FROM bus_stops

        WHERE route_id=%s

        ORDER BY stop_order

    """,(route_id,))

    stops = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(stops)

# ==========================================
# SAVE STOP COORDINATES
# ==========================================

@app.route("/admin/save_stop_coordinates", methods=["POST"])
def save_stop_coordinates():

    if "admin_id" not in session:
        return jsonify({
            "status": "error",
            "message": "Please login as admin."
        }), 401

    data = request.get_json()

    stop_id = data.get("stop_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    # ------------------------------------------
    # VALIDATION
    # ------------------------------------------

    if not stop_id:
        return jsonify({
            "status": "error",
            "message": "Stop ID is missing."
        }), 400

    if latitude in [None, ""] or longitude in [None, ""]:
        return jsonify({
            "status": "error",
            "message": "Please select a location on the map."
        }), 400

    try:

        latitude = float(latitude)
        longitude = float(longitude)

    except ValueError:

        return jsonify({
            "status": "error",
            "message": "Invalid coordinates."
        }), 400

    # ------------------------------------------
    # CHECK COORDINATE RANGE
    # ------------------------------------------

    if latitude < -90 or latitude > 90:

        return jsonify({
            "status": "error",
            "message": "Invalid latitude."
        }), 400

    if longitude < -180 or longitude > 180:

        return jsonify({
            "status": "error",
            "message": "Invalid longitude."
        }), 400

    # ------------------------------------------
    # DATABASE
    # ------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE bus_stops
            SET latitude = %s,
                longitude = %s
            WHERE id = %s
        """, (
            latitude,
            longitude,
            stop_id
        ))

        conn.commit()

        if cursor.rowcount == 0:

            return jsonify({
                "status": "error",
                "message": "Stop not found."
            }), 404

        return jsonify({
            "status": "success",
            "message": "Coordinates saved successfully."
        })

    except Exception as e:

        conn.rollback()

        print("Save coordinates error:", e)

        return jsonify({
            "status": "error",
            "message": "Failed to save coordinates."
        }), 500

    finally:

        cursor.close()
        conn.close()
        
# =====================================================
# ADMIN LIVE FLEET TRACKING
# =====================================================

@app.route("/admin/live_fleet")
def admin_live_fleet():

    # ----------------------------------------
    # Protect Admin Page
    # ----------------------------------------

    if "admin_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ----------------------------------------
    # Get All Routes
    # ----------------------------------------

    cursor.execute("""
        SELECT
            route_id,
            route_name,
            source,
            destination,
            distance,
            estimated_time
        FROM routes
        ORDER BY route_name
    """)

    routes = cursor.fetchall()

    # ----------------------------------------
    # Get All Bus Stops
    # ----------------------------------------

    cursor.execute("""
        SELECT
            id,
            route_id,
            stop_name,
            stop_order,
            latitude,
            longitude
        FROM bus_stops
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
        ORDER BY route_id, stop_order
    """)

    stops = cursor.fetchall()

    # ----------------------------------------
    # Get All Buses + Live Location
    # ----------------------------------------

    cursor.execute("""
        SELECT

            b.bus_id,
            b.bus_number,
            b.driver_name,
            b.capacity,

            r.route_id,
            r.route_name,
            r.source,
            r.destination,

            lbl.latitude,
            lbl.longitude,
            lbl.current_stop,
            lbl.speed,
            lbl.trip_status,

            TIME_FORMAT(lbl.eta, '%h:%i %p') AS eta,

            TIME_FORMAT(lbl.updated_at, '%h:%i %p') AS last_updated,

            lbl.updated_at

        FROM buses b

        LEFT JOIN routes r
            ON b.route_id = r.route_id

        LEFT JOIN live_bus_location lbl
            ON b.bus_id = lbl.bus_id

        ORDER BY b.bus_number
    """)

    buses = cursor.fetchall()

    cursor.close()
    conn.close()

    # ----------------------------------------
    # Calculate Initial Statistics
    # ----------------------------------------

    total_buses = len(buses)

    online_buses = 0
    moving_buses = 0
    stopped_buses = 0
    offline_buses = 0

    for bus in buses:

        trip_status = bus.get("trip_status")
        speed = bus.get("speed") or 0

        if trip_status == "Online":

            online_buses += 1

            if float(speed) > 0:
                moving_buses += 1
            else:
                stopped_buses += 1

        else:

            offline_buses += 1

    # ----------------------------------------
    # Render Page
    # ----------------------------------------

    return render_template(
        "admin/live_fleet.html",

        buses=buses,
        routes=routes,
        stops=stops,

        total_buses=total_buses,
        online_buses=online_buses,
        moving_buses=moving_buses,
        stopped_buses=stopped_buses,
        offline_buses=offline_buses,

        active_page="live_fleet"
    )
    
# =====================================================
# ADMIN LIVE FLEET DATA API
# =====================================================

@app.route("/admin/live_fleet/data")
def admin_live_fleet_data():

    if "admin_id" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT

            b.bus_id,
            b.bus_number,
            b.driver_name,
            b.capacity,

            r.route_id,
            r.route_name,
            r.source,
            r.destination,

            lbl.latitude,
            lbl.longitude,
            lbl.current_stop,
            lbl.speed,
            lbl.trip_status,

            TIME_FORMAT(
                lbl.eta,
                '%h:%i %p'
            ) AS eta,

            TIME_FORMAT(
                lbl.updated_at,
                '%h:%i %p'
            ) AS last_updated

        FROM buses b

        LEFT JOIN routes r
            ON b.route_id = r.route_id

        LEFT JOIN live_bus_location lbl
            ON b.bus_id = lbl.bus_id

        ORDER BY b.bus_number
    """)

    buses = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "buses": buses
    })
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
    cursor = conn.cursor(dictionary=True)

    try:

        # =================================================
        # BASIC SYSTEM COUNTS
        # =================================================

        # Students
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM students
        """)

        student_count = cursor.fetchone()["total"]


        # Drivers
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM drivers
        """)

        driver_count = cursor.fetchone()["total"]


        # Buses
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM buses
        """)

        bus_count = cursor.fetchone()["total"]


        # Routes
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM routes
        """)

        route_count = cursor.fetchone()["total"]


        # =================================================
        # DRIVER STATUS
        # =================================================

        # Available Drivers
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM drivers
            WHERE status = %s
        """, ("Available",))

        available_count = cursor.fetchone()["total"]


        # Drivers On Trip
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM drivers
            WHERE status = %s
        """, ("On Trip",))

        trip_count = cursor.fetchone()["total"]


        # Drivers On Leave
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM drivers
            WHERE status = %s
        """, ("On Leave",))

        leave_count = cursor.fetchone()["total"]


        # =================================================
        # LIVE FLEET
        # =================================================

        # Buses currently moving
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM buses b

            INNER JOIN live_bus_location lbl
                ON b.bus_id = lbl.bus_id

            WHERE lbl.speed > 0
        """)

        moving_count = cursor.fetchone()["total"]


        # Buses currently stopped
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM buses b

            INNER JOIN live_bus_location lbl
                ON b.bus_id = lbl.bus_id

            WHERE lbl.speed = 0
        """)

        stopped_count = cursor.fetchone()["total"]


        # Buses without live location
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM buses b

            LEFT JOIN live_bus_location lbl
                ON b.bus_id = lbl.bus_id

            WHERE lbl.bus_id IS NULL
        """)

        offline_count = cursor.fetchone()["total"]


        # =================================================
        # LIVE BUS ACTIVITY
        # =================================================

        cursor.execute("""
            SELECT

                b.bus_id,

                b.bus_number,

                b.driver_name,

                r.route_name,

                lbl.current_stop,

                lbl.speed,

                TIME_FORMAT(
                    lbl.eta,
                    '%h:%i %p'
                ) AS eta,

                CASE

                    WHEN lbl.bus_id IS NULL
                        THEN 'Offline'

                    WHEN lbl.speed > 0
                        THEN 'Moving'

                    ELSE 'Stopped'

                END AS live_status

            FROM buses b

            LEFT JOIN routes r
                ON b.route_id = r.route_id

            LEFT JOIN live_bus_location lbl
                ON b.bus_id = lbl.bus_id

            ORDER BY

                CASE

                    WHEN lbl.speed > 0
                        THEN 1

                    WHEN lbl.speed = 0
                        THEN 2

                    ELSE 3

                END,

                b.bus_number

            LIMIT 10
        """)

        live_buses = cursor.fetchall()


    finally:

        cursor.close()
        conn.close()


    # =================================================
    # RENDER DASHBOARD
    # =================================================

    return render_template(

        "admin/dashboard/dashboard.html",

        active_page="dashboard",

        # Basic statistics
        student_count=student_count,
        driver_count=driver_count,
        bus_count=bus_count,
        route_count=route_count,

        # Driver status
        available_count=available_count,
        trip_count=trip_count,
        leave_count=leave_count,

        # Live fleet
        moving_count=moving_count,
        stopped_count=stopped_count,
        offline_count=offline_count,

        # Live bus activity
        live_buses=live_buses
    )
# =====================================================
# ADMIN SEAT AVAILABILITY
# =====================================================

@app.route("/admin/seat_availability")
def admin_seat_availability():

    # ------------------------------------------
    # Admin Login Check
    # ------------------------------------------

    if "admin_id" not in session:

        return redirect(url_for("login"))


    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)


    try:

        # ------------------------------------------
        # GET ALL BUS SEAT DETAILS
        # ------------------------------------------

        cursor.execute("""

            SELECT

                b.bus_id,

                b.bus_number,

                b.capacity,

                b.occupied_seats,

                b.available_seats,

                b.driver_name,

                r.route_name

            FROM buses b

            LEFT JOIN routes r

                ON b.route_id = r.route_id

            ORDER BY b.bus_number ASC

        """)


        buses = cursor.fetchall()


    finally:

        cursor.close()

        conn.close()


    # ------------------------------------------
    # LOAD ADMIN PAGE
    # ------------------------------------------

    return render_template(

        "admin/seat_availability.html",

        buses=buses,

        active_page="seat_availability"

    )
    
# =====================================================
# ADMIN NOTIFICATIONS
# =====================================================

@app.route("/admin/notifications")
def admin_notifications():

    # ==========================================
    # CHECK ADMIN LOGIN
    # ==========================================

    if "admin_id" not in session:
        return redirect(url_for("login"))


    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # ==========================================
        # GET ALL NOTIFICATIONS
        # ==========================================

        cursor.execute("""
            SELECT
                id,
                title,
                message,
                notification_type,
                target_audience,
                created_at,
                status

            FROM notifications

            ORDER BY created_at DESC
        """)

        notifications = cursor.fetchall()


        # ==========================================
        # GET TOTAL NOTIFICATIONS
        # ==========================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM notifications
        """)

        total_notifications = cursor.fetchone()["total"]


        # ==========================================
        # GET ACTIVE NOTIFICATIONS
        # ==========================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM notifications
            WHERE status = 'Active'
        """)

        active_notifications = cursor.fetchone()["total"]


        # ==========================================
        # GET EMERGENCY NOTIFICATIONS
        # ==========================================

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM notifications
            WHERE notification_type = 'Emergency'
            AND status = 'Active'
        """)

        emergency_notifications = cursor.fetchone()["total"]


    finally:

        cursor.close()
        conn.close()


    # ==========================================
    # RENDER PAGE
    # ==========================================

    return render_template(

        "admin/notifications/notifications.html",

        active_page="notifications",

        notifications=notifications,

        total_notifications=total_notifications,

        active_notifications=active_notifications,

        emergency_notifications=emergency_notifications
    )
# =====================================================
# CREATE ADMIN NOTIFICATION
# =====================================================

@app.route("/admin/notifications/create", methods=["POST"])
def create_admin_notification():

    # ==========================================
    # CHECK ADMIN LOGIN
    # ==========================================

    if "admin_id" not in session:
        return redirect(url_for("login"))


    # ==========================================
    # GET FORM DATA
    # ==========================================

    title = request.form.get("title")
    message = request.form.get("message")
    notification_type = request.form.get(
        "notification_type",
        "Info"
    )
    target_audience = request.form.get(
        "target_audience",
        "All"
    )


    # ==========================================
    # VALIDATE DATA
    # ==========================================

    if not title or not message:

        flash(
            "Title and message are required.",
            "error"
        )

        return redirect(
            url_for("admin_notifications")
        )


    # ==========================================
    # SAVE NOTIFICATION
    # ==========================================

    conn = get_db_connection()
    cursor = conn.cursor()


    try:

        cursor.execute("""

            INSERT INTO notifications (

                title,
                message,
                notification_type,
                target_audience,
                created_by,
                status

            )

            VALUES (

                %s,
                %s,
                %s,
                %s,
                %s,
                'Active'

            )

        """, (

            title,
            message,
            notification_type,
            target_audience,
            session["admin_id"]

        ))


        conn.commit()


        flash(
            "Notification sent successfully!",
            "success"
        )


    except Exception as e:

        conn.rollback()

        flash(
            f"Error sending notification: {str(e)}",
            "error"
        )


    finally:

        cursor.close()
        conn.close()


    return redirect(
        url_for("admin_notifications")
    )
    
    
# =====================================================
# ADMIN - SEND NOTIFICATION
# =====================================================

@app.route("/admin/notifications/send", methods=["GET", "POST"])
def send_admin_notification():

    # ==========================================
    # CHECK ADMIN LOGIN
    # ==========================================

    if "admin_id" not in session:

        return redirect(url_for("login"))


    # ==========================================
    # GET → OPEN SEND NOTIFICATION PAGE
    # ==========================================

    if request.method == "GET":

        return render_template(
            "admin/notifications/send_notification.html",
            active_page="notifications"
        )


    # ==========================================
    # POST → GET FORM DATA
    # ==========================================

    title = request.form.get(
        "title",
        ""
    ).strip()


    message = request.form.get(
        "message",
        ""
    ).strip()


    notification_type = request.form.get(
        "notification_type",
        "Info"
    )


    target_audience = request.form.get(
        "target_audience",
        "All"
    )


    # ==========================================
    # VALIDATION
    # ==========================================

    if not title or not message:

        flash(
            "Please enter both notification title and message.",
            "error"
        )

        return redirect(
            url_for("send_admin_notification")
        )


    # ==========================================
    # VALID NOTIFICATION TYPES
    # ==========================================

    valid_types = [

        "Info",
        "Warning",
        "Emergency",
        "Holiday"

    ]


    # ==========================================
    # VALID TARGET AUDIENCES
    # ==========================================

    valid_audiences = [

        "All",
        "Students",
        "Parents",
        "Drivers"

    ]


    # ==========================================
    # VALIDATE NOTIFICATION TYPE
    # ==========================================

    if notification_type not in valid_types:

        flash(
            "Invalid notification type.",
            "error"
        )

        return redirect(
            url_for("send_admin_notification")
        )


    # ==========================================
    # VALIDATE TARGET AUDIENCE
    # ==========================================

    if target_audience not in valid_audiences:

        flash(
            "Invalid target audience.",
            "error"
        )

        return redirect(
            url_for("send_admin_notification")
        )


    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    conn = get_db_connection()

    cursor = conn.cursor()


    try:

        # =====================================
        # CREATE MAIN NOTIFICATION
        # =====================================

        cursor.execute(
            """
            INSERT INTO notifications
            (
                title,
                message,
                notification_type,
                target_audience,
                created_by,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'Active'
            )
            """,
            (
                title,
                message,
                notification_type,
                target_audience,
                session["admin_id"]
            )
        )


        # =====================================
        # GET NOTIFICATION ID
        # =====================================

        notification_id = cursor.lastrowid


        # =====================================
        # SEND DATABASE NOTIFICATION TO STUDENTS
        # =====================================

        if target_audience in ["All", "Students"]:

            cursor.execute(
                """
                SELECT id
                FROM students
                """
            )

            students = cursor.fetchall()


            for student in students:

                if isinstance(student, dict):

                    student_id = student["id"]

                else:

                    student_id = student[0]


                cursor.execute(
                    """
                    INSERT INTO student_notifications
                    (
                        student_id,
                        notification_id,
                        is_read
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        0
                    )
                    """,
                    (
                        student_id,
                        notification_id
                    )
                )


        # =====================================
        # SEND DATABASE NOTIFICATION TO PARENTS
        # =====================================

        if target_audience in ["All", "Parents"]:

            cursor.execute(
                """
                SELECT parent_id
                FROM parents
                """
            )

            parents = cursor.fetchall()


            for parent in parents:

                if isinstance(parent, dict):

                    parent_id = parent["parent_id"]

                else:

                    parent_id = parent[0]


                cursor.execute(
                    """
                    INSERT INTO parent_notifications
                    (
                        parent_id,
                        notification_id,
                        is_read
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        0
                    )
                    """,
                    (
                        parent_id,
                        notification_id
                    )
                )


        # =====================================
        # SEND DATABASE NOTIFICATION TO DRIVERS
        # =====================================

        if target_audience in ["All", "Drivers"]:

            cursor.execute(
                """
                SELECT id
                FROM drivers
                """
            )

            drivers = cursor.fetchall()


            for driver in drivers:

                if isinstance(driver, dict):

                    driver_id = driver["id"]

                else:

                    driver_id = driver[0]


                cursor.execute(
                    """
                    INSERT INTO driver_notifications
                    (
                        driver_id,
                        notification_id,
                        is_read
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        0
                    )
                    """,
                    (
                        driver_id,
                        notification_id
                    )
                )


        # =====================================
        # COMMIT DATABASE NOTIFICATIONS FIRST
        # =====================================

        conn.commit()


        # =================================================
        # SEND FIREBASE PUSH NOTIFICATIONS TO STUDENTS
        # =================================================

        if target_audience in ["All", "Students"]:

            cursor.execute(
                """
                SELECT fcm_token
                FROM student_fcm_tokens
                """
            )

            student_tokens = cursor.fetchall()


            for token_row in student_tokens:

                if isinstance(token_row, dict):

                    fcm_token = token_row["fcm_token"]

                else:

                    fcm_token = token_row[0]


                try:

                    send_push_notification(
                        fcm_token,
                        title,
                        message
                    )


                    print(
                        "Firebase notification sent to Student successfully."
                    )


                except Exception as push_error:

                    print(
                        "Firebase Student notification error:",
                        str(push_error)
                    )


        # =================================================
        # SEND FIREBASE PUSH NOTIFICATIONS TO PARENTS
        # =================================================

        if target_audience in ["All", "Parents"]:

            cursor.execute(
                """
                SELECT fcm_token
                FROM parent_fcm_tokens
                """
            )

            parent_tokens = cursor.fetchall()


            for token_row in parent_tokens:

                if isinstance(token_row, dict):

                    fcm_token = token_row["fcm_token"]

                else:

                    fcm_token = token_row[0]


                try:

                    send_push_notification(
                        fcm_token,
                        title,
                        message
                    )


                    print(
                        "Firebase notification sent to Parent successfully."
                    )


                except Exception as push_error:

                    print(
                        "Firebase Parent notification error:",
                        str(push_error)
                    )


        # =================================================
        # SEND FIREBASE PUSH NOTIFICATIONS TO DRIVERS
        # =================================================

        if target_audience in ["All", "Drivers"]:

            cursor.execute(
                """
                SELECT fcm_token
                FROM driver_fcm_tokens
                """
            )

            driver_tokens = cursor.fetchall()


            for token_row in driver_tokens:

                if isinstance(token_row, dict):

                    fcm_token = token_row["fcm_token"]

                else:

                    fcm_token = token_row[0]


                try:

                    # =====================================
                    # SEND FIREBASE NOTIFICATION
                    # =====================================

                    send_push_notification(
                        fcm_token,
                        title,
                        message
                    )


                    print(
                        "Firebase notification sent to Driver successfully."
                    )


                except Exception as push_error:

                    print(
                        "Firebase Driver notification error:",
                        str(push_error)
                    )


        # =====================================
        # SUCCESS MESSAGE
        # =====================================

        flash(
            "Notification sent successfully!",
            "success"
        )


        return redirect(
            url_for("admin_notifications")
        )


    # ==========================================
    # ERROR HANDLING
    # ==========================================

    except Exception as e:

        conn.rollback()


        print(
            "Notification Error:",
            str(e)
        )


        flash(
            f"Failed to send notification: {str(e)}",
            "error"
        )


        return redirect(
            url_for("send_admin_notification")
        )


    # ==========================================
    # CLOSE DATABASE CONNECTION
    # ==========================================

    finally:

        cursor.close()

        conn.close()
        

# ==========================================================
# ADMIN EMERGENCY MANAGEMENT
# ==========================================================

@app.route("/admin/emergencies")
def admin_emergencies():

    # -----------------------------------------
    # ADMIN LOGIN CHECK
    # -----------------------------------------
    if "admin_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # -----------------------------------------
        # GET ALL EMERGENCY ALERTS
        # -----------------------------------------

        cursor.execute("""
            SELECT
                ea.id,
                ea.driver_id,
                ea.emergency_type,
                ea.bus_id,
                ea.route_id,
                ea.latitude,
                ea.longitude,
                ea.message,
                ea.admin_response,
                ea.status,
                ea.resolved_at,
                ea.created_at,

                d.driver_name,
                d.phone,
                d.bus_number AS driver_bus_number,

                b.bus_number,

                r.route_name,
                r.source,
                r.destination

            FROM emergency_alerts ea

            LEFT JOIN drivers d
                ON ea.driver_id = d.id

            LEFT JOIN buses b
                ON ea.bus_id = b.bus_id

            LEFT JOIN routes r
                ON ea.route_id = r.route_id

            ORDER BY ea.created_at DESC
        """)

        emergencies = cursor.fetchall()

        # -----------------------------------------
        # SUMMARY COUNTS
        # -----------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM emergency_alerts
        """)

        total_emergencies = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS pending
            FROM emergency_alerts
            WHERE status = 'Pending'
        """)

        pending_emergencies = cursor.fetchone()["pending"]

        cursor.execute("""
            SELECT COUNT(*) AS resolved
            FROM emergency_alerts
            WHERE status = 'Resolved'
        """)

        resolved_emergencies = cursor.fetchone()["resolved"]

        cursor.execute("""
            SELECT COUNT(*) AS active
            FROM emergency_alerts
            WHERE status != 'Resolved'
        """)

        active_emergencies = cursor.fetchone()["active"]

        return render_template(
            "admin/emergencies.html",
            emergencies=emergencies,
            total_emergencies=total_emergencies,
            pending_emergencies=pending_emergencies,
            resolved_emergencies=resolved_emergencies,
            active_emergencies=active_emergencies,
            active_page="emergencies"
        )

    except Exception as error:

        print("Admin Emergency Error:", error)

        flash(
            "Unable to load emergency alerts.",
            "danger"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    finally:

        cursor.close()
        conn.close()
# ==========================================================
# ADMIN - EMERGENCY DETAILS
# ==========================================================

@app.route("/admin/emergencies/<int:emergency_id>")
def admin_emergency_details(emergency_id):

    # -----------------------------------------
    # ADMIN LOGIN CHECK
    # -----------------------------------------
    if "admin_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                ea.id,
                ea.driver_id,
                ea.emergency_type,
                ea.bus_id,
                ea.route_id,
                ea.latitude,
                ea.longitude,
                ea.message,
                ea.admin_response,
                ea.status,
                ea.resolved_at,
                ea.created_at,

                d.driver_name,
                d.phone,
                d.license_number,
                d.bus_number,

                b.bus_number AS assigned_bus_number,

                r.route_name,
                r.source,
                r.destination,
                r.estimated_time

            FROM emergency_alerts ea

            LEFT JOIN drivers d
                ON ea.driver_id = d.id

            LEFT JOIN buses b
                ON ea.bus_id = b.bus_id

            LEFT JOIN routes r
                ON ea.route_id = r.route_id

            WHERE ea.id = %s

            LIMIT 1
        """, (emergency_id,))

        emergency = cursor.fetchone()

        if not emergency:

            flash(
                "Emergency alert not found.",
                "warning"
            )

            return redirect(
                url_for("admin_emergencies")
            )

        return render_template(
            "admin/emergency_details.html",
            emergency=emergency,
            active_page="emergencies"
        )

    except Exception as error:

        print(
            "Emergency Details Error:",
            error
        )

        flash(
            "Unable to load emergency details.",
            "danger"
        )

        return redirect(
            url_for("admin_emergencies")
        )

    finally:

        cursor.close()
        conn.close()
        
# ==========================================================
# ADMIN - RESPOND TO EMERGENCY
# ==========================================================

@app.route("/admin/emergencies/<int:emergency_id>/respond", methods=["POST"])
def respond_to_emergency(emergency_id):

    # -----------------------------------------
    # ADMIN LOGIN CHECK
    # -----------------------------------------

    if "admin_id" not in session:

        return jsonify({
            "success": False,
            "message": "Admin login required."
        }), 401


    # -----------------------------------------
    # GET RESPONSE MESSAGE
    # -----------------------------------------

    data = request.get_json(silent=True) or {}

    response_message = data.get(
        "response",
        ""
    ).strip()


    # -----------------------------------------
    # VALIDATE RESPONSE
    # -----------------------------------------

    if not response_message:

        return jsonify({
            "success": False,
            "message": "Response message is required."
        }), 400


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # -----------------------------------------
        # GET EMERGENCY
        # -----------------------------------------

        cursor.execute("""
            SELECT
                ea.id,
                ea.driver_id,
                ea.emergency_type,
                ea.status,

                d.driver_name,
                d.bus_number

            FROM emergency_alerts ea

            LEFT JOIN drivers d
                ON ea.driver_id = d.id

            WHERE ea.id = %s
        """, (
            emergency_id,
        ))

        emergency = cursor.fetchone()


        # -----------------------------------------
        # CHECK EMERGENCY EXISTS
        # -----------------------------------------

        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency alert not found."
            }), 404


        # -----------------------------------------
        # CHECK IF ALREADY RESOLVED
        # -----------------------------------------

        if emergency["status"] == "Resolved":

            return jsonify({
                "success": False,
                "message": "This emergency has already been resolved."
            }), 400


        # -----------------------------------------
        # UPDATE ADMIN RESPONSE
        # -----------------------------------------

        cursor.execute("""
            UPDATE emergency_alerts

            SET
                admin_response = %s,
                status = 'Responded'

            WHERE id = %s
        """, (
            response_message,
            emergency_id
        ))


        # -----------------------------------------
        # COMMIT DATABASE CHANGE
        # -----------------------------------------

        conn.commit()


        # ==================================================
        # SEND RESPONSE TO DRIVER USING FIREBASE
        # ==================================================

        cursor.execute("""
            SELECT fcm_token
            FROM driver_fcm_tokens
            WHERE driver_id = %s
        """, (
            emergency["driver_id"],
        ))

        driver_tokens = cursor.fetchall()


        firebase_success = 0
        firebase_failed = 0


        for token_row in driver_tokens:

            fcm_token = token_row["fcm_token"]


            try:

                send_push_notification(
                    fcm_token,
                    "Emergency Response",
                    response_message
                )

                firebase_success += 1

                print(
                    "Firebase emergency response sent to Driver successfully."
                )


            except Exception as push_error:

                firebase_failed += 1

                print(
                    "Firebase Emergency Response Error:",
                    str(push_error)
                )


        # -----------------------------------------
        # SUCCESS RESPONSE
        # -----------------------------------------

        return jsonify({

            "success": True,

            "message":
                "Emergency response sent successfully.",

            "status":
                "Responded",

            "firebase_sent":
                firebase_success,

            "firebase_failed":
                firebase_failed

        })


    except Exception as error:

        conn.rollback()

        print(
            "Admin Emergency Response Error:",
            str(error)
        )


        return jsonify({

            "success": False,

            "message":
                "Unable to send emergency response."

        }), 500


    finally:

        cursor.close()
        conn.close()
        
# ==========================================================
# ADMIN RESOLVE EMERGENCY
# ==========================================================

@app.route("/admin/emergencies/<int:emergency_id>/resolve", methods=["POST"])
def resolve_emergency(emergency_id):

    # -----------------------------------------
    # ADMIN LOGIN CHECK
    # -----------------------------------------

    if "admin_id" not in session:
        return jsonify({
            "success": False,
            "message": "Admin login required."
        }), 401


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # -----------------------------------------
        # CHECK EMERGENCY EXISTS
        # -----------------------------------------

        cursor.execute("""
            SELECT *
            FROM emergency_alerts
            WHERE id = %s
        """, (emergency_id,))

        emergency = cursor.fetchone()


        if not emergency:

            return jsonify({
                "success": False,
                "message": "Emergency alert not found."
            }), 404


        # -----------------------------------------
        # ALREADY RESOLVED CHECK
        # -----------------------------------------

        if emergency["status"] and \
           emergency["status"].lower() == "resolved":

            return jsonify({
                "success": False,
                "message": "This emergency is already resolved."
            }), 400


        # -----------------------------------------
        # RESOLVE EMERGENCY
        # -----------------------------------------

        cursor.execute("""
            UPDATE emergency_alerts
            SET
                status = 'Resolved',
                resolved_at = NOW()
            WHERE id = %s
        """, (emergency_id,))


        # -----------------------------------------
        # COMMIT
        # -----------------------------------------

        conn.commit()


        # -----------------------------------------
        # SUCCESS RESPONSE
        # -----------------------------------------

        return jsonify({
            "success": True,
            "message": "Emergency resolved successfully."
        })


    except Exception as error:

        # -----------------------------------------
        # ROLLBACK
        # -----------------------------------------

        conn.rollback()

        print(
            "Resolve Emergency Error:",
            error
        )


        return jsonify({
            "success": False,
            "message": "Unable to resolve emergency."
        }), 500


    finally:

        cursor.close()
        conn.close()
        
# =====================================================
# ADMIN - NOTIFY PARENTS & STUDENTS ABOUT EMERGENCY
# =====================================================

@app.route(
    "/admin/emergencies/<int:emergency_id>/notify",
    methods=["POST"]
)
def notify_emergency_users(emergency_id):

    # ==========================================
    # CHECK ADMIN LOGIN
    # ==========================================

    if "admin_id" not in session:
        return {
            "success": False,
            "message": "Admin login required."
        }, 401


    conn = get_db_connection()
    cursor = conn.cursor()


    try:

        # ==========================================
        # GET EMERGENCY DETAILS
        # ==========================================

        cursor.execute(
            """
            SELECT
                ea.id,
                ea.driver_id,
                ea.emergency_type,
                ea.bus_id,
                ea.route_id,
                ea.latitude,
                ea.longitude,
                ea.message,
                ea.status,

                d.driver_name,

                b.bus_number,

                r.route_name

            FROM emergency_alerts ea

            LEFT JOIN drivers d
                ON ea.driver_id = d.id

            LEFT JOIN buses b
                ON ea.bus_id = b.bus_id

            LEFT JOIN routes r
                ON ea.route_id = r.route_id

            WHERE ea.id = %s

            LIMIT 1
            """,
            (emergency_id,)
        )


        emergency = cursor.fetchone()


        # ==========================================
        # EMERGENCY NOT FOUND
        # ==========================================

        if not emergency:

            return {
                "success": False,
                "message": "Emergency alert not found."
            }, 404


        # ==========================================
        # SUPPORT TUPLE / DICT CURSOR
        # ==========================================

        if isinstance(emergency, dict):

            emergency_type = emergency["emergency_type"]
            driver_name = emergency.get(
                "driver_name"
            )

            bus_number = emergency.get(
                "bus_number"
            )

            route_name = emergency.get(
                "route_name"
            )

            latitude = emergency.get(
                "latitude"
            )

            longitude = emergency.get(
                "longitude"
            )

            driver_message = emergency.get(
                "message"
            )

        else:

            emergency_type = emergency[2]
            driver_name = emergency[9]
            bus_number = emergency[10]
            route_name = emergency[11]
            latitude = emergency[5]
            longitude = emergency[6]
            driver_message = emergency[7]


        # ==========================================
        # DEFAULT VALUES
        # ==========================================

        driver_name = driver_name or "Unknown Driver"

        bus_number = bus_number or "Not Assigned"

        route_name = route_name or "Not Assigned"


        # ==========================================
        # CREATE NOTIFICATION MESSAGE
        # ==========================================

        title = (
            "🚨 Bus Emergency Alert"
        )


        message = (
            f"{emergency_type} reported by "
            f"{driver_name}. "
            f"Bus: {bus_number}. "
            f"Route: {route_name}."
        )


        # ==========================================
        # ADD LOCATION
        # ==========================================

        if (
            latitude is not None
            and longitude is not None
        ):

            message += (
                f" Location: "
                f"{latitude:.6f}, "
                f"{longitude:.6f}."
            )


        # ==========================================
        # ADD DRIVER MESSAGE
        # ==========================================

        if driver_message:

            message += (
                f" Message: {driver_message}"
            )


        # ==========================================
        # CREATE MAIN NOTIFICATION
        # ==========================================

        cursor.execute(
            """
            INSERT INTO notifications
            (
                title,
                message,
                notification_type,
                target_audience,
                created_by,
                status
            )
            VALUES
            (
                %s,
                %s,
                'Emergency',
                'All',
                %s,
                'Active'
            )
            """,
            (
                title,
                message,
                session["admin_id"]
            )
        )


        notification_id = cursor.lastrowid


        # =================================================
        # DATABASE NOTIFICATION → STUDENTS
        # =================================================

        cursor.execute(
            """
            SELECT id
            FROM students
            """
        )

        students = cursor.fetchall()


        for student in students:

            if isinstance(student, dict):
                student_id = student["id"]
            else:
                student_id = student[0]


            cursor.execute(
                """
                INSERT INTO student_notifications
                (
                    student_id,
                    notification_id,
                    is_read
                )
                VALUES
                (
                    %s,
                    %s,
                    0
                )
                """,
                (
                    student_id,
                    notification_id
                )
            )


        # =================================================
        # DATABASE NOTIFICATION → PARENTS
        # =================================================

        cursor.execute(
            """
            SELECT parent_id
            FROM parents
            """
        )

        parents = cursor.fetchall()


        for parent in parents:

            if isinstance(parent, dict):
                parent_id = parent["parent_id"]
            else:
                parent_id = parent[0]


            cursor.execute(
                """
                INSERT INTO parent_notifications
                (
                    parent_id,
                    notification_id,
                    is_read
                )
                VALUES
                (
                    %s,
                    %s,
                    0
                )
                """,
                (
                    parent_id,
                    notification_id
                )
            )


        # ==========================================
        # COMMIT DATABASE NOTIFICATIONS
        # ==========================================

        conn.commit()


        # =================================================
        # FIREBASE → STUDENTS
        # =================================================

        student_push_count = 0


        cursor.execute(
            """
            SELECT fcm_token
            FROM student_fcm_tokens
            WHERE fcm_token IS NOT NULL
            AND fcm_token != ''
            """
        )


        student_tokens = cursor.fetchall()


        for token_row in student_tokens:

            if isinstance(token_row, dict):
                fcm_token = token_row["fcm_token"]
            else:
                fcm_token = token_row[0]


            if not fcm_token:
                continue


            try:

                send_push_notification(
                    fcm_token,
                    title,
                    message
                )

                student_push_count += 1

            except Exception as push_error:

                print(
                    "Emergency Student Firebase Error:",
                    str(push_error)
                )


        # =================================================
        # FIREBASE → PARENTS
        # =================================================

        parent_push_count = 0


        cursor.execute(
            """
            SELECT fcm_token
            FROM parent_fcm_tokens
            WHERE fcm_token IS NOT NULL
            AND fcm_token != ''
            """
        )


        parent_tokens = cursor.fetchall()


        for token_row in parent_tokens:

            if isinstance(token_row, dict):
                fcm_token = token_row["fcm_token"]
            else:
                fcm_token = token_row[0]


            if not fcm_token:
                continue


            try:

                send_push_notification(
                    fcm_token,
                    title,
                    message
                )

                parent_push_count += 1

            except Exception as push_error:

                print(
                    "Emergency Parent Firebase Error:",
                    str(push_error)
                )


        # ==========================================
        # SUCCESS
        # ==========================================

        return {
            "success": True,
            "message": (
                "Emergency notification sent "
                "to parents and students."
            ),
            "notification_id": notification_id,
            "student_push_count": student_push_count,
            "parent_push_count": parent_push_count
        }


    except Exception as e:

        conn.rollback()

        print(
            "Emergency Notification Error:",
            str(e)
        )


        return {
            "success": False,
            "message": (
                "Failed to send emergency notification."
            )
        }, 500


    finally:

        cursor.close()
        conn.close()
        
        
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
    # PARENT LOGIN
    # =====================================================

    elif role == "parent":

        cursor.execute("""
            SELECT *
            FROM parents
            WHERE username=%s
        """, (username,))

        parent = cursor.fetchone()

        if parent:
            try:
                ph.verify(parent["password"], password)

                session.clear()

                session["parent_id"] = parent["parent_id"]
                session["parent_name"] = parent["parent_name"]
                session["parent_student_id"] = parent["student_id"]
                session["parent_phone"] = parent["parent_phone"]
                session["parent_profile_image"] = parent["profile_image"]

                cursor.close()
                conn.close()

                return redirect(url_for("parent_dashboard"))

            except VerifyMismatchError:
                pass

        flash("Please check your Parent Username and Password.", "danger")


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

# =====================================================
# FORGOT PASSWORD - EMAIL OTP
# =====================================================

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    # =================================================
    # GET REQUEST
    # =================================================

    if request.method == "GET":

        return render_template("forgot_password.html")


    # =================================================
    # GET FORM DATA
    # =================================================

    role = request.form.get("role", "").strip().lower()

    username = request.form.get("username", "").strip()

    email = request.form.get("email", "").strip().lower()


    # =================================================
    # BASIC VALIDATION
    # =================================================

    if not role or not username or not email:

        flash(
            "Please enter all required details.",
            "danger"
        )

        return redirect(
            url_for("forgot_password")
        )


    # =================================================
    # DATABASE CONNECTION
    # =================================================

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    user = None


    # =================================================
    # STUDENT VERIFICATION
    # =================================================

    if role == "student":

        cursor.execute("""
            SELECT
                id,
                student_name,
                email
            FROM students
            WHERE roll_number = %s
            AND email = %s
        """, (
            username,
            email
        ))

        user = cursor.fetchone()


    # =================================================
    # DRIVER VERIFICATION
    # =================================================

    elif role == "driver":

        cursor.execute("""
            SELECT
                id,
                driver_name,
                email
            FROM drivers
            WHERE license_number = %s
            AND email = %s
        """, (
            username,
            email
        ))

        user = cursor.fetchone()


    # =================================================
    # INVALID ROLE
    # =================================================

    else:

        cursor.close()
        conn.close()

        flash(
            "Invalid account type.",
            "danger"
        )

        return redirect(
            url_for("forgot_password")
        )


    # =================================================
    # CLOSE DATABASE
    # =================================================

    cursor.close()

    conn.close()


    # =================================================
    # USER NOT FOUND
    # =================================================

    if not user:

        flash(
            "The entered account details do not match our records.",
            "danger"
        )

        return redirect(
            url_for("forgot_password")
        )


    # =================================================
    # GENERATE 6-DIGIT OTP
    # =================================================

    otp = str(
        random.randint(100000, 999999)
    )


    # =================================================
    # STORE INFORMATION IN SESSION
    # =================================================

    session["reset_user_id"] = user["id"]

    session["reset_role"] = role

    session["reset_email"] = email

    session["reset_otp"] = otp

    session["reset_otp_expiry"] = (
        datetime.now() +
        timedelta(minutes=5)
    ).timestamp()


    # =================================================
    # GET USER NAME
    # =================================================

    if role == "student":

        name = user["student_name"]

    else:

        name = user["driver_name"]


    # =================================================
    # SEND OTP TO EMAIL
    # =================================================

    try:

        send_reset_otp_email(
            email,
            otp,
            name
        )


    except Exception as e:

        # Clear session if email fails

        session.pop("reset_user_id", None)

        session.pop("reset_role", None)

        session.pop("reset_email", None)

        session.pop("reset_otp", None)

        session.pop("reset_otp_expiry", None)


        flash(
            "Unable to send OTP to your email. Please try again.",
            "danger"
        )

        return redirect(
            url_for("forgot_password")
        )


    # =================================================
    # SUCCESS
    # =================================================

    flash(
        "OTP has been sent to your registered email address.",
        "success"
    )


    # =================================================
    # GO TO OTP PAGE
    # =================================================

    return redirect(
        url_for("verify_reset_otp")
    )
# =====================================================
# SEND PASSWORD RESET OTP THROUGH EMAIL
# =====================================================

def send_reset_otp_email(receiver_email, otp, user_name):

    try:

        # ---------------------------------------------
        # CREATE EMAIL MESSAGE
        # ---------------------------------------------

        message = EmailMessage()

        message["Subject"] = (
            "Password Reset OTP - College Bus Tracking System"
        )

        message["From"] = EMAIL_ADDRESS

        message["To"] = receiver_email


        # ---------------------------------------------
        # EMAIL CONTENT
        # ---------------------------------------------

        message.set_content(
            f"""
Hello {user_name},

You requested to reset your password for the College Bus Tracking System.

Your Password Reset OTP is:

{otp}

This OTP is valid for 5 minutes.

Do not share this OTP with anyone.

Thank you,
College Bus Tracking System
"""
        )


        # ---------------------------------------------
        # CONNECT TO GMAIL SMTP
        # ---------------------------------------------

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as smtp:

            # Login to Gmail
            smtp.login(
                EMAIL_ADDRESS,
                EMAIL_APP_PASSWORD
            )

            # Send Email
            smtp.send_message(message)


        # ---------------------------------------------
        # SUCCESS MESSAGE
        # ---------------------------------------------

        print(
            "PASSWORD RESET OTP EMAIL SENT TO:",
            receiver_email
        )


        return True


    except Exception as e:

        print(
            "EMAIL OTP ERROR:",
            e
        )

        raise e
# =====================================================
# VERIFY RESET OTP
# =====================================================

@app.route("/verify_reset_otp", methods=["GET", "POST"])
def verify_reset_otp():

    # ---------------------------------------------
    # CHECK RESET SESSION
    # ---------------------------------------------

    if "reset_user_id" not in session:

        flash(
            "Password reset session expired.",
            "danger"
        )

        return redirect(
            url_for("forgot_password")
        )


    # ---------------------------------------------
    # SHOW OTP PAGE
    # ---------------------------------------------

    if request.method == "GET":

        return render_template(
            "verify_reset_otp.html"
        )


    # ---------------------------------------------
    # GET ENTERED OTP
    # ---------------------------------------------

    entered_otp = request.form.get(
        "otp",
        ""
    ).strip()


    stored_otp = session.get(
        "reset_otp"
    )


    expiry = session.get(
        "reset_otp_expiry"
    )


    # ---------------------------------------------
    # OTP EXPIRY CHECK
    # ---------------------------------------------

    if (
        not expiry
        or
        datetime.now().timestamp() > expiry
    ):

        session.pop(
            "reset_otp",
            None
        )

        session.pop(
            "reset_otp_expiry",
            None
        )

        flash(
            "OTP has expired. Please request a new OTP.",
            "danger"
        )

        return redirect(
            url_for("forgot_password")
        )


    # ---------------------------------------------
    # OTP FORMAT CHECK
    # ---------------------------------------------

    if (
        not entered_otp.isdigit()
        or
        len(entered_otp) != 6
    ):

        flash(
            "Please enter a valid 6-digit OTP.",
            "danger"
        )

        return redirect(
            url_for("verify_reset_otp")
        )


    # ---------------------------------------------
    # OTP MATCH
    # ---------------------------------------------

    if entered_otp != stored_otp:

        flash(
            "Invalid OTP. Please check and try again.",
            "danger"
        )

        return redirect(
            url_for("verify_reset_otp")
        )


    # ---------------------------------------------
    # OTP VERIFIED
    # ---------------------------------------------

    session["reset_verified"] = True


    # ---------------------------------------------
    # REMOVE OTP
    # ---------------------------------------------

    session.pop(
        "reset_otp",
        None
    )

    session.pop(
        "reset_otp_expiry",
        None
    )


    # ---------------------------------------------
    # GO TO NEW PASSWORD
    # ---------------------------------------------

    return redirect(
        url_for("reset_password")
    )

# =====================================================
# RESET PASSWORD
# =====================================================

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    if "reset_user_id" not in session:
        return redirect(url_for("forgot_password"))

    if not session.get("reset_verified"):

        flash(
            "Please verify the OTP first.",
            "danger"
        )

        return redirect(url_for("verify_reset_otp"))

    if request.method == "GET":

        return render_template("reset_password.html")

    new_password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # =================================================
    # VALIDATION
    # =================================================

    if not new_password or not confirm_password:

        flash(
            "Please enter both password fields.",
            "danger"
        )

        return redirect(url_for("reset_password"))

    if new_password != confirm_password:

        flash(
            "Passwords do not match.",
            "danger"
        )

        return redirect(url_for("reset_password"))

    if len(new_password) < 8:

        flash(
            "Password must contain at least 8 characters.",
            "danger"
        )

        return redirect(url_for("reset_password"))

    user_id = session["reset_user_id"]
    role = session["reset_role"]

    # =================================================
    # HASH NEW PASSWORD
    # =================================================

    hashed_password = ph.hash(new_password)

    conn = get_db_connection()
    cursor = conn.cursor()

    # =================================================
    # UPDATE STUDENT PASSWORD
    # =================================================

    if role == "student":

        cursor.execute("""
            UPDATE students
            SET password=%s
            WHERE id=%s
        """, (
            hashed_password,
            user_id
        ))

    # =================================================
    # UPDATE DRIVER PASSWORD
    # =================================================

    elif role == "driver":

        cursor.execute("""
            UPDATE drivers
            SET password=%s
            WHERE id=%s
        """, (
            hashed_password,
            user_id
        ))

    else:

        cursor.close()
        conn.close()

        flash(
            "Invalid account type.",
            "danger"
        )

        return redirect(url_for("login"))

    conn.commit()

    cursor.close()
    conn.close()

    # =================================================
    # CLEAR RESET SESSION
    # =================================================

    session.pop("reset_user_id", None)
    session.pop("reset_role", None)
    session.pop("reset_phone", None)
    session.pop("reset_verified", None)

    flash(
        "Password reset successfully. You can now login.",
        "success"
    )

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

    # ------------------------------------------
    # Student Login Check
    # ------------------------------------------

    if "student_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ------------------------------------------
    # Student Details
    # ------------------------------------------

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

    # ------------------------------------------
    # Student Not Found
    # ------------------------------------------

    if not student:

        cursor.close()
        conn.close()

        session.clear()

        return redirect("/login")

    # ------------------------------------------
    # Today's Live Bus Status
    # ------------------------------------------

    cursor.execute("""
        SELECT

            s.student_name,
            s.roll_number,

            b.bus_id,
            b.bus_number,
            b.driver_name,
            
            b.capacity,
            b.occupied_seats,
            b.available_seats,

            r.route_id,
            r.route_name,

            lbl.current_stop,
            lbl.speed,
            lbl.trip_status,
            lbl.latitude,
            lbl.longitude,
            lbl.eta,
            lbl.updated_at,

            TIME_FORMAT(
                lbl.eta,
                '%h:%i %p'
            ) AS eta_time,

            TIME_FORMAT(
                lbl.updated_at,
                '%h:%i %p'
            ) AS last_updated,

            CASE

                WHEN lbl.bus_id IS NULL
                    THEN 'Offline'

                WHEN lbl.trip_status IS NOT NULL
                     AND lbl.trip_status <> ''
                    THEN lbl.trip_status

                WHEN lbl.speed > 0
                    THEN 'Moving'

                ELSE
                    'Stopped'

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

    # ------------------------------------------
    # Close Database
    # ------------------------------------------

    cursor.close()
    conn.close()

    # ------------------------------------------
    # Render Dashboard
    # ------------------------------------------

    return render_template(
        "student/student_dashboard.html",
        student=student,
        bus_status=bus_status,
        active_page="dashboard"
    )
    
# ==========================================
# STUDENT SCAN BUS QR CODE
# ==========================================

@app.route("/student/scan_bus_qr/<trip_token>")
def student_scan_bus_qr(trip_token):

    # --------------------------------------
    # Student Login Check
    # --------------------------------------

    if "student_id" not in session:

        flash(
            "Please login as a student before boarding.",
            "warning"
        )

        return redirect(url_for("login"))


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # --------------------------------------
        # Get Student
        # --------------------------------------

        cursor.execute("""
            SELECT *
            FROM students
            WHERE id = %s
        """, (session["student_id"],))

        student = cursor.fetchone()


        if not student:

            flash(
                "Student account not found.",
                "danger"
            )

            return redirect(url_for("login"))


        # --------------------------------------
        # Get Active Trip
        # --------------------------------------

        cursor.execute("""
            SELECT *
            FROM bus_trips
            WHERE trip_token = %s
            AND status = 'ACTIVE'
        """, (trip_token,))

        trip = cursor.fetchone()


        if not trip:

            flash(
                "This QR Code is invalid or the trip has ended.",
                "danger"
            )

            return redirect(url_for("student_dashboard"))


        # --------------------------------------
        # Check Student Bus Assignment
        # --------------------------------------

        cursor.execute("""
            SELECT *
            FROM student_bus_assignment
            WHERE student_id = %s
            AND bus_id = %s
        """, (

            student["id"],
            trip["bus_id"]

        ))

        assignment = cursor.fetchone()


        if not assignment:

            flash(
                "You are not assigned to this bus.",
                "danger"
            )

            return redirect(url_for("student_dashboard"))


        # --------------------------------------
        # Check Already Boarded
        # --------------------------------------

        cursor.execute("""
            SELECT *
            FROM student_boarding
            WHERE trip_id = %s
            AND student_id = %s
        """, (

            trip["trip_id"],
            student["id"]

        ))

        already_boarded = cursor.fetchone()


        if already_boarded:

            flash(
                "You have already boarded this bus.",
                "warning"
            )

            return redirect(url_for("student_dashboard"))


        # --------------------------------------
        # Get Bus Details
        # --------------------------------------

        cursor.execute("""
            SELECT *
            FROM buses
            WHERE bus_id = %s
        """, (trip["bus_id"],))

        bus = cursor.fetchone()


        # --------------------------------------
        # Check Seat Availability
        # --------------------------------------

        if bus["available_seats"] <= 0:

            flash(
                "Sorry! No seats are available.",
                "danger"
            )

            return redirect(url_for("student_dashboard"))


        # --------------------------------------
        # Record Student Boarding
        # --------------------------------------

        cursor.execute("""
            INSERT INTO student_boarding (

                trip_id,
                student_id,
                bus_id,
                status

            )

            VALUES (

                %s,
                %s,
                %s,
                'BOARDED'

            )
        """, (

            trip["trip_id"],
            student["id"],
            trip["bus_id"]

        ))


        # --------------------------------------
        # Update Bus Seats
        # --------------------------------------

        cursor.execute("""
            UPDATE buses

            SET

                occupied_seats = occupied_seats + 1,

                available_seats = available_seats - 1

            WHERE

                bus_id = %s

                AND available_seats > 0
        """, (trip["bus_id"],))


        conn.commit()


        flash(
            "Boarding successful! Your seat has been registered.",
            "success"
        )


        return redirect(
            url_for("student_dashboard")
        )


    except Exception as e:

        conn.rollback()

        print("STUDENT BOARDING ERROR:", e)


        flash(
            "Something went wrong while boarding.",
            "danger"
        )


        return redirect(
            url_for("student_dashboard")
        )


    finally:

        cursor.close()
        conn.close()
        
# ==========================================
# STUDENT VERIFY BUS QR CODE
# ==========================================

@app.route("/student/verify_bus_qr", methods=["POST"])
def student_verify_bus_qr():

    # --------------------------------------
    # Student Login Check
    # --------------------------------------

    if "student_id" not in session:

        return jsonify({

            "success": False,

            "message": "Please login as a student first."

        }), 401


    # --------------------------------------
    # Get QR Data
    # --------------------------------------

    data = request.get_json()

    qr_data = data.get("qr_data", "").strip()


    if not qr_data:

        return jsonify({

            "success": False,

            "message": "Invalid QR Code."

        })


    # --------------------------------------
    # Extract Trip Token
    # --------------------------------------

    trip_token = qr_data


    # If QR contains a full URL
    # Example:
    # http://192.168.1.10:5000/student/scan_bus_qr/TOKEN

    if "/student/scan_bus_qr/" in qr_data:

        trip_token = qr_data.split(
            "/student/scan_bus_qr/"
        )[-1].strip("/")


    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)


    try:

        # --------------------------------------
        # Get Student
        # --------------------------------------

        cursor.execute("""

            SELECT *

            FROM students

            WHERE id = %s

        """, (

            session["student_id"],

        ))

        student = cursor.fetchone()


        if not student:

            return jsonify({

                "success": False,

                "message": "Student account not found."

            })


        # --------------------------------------
        # Get Active Trip
        # --------------------------------------

        cursor.execute("""

            SELECT *

            FROM bus_trips

            WHERE trip_token = %s

            AND status = 'ACTIVE'

        """, (

            trip_token,

        ))

        trip = cursor.fetchone()


        if not trip:

            return jsonify({

                "success": False,

                "message": "This QR Code is invalid or the trip has ended."

            })


        # --------------------------------------
        # Check Student Bus Assignment
        # --------------------------------------

        cursor.execute("""

            SELECT *

            FROM student_bus_assignment

            WHERE student_id = %s

            AND bus_id = %s

        """, (

            student["id"],

            trip["bus_id"]

        ))

        assignment = cursor.fetchone()


        if not assignment:

            return jsonify({

                "success": False,

                "message": "You are not assigned to this bus."

            })


        # --------------------------------------
        # Check Already Boarded
        # --------------------------------------

        cursor.execute("""

            SELECT *

            FROM student_boarding

            WHERE trip_id = %s

            AND student_id = %s

        """, (

            trip["trip_id"],

            student["id"]

        ))

        already_boarded = cursor.fetchone()


        if already_boarded:

            return jsonify({

                "success": False,

                "message": "You have already boarded this bus."

            })


        # --------------------------------------
        # Check Available Seats
        # --------------------------------------

        cursor.execute("""

            SELECT *

            FROM buses

            WHERE bus_id = %s

        """, (

            trip["bus_id"],

        ))

        bus = cursor.fetchone()


        if not bus:

            return jsonify({

                "success": False,

                "message": "Bus not found."

            })


        if bus["available_seats"] <= 0:

            return jsonify({

                "success": False,

                "message": "Sorry! No seats are available."

            })


        # --------------------------------------
        # Record Student Boarding
        # --------------------------------------

        cursor.execute("""

            INSERT INTO student_boarding (

                trip_id,

                student_id,

                bus_id,

                status

            )

            VALUES (

                %s,

                %s,

                %s,

                'BOARDED'

            )

        """, (

            trip["trip_id"],

            student["id"],

            trip["bus_id"]

        ))


        # --------------------------------------
        # Update Seat Availability
        # --------------------------------------

        cursor.execute("""

            UPDATE buses

            SET

                occupied_seats = occupied_seats + 1,

                available_seats = available_seats - 1

            WHERE

                bus_id = %s

            AND available_seats > 0

        """, (

            trip["bus_id"],

        ))


        conn.commit()


        return jsonify({

            "success": True,

            "message": "Boarding successful! Your seat has been registered."

        })


    except Exception as e:

        conn.rollback()

        print("QR BOARDING ERROR:", e)


        return jsonify({

            "success": False,

            "message": "Something went wrong while registering boarding."

        })


    finally:

        cursor.close()

        conn.close()
# ==========================================
# STUDENT QR SCANNER PAGE
# ==========================================

@app.route("/student/scan_qr")
def student_scan_qr():

    # Check student login
    if "student_id" not in session:

        flash(
            "Please login as a student first.",
            "warning"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "student/scan_qr.html"
    )
# ==========================================
# VERIFY BUS QR & STUDENT BOARDING
# ==========================================

@app.route(
    "/student/verify_bus_qr",
    methods=["POST"]
)
def verify_bus_qr():

    # --------------------------------------
    # Student Login Check
    # --------------------------------------

    if "student_id" not in session:

        return jsonify({

            "success": False,

            "message": "Please login as a student."

        }), 401


    # --------------------------------------
    # Get QR Data
    # --------------------------------------

    data = request.get_json()

    if not data:

        return jsonify({

            "success": False,

            "message": "Invalid QR data."

        })


    qr_data = data.get("qr_data")


    if not qr_data:

        return jsonify({

            "success": False,

            "message": "QR code is empty."

        })


    # --------------------------------------
    # Get Trip Token
    # --------------------------------------
    # Expected QR URL format:
    #
    # http://YOUR-IP:5000/student/scan_bus_qr/TRIP_TOKEN
    #

    try:

        trip_token = qr_data.rstrip("/").split("/")[-1]

    except Exception:

        return jsonify({

            "success": False,

            "message": "Invalid QR Code."

        })


    conn = get_db_connection()

    cursor = conn.cursor(
        dictionary=True
    )


    try:

        # ==================================
        # GET STUDENT
        # ==================================

        cursor.execute("""

            SELECT *

            FROM students

            WHERE id = %s

        """, (

            session["student_id"],

        ))

        student = cursor.fetchone()


        if not student:

            return jsonify({

                "success": False,

                "message": "Student account not found."

            })


        # ==================================
        # GET ACTIVE TRIP
        # ==================================

        cursor.execute("""

            SELECT *

            FROM bus_trips

            WHERE trip_token = %s

            AND status = 'ACTIVE'

        """, (

            trip_token,

        ))

        trip = cursor.fetchone()


        if not trip:

            return jsonify({

                "success": False,

                "message": "This QR Code is invalid or the trip has ended."

            })


        # ==================================
        # CHECK STUDENT BUS ASSIGNMENT
        # ==================================

        cursor.execute("""

            SELECT *

            FROM student_bus_assignment

            WHERE student_id = %s

            AND bus_id = %s

        """, (

            student["id"],

            trip["bus_id"]

        ))

        assignment = cursor.fetchone()


        if not assignment:

            return jsonify({

                "success": False,

                "message": "You are not assigned to this bus."

            })


        # ==================================
        # CHECK ALREADY BOARDED
        # ==================================

        cursor.execute("""

            SELECT *

            FROM student_boarding

            WHERE trip_id = %s

            AND student_id = %s

        """, (

            trip["trip_id"],

            student["id"]

        ))

        already_boarded = cursor.fetchone()


        if already_boarded:

            return jsonify({

                "success": False,

                "message": "You have already boarded this bus."

            })


        # ==================================
        # CHECK AVAILABLE SEATS
        # ==================================

        cursor.execute("""

            SELECT *

            FROM buses

            WHERE bus_id = %s

        """, (

            trip["bus_id"],

        ))

        bus = cursor.fetchone()


        if not bus:

            return jsonify({

                "success": False,

                "message": "Bus not found."

            })


        if bus["available_seats"] <= 0:

            return jsonify({

                "success": False,

                "message": "Sorry! No seats are available."

            })


        # ==================================
        # RECORD STUDENT BOARDING
        # ==================================

        cursor.execute("""

            INSERT INTO student_boarding (

                trip_id,

                student_id,

                bus_id,

                status

            )

            VALUES (

                %s,

                %s,

                %s,

                'BOARDED'

            )

        """, (

            trip["trip_id"],

            student["id"],

            trip["bus_id"]

        ))


        # ==================================
        # UPDATE BUS SEATS
        # ==================================

        cursor.execute("""

            UPDATE buses

            SET

                occupied_seats = occupied_seats + 1,

                available_seats = available_seats - 1

            WHERE

                bus_id = %s

                AND available_seats > 0

        """, (

            trip["bus_id"],

        ))


        # ==================================
        # COMMIT DATABASE
        # ==================================

        conn.commit()


        return jsonify({

            "success": True,

            "message": "Boarding successful! Seat availability updated."

        })


    except Exception as e:

        conn.rollback()

        print(
            "QR BOARDING ERROR:",
            e
        )


        return jsonify({

            "success": False,

            "message": "Something went wrong while boarding."

        })


    finally:

        cursor.close()

        conn.close()
# ==========================================
# STUDENT PROFILE (Student Portal)
# ==========================================

@app.route("/student/student_profile")
def student_profile():

    if "student_id" not in session:
        return redirect("/login")

    conn = mysql.connector.connect(
        host= os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
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
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
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
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
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

    # ==========================================
    # GET STUDENT + BUS + LIVE LOCATION
    # ==========================================

    cursor.execute("""
        SELECT

            s.student_name,

            b.bus_id,
            b.bus_number,
            b.driver_name,

            r.route_id,
            r.route_name,

            lbl.latitude,
            lbl.longitude,
            lbl.current_stop,
            lbl.speed,
            lbl.trip_status,

            TIME_FORMAT(
                lbl.updated_at,
                '%h:%i %p'
            ) AS last_updated,

            TIME_FORMAT(
                lbl.eta,
                '%h:%i %p'
            ) AS eta,

            CASE
                WHEN lbl.speed > 0
                THEN 'Moving'
                ELSE 'Stopped'
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

    tracking = cursor.fetchone()

    # ==========================================
    # GET ROUTE STOPS
    # ==========================================

    stops = []

    if tracking and tracking.get("route_id"):

        cursor.execute("""
            SELECT

                id,
                route_id,
                stop_name,
                stop_order,
                latitude,
                longitude

            FROM bus_stops

            WHERE route_id = %s

            ORDER BY stop_order ASC

        """, (tracking["route_id"],))

        stops = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "student/live_tracking.html",
        tracking=tracking,
        route_stops=stops,
        active_page="live_tracking"
    )
# ==========================================
# STUDENT LIVE ROUTE DATA
# ==========================================

@app.route("/student/live_route/<int:bus_id>")
def student_live_route(bus_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ==========================================
    # LIVE BUS LOCATION
    # ==========================================

    cursor.execute("""
        SELECT

            latitude,
            longitude,
            current_stop,
            speed,
            trip_status,

            TIME_FORMAT(
                updated_at,
                '%h:%i %p'
            ) AS last_updated,

            eta

        FROM live_bus_location

        WHERE bus_id = %s

        LIMIT 1

    """, (bus_id,))

    live = cursor.fetchone()

    if not live:

        cursor.close()
        conn.close()

        return jsonify({
            "success": False,
            "message": "Live bus location not available."
        })

    # ==========================================
    # GET BUS ROUTE
    # ==========================================

    cursor.execute("""
        SELECT route_id
        FROM buses
        WHERE bus_id = %s
        LIMIT 1
    """, (bus_id,))

    bus = cursor.fetchone()

    if not bus:

        cursor.close()
        conn.close()

        return jsonify({
            "success": False,
            "message": "Bus not found."
        })

    route_id = bus["route_id"]

    # ==========================================
    # GET ROUTE STOPS
    # ==========================================

    cursor.execute("""
        SELECT

            id,
            stop_name,
            stop_order,
            latitude,
            longitude

        FROM bus_stops

        WHERE route_id = %s

        ORDER BY stop_order ASC

    """, (route_id,))

    stops = cursor.fetchall()

    cursor.close()
    conn.close()

    # ==========================================
    # HAVERSINE FUNCTION
    # ==========================================

    from math import radians, sin, cos, sqrt, atan2

    def distance_km(lat1, lon1, lat2, lon2):

        R = 6371.0

        lat1 = radians(float(lat1))
        lon1 = radians(float(lon1))

        lat2 = radians(float(lat2))
        lon2 = radians(float(lon2))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            sin(dlat / 2) ** 2
            +
            cos(lat1)
            * cos(lat2)
            * sin(dlon / 2) ** 2
        )

        c = 2 * atan2(
            sqrt(a),
            sqrt(1 - a)
        )

        return R * c

    # ==========================================
    # CURRENT GPS
    # ==========================================

    current_lat = live["latitude"]
    current_lng = live["longitude"]

    current_stop = live["current_stop"]

    current_speed = float(
        live["speed"] or 0
    )

    # ==========================================
    # FIND CURRENT STOP INDEX
    # ==========================================

    current_index = -1

    for index, stop in enumerate(stops):

        if (
            current_stop
            and
            stop["stop_name"].strip().lower()
            ==
            current_stop.strip().lower()
        ):

            current_index = index
            break

    # ==========================================
    # FIND NEXT STOP
    # ==========================================

    next_stop = None

    if current_index >= 0:

        if current_index + 1 < len(stops):

            next_stop = stops[
                current_index + 1
            ]

    else:

        # If current stop is not matched,
        # find the nearest upcoming stop.

        nearest_distance = None

        for stop in stops:

            if (
                current_lat is None
                or current_lng is None
                or stop["latitude"] is None
                or stop["longitude"] is None
            ):
                continue

            d = distance_km(
                current_lat,
                current_lng,
                stop["latitude"],
                stop["longitude"]
            )

            if (
                nearest_distance is None
                or d < nearest_distance
            ):

                nearest_distance = d
                next_stop = stop

    # ==========================================
    # DISTANCE TO NEXT STOP
    # ==========================================

    distance_to_next = 0

    if (
        next_stop
        and current_lat is not None
        and current_lng is not None
    ):

        distance_to_next = distance_km(
            current_lat,
            current_lng,
            next_stop["latitude"],
            next_stop["longitude"]
        )

    # ==========================================
    # DISTANCE REMAINING
    # ==========================================

    distance_remaining = 0

    if next_stop:

        # Current position → next stop
        distance_remaining += distance_to_next

        # Next stop → remaining stops
        next_index = stops.index(next_stop)

        for i in range(
            next_index,
            len(stops) - 1
        ):

            stop_a = stops[i]
            stop_b = stops[i + 1]

            distance_remaining += distance_km(
                stop_a["latitude"],
                stop_a["longitude"],
                stop_b["latitude"],
                stop_b["longitude"]
            )

    # ==========================================
    # ETA CALCULATION
    # ==========================================

    # If bus is moving, use live GPS speed.
    #
    # If bus is stopped, use a reasonable
    # fallback average speed.

    average_speed = (
        current_speed
        if current_speed > 3
        else 25
    )

    eta_minutes = (
        distance_to_next
        / average_speed
        * 60
    )

    # ==========================================
    # CREATE ETA TIME
    # ==========================================

    from datetime import datetime, timedelta

    eta_time = (
        datetime.now()
        +
        timedelta(
            minutes=eta_minutes
        )
    )

    eta_formatted = eta_time.strftime(
        "%I:%M %p"
    )

    # ==========================================
    # STOPS REMAINING
    # ==========================================

    stops_remaining = 0

    if next_stop:

        next_index = stops.index(next_stop)

        stops_remaining = (
            len(stops)
            -
            next_index
        )

    # ==========================================
    # RETURN DATA
    # ==========================================

    return jsonify({

        "success": True,

        "latitude": current_lat,

        "longitude": current_lng,

        "current_stop": current_stop,

        "next_stop": (
            next_stop["stop_name"]
            if next_stop
            else "Route Completed"
        ),

        "next_stop_lat": (
            float(next_stop["latitude"])
            if next_stop
            else None
        ),

        "next_stop_lng": (
            float(next_stop["longitude"])
            if next_stop
            else None
        ),

        "distance_to_next": round(
            distance_to_next,
            2
        ),

        "distance_remaining": round(
            distance_remaining,
            2
        ),

        "stops_remaining":
            stops_remaining,

        "speed":
            current_speed,

        "eta":
            eta_formatted,

        "trip_status":
            live["trip_status"],

        "last_updated":
            live["last_updated"],

        "stops": [

            {
                "id": stop["id"],

                "stop_name":
                    stop["stop_name"],

                "stop_order":
                    stop["stop_order"],

                "latitude":
                    float(stop["latitude"]),

                "longitude":
                    float(stop["longitude"])

            }

            for stop in stops
        ]

    })
# ==========================================
# GET LIVE BUS LOCATION
# ==========================================

@app.route("/student/live_location/<int:bus_id>")
def get_student_live_location(bus_id):

    # ------------------------------------------
    # Student Login Check
    # ------------------------------------------

    if "student_id" not in session:

        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ==========================================
    # GET LIVE LOCATION
    # ==========================================

    cursor.execute("""
        SELECT

            latitude,
            longitude,
            current_stop,
            speed,
            trip_status,

            TIME_FORMAT(
                updated_at,
                '%h:%i %p'
            ) AS last_updated,

            TIME_FORMAT(
                eta,
                '%h:%i %p'
            ) AS eta

        FROM live_bus_location

        WHERE bus_id = %s

        ORDER BY updated_at DESC

        LIMIT 1

    """, (bus_id,))

    location = cursor.fetchone()

    cursor.close()
    conn.close()

    # ==========================================
    # LOCATION FOUND
    # ==========================================

    if location:

        return jsonify({

            "success": True,

            "latitude": float(location["latitude"])
                if location["latitude"] is not None
                else None,

            "longitude": float(location["longitude"])
                if location["longitude"] is not None
                else None,

            "current_stop":
                location["current_stop"],

            "speed":
                float(location["speed"])
                if location["speed"] is not None
                else 0,

            "trip_status":
                location["trip_status"],

            "last_updated":
                location["last_updated"],

            "eta":
                location["eta"]

        })

    # ==========================================
    # NO LOCATION
    # ==========================================

    return jsonify({

        "success": False,

        "message":
            "Live bus location is not available."

    })
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
    # Bus + LIVE INFORMATION
    # --------------------------------

    cursor.execute("""

        SELECT

            b.bus_id,
            b.bus_number,
            b.capacity,
            b.driver_name,

            r.route_id,
            r.route_name,
            r.source,
            r.destination,
            r.distance,
            r.estimated_time,

            /* ==========================
               LIVE BUS DATA
            ========================== */

            lbl.current_stop,

            lbl.speed,

            lbl.trip_status,

            lbl.latitude,

            lbl.longitude,

            lbl.eta,

            lbl.updated_at,

            TIME_FORMAT(
                lbl.eta,
                '%h:%i %p'
            ) AS eta_time,

            TIME_FORMAT(
                lbl.updated_at,
                '%h:%i %p'
            ) AS last_updated,

            /* ==========================
               REAL STATUS
            ========================== */

            CASE

                WHEN lbl.bus_id IS NULL
                    THEN 'Offline'

                WHEN lbl.trip_status IS NOT NULL
                     AND TRIM(lbl.trip_status) <> ''
                    THEN lbl.trip_status

                WHEN lbl.speed > 0
                    THEN 'Moving'

                ELSE
                    'Stopped'

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

    # --------------------------------
    # Close Database
    # --------------------------------

    cursor.close()
    conn.close()

    # --------------------------------
    # No Bus Assigned
    # --------------------------------

    if not bus:

        flash(
            "No bus assigned yet.",
            "warning"
        )

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

            n.id,
            n.title,
            n.message,
            n.notification_type,
            n.created_at,
            sn.is_read

        FROM student_notifications sn
        
        INNER JOIN notifications n
            ON sn.notification_id = n.id
            
        WHERE sn.student_id = %s
        
          AND n.status = 'Active'
          
        ORDER BY created_at DESC

    """, (session["student_id"],))

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
# =====================================================
# STUDENT - GET UNREAD NOTIFICATION COUNT
# =====================================================

@app.route("/student/notifications/unread-count")
def student_unread_notification_count():

    # Check student login
    if "student_id" not in session:
        return jsonify({
            "count": 0
        })


    conn = get_db_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM student_notifications
            WHERE student_id = %s
            AND is_read = 0
            """,
            (
                session["student_id"],
            )
        )


        result = cursor.fetchone()

        unread_count = result[0] if result else 0


        return jsonify({
            "count": unread_count
        })


    except Exception as e:

        print(
            "Unread Notification Count Error:",
            str(e)
        )

        return jsonify({
            "count": 0
        })


    finally:

        cursor.close()
        conn.close()
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
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ------------------------------------------
    # Get Student + Assigned Bus + Driver + Route
    # ------------------------------------------

    cursor.execute("""
        SELECT

            s.id,
            s.student_name,
            s.roll_number,
            s.profile_image,

            b.bus_id,
            b.bus_number,
            b.driver_name,
            b.capacity,

            r.route_id,
            r.route_name,
            r.source,
            r.destination,

            d.phone AS driver_phone,

            lbl.current_stop,
            lbl.speed,
            lbl.trip_status

        FROM students s

        LEFT JOIN student_bus_assignment sba
            ON s.id = sba.student_id

        LEFT JOIN buses b
            ON sba.bus_id = b.bus_id

        LEFT JOIN routes r
            ON b.route_id = r.route_id

        LEFT JOIN drivers d
            ON d.bus_number = b.bus_number

        LEFT JOIN live_bus_location lbl
            ON b.bus_id = lbl.bus_id

        WHERE s.id = %s

        LIMIT 1

    """, (session["student_id"],))

    emergency = cursor.fetchone()

    cursor.close()
    conn.close()

    # ------------------------------------------
    # Student Not Found
    # ------------------------------------------

    if not emergency:

        flash("Student information not found.", "danger")

        return redirect(url_for("student_dashboard"))

    # ------------------------------------------
    # Render Emergency Page
    # ------------------------------------------

    return render_template(
        "student/emergency.html",
        emergency=emergency,
        active_page="emergency"
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
# PARENT DASHBOARD
# ==========================================

@app.route("/parent_dashboard")
def parent_dashboard():

    # ------------------------------------------
    # Parent Login Check
    # ------------------------------------------

    if "parent_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ==========================================
    # GET PARENT + STUDENT DETAILS
    # ==========================================

    cursor.execute("""
        SELECT

            p.parent_id,
            p.parent_name,
            p.parent_phone,

            s.id AS student_id,
            s.student_name,
            s.roll_number,
            s.phone,
            s.profile_image

        FROM parents p

        INNER JOIN students s
            ON p.student_id = s.id

        WHERE p.parent_id = %s

        LIMIT 1

    """, (session["parent_id"],))

    parent_data = cursor.fetchone()

    # ==========================================
    # GET BUS + LIVE STATUS
    # ==========================================

    bus_status = None

    if parent_data:

        cursor.execute("""
            SELECT

                b.bus_id,
                b.bus_number,
                b.driver_name,

                r.route_id,
                r.route_name,

                lbl.current_stop,
                lbl.speed,
                lbl.trip_status,
                lbl.latitude,
                lbl.longitude,

                TIME_FORMAT(
                    lbl.eta,
                    '%h:%i %p'
                ) AS eta,

                TIME_FORMAT(
                    lbl.updated_at,
                    '%h:%i %p'
                ) AS last_updated,

                CASE

                    WHEN lbl.bus_id IS NULL
                        THEN 'Offline'

                    WHEN lbl.trip_status IS NOT NULL
                        AND lbl.trip_status <> ''
                        THEN lbl.trip_status

                    WHEN lbl.speed > 0
                        THEN 'Moving'

                    ELSE 'Stopped'

                END AS status

            FROM student_bus_assignment sba

            LEFT JOIN buses b
                ON sba.bus_id = b.bus_id

            LEFT JOIN routes r
                ON b.route_id = r.route_id

            LEFT JOIN live_bus_location lbl
                ON b.bus_id = lbl.bus_id

            WHERE sba.student_id = %s

            LIMIT 1

        """, (parent_data["student_id"],))

        bus_status = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "parent/parent_dashboard.html",
        parent_data=parent_data,
        bus_status=bus_status,
        active_page="dashboard"
    )
# ==========================================
# PARENT LIVE TRACKING
# ==========================================

@app.route("/parent/live_tracking")
def parent_live_tracking():

    if "parent_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ==========================================
    # GET PARENT'S STUDENT
    # ==========================================

    cursor.execute("""
        SELECT

            p.parent_name,

            s.id AS student_id,
            s.student_name,
            s.roll_number

        FROM parents p

        INNER JOIN students s
            ON p.student_id = s.id

        WHERE p.parent_id = %s

        LIMIT 1

    """, (session["parent_id"],))

    parent_student = cursor.fetchone()

    tracking = None
    stops = []

    # ==========================================
    # GET BUS + LIVE LOCATION
    # ==========================================

    if parent_student:

        cursor.execute("""
            SELECT

                s.student_name,
                s.roll_number,

                b.bus_id,
                b.bus_number,
                b.driver_name,

                r.route_id,
                r.route_name,

                lbl.latitude,
                lbl.longitude,
                lbl.current_stop,
                lbl.speed,
                lbl.trip_status,

                TIME_FORMAT(
                    lbl.updated_at,
                    '%h:%i %p'
                ) AS last_updated,

                TIME_FORMAT(
                    lbl.eta,
                    '%h:%i %p'
                ) AS eta,

                CASE

                    WHEN lbl.bus_id IS NULL
                        THEN 'Offline'

                    WHEN lbl.trip_status IS NOT NULL
                        AND lbl.trip_status <> ''
                        THEN lbl.trip_status

                    WHEN lbl.speed > 0
                        THEN 'Moving'

                    ELSE 'Stopped'

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

        """, (parent_student["student_id"],))

        tracking = cursor.fetchone()

        # ======================================
        # GET ROUTE STOPS
        # ======================================

        if tracking and tracking.get("route_id"):

            cursor.execute("""
                SELECT

                    id,
                    route_id,
                    stop_name,
                    stop_order,
                    latitude,
                    longitude

                FROM bus_stops

                WHERE route_id = %s

                ORDER BY stop_order ASC

            """, (tracking["route_id"],))

            stops = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "parent/live_tracking.html",
        parent_student=parent_student,
        tracking=tracking,
        route_stops=stops,
        active_page="live_tracking"
    )
# ==========================================
# PARENT LIVE LOCATION API
# ==========================================

@app.route("/parent/live_location/<int:bus_id>")
def get_parent_live_location(bus_id):

    if "parent_id" not in session:

        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT

            latitude,
            longitude,
            current_stop,
            speed,
            trip_status,

            TIME_FORMAT(
                updated_at,
                '%h:%i %p'
            ) AS last_updated,

            TIME_FORMAT(
                eta,
                '%h:%i %p'
            ) AS eta

        FROM live_bus_location

        WHERE bus_id = %s

        ORDER BY updated_at DESC

        LIMIT 1

    """, (bus_id,))

    location = cursor.fetchone()

    cursor.close()
    conn.close()

    if location:

        return jsonify({

            "success": True,

            "latitude": float(location["latitude"])
            if location["latitude"] is not None
            else None,

            "longitude": float(location["longitude"])
            if location["longitude"] is not None
            else None,

            "current_stop": location["current_stop"],

            "speed": float(location["speed"])
            if location["speed"] is not None
            else 0,

            "trip_status": location["trip_status"],

            "last_updated": location["last_updated"],

            "eta": location["eta"]

        })

    return jsonify({

        "success": False,

        "message": "Live bus location is not available."

    })
    
# ==========================================
# PARENT NOTIFICATIONS
# ==========================================

@app.route("/parent/notifications")
def parent_notifications():

    # ==========================================
    # CHECK PARENT LOGIN
    # ==========================================

    if "parent_id" not in session:

        return redirect("/login")


    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)


    try:

        # ==========================================
        # GET PARENT DETAILS
        # ==========================================

        cursor.execute("""
            SELECT

                p.parent_id,
                p.parent_name,

                s.id AS student_id,
                s.student_name

            FROM parents p

            LEFT JOIN students s
                ON p.student_id = s.id

            WHERE p.parent_id = %s

            LIMIT 1
        """, (session["parent_id"],))


        parent_student = cursor.fetchone()


        # ==========================================
        # GET ONLY THIS PARENT'S NOTIFICATIONS
        # ==========================================

        cursor.execute("""
            SELECT

                n.id AS notification_id,

                n.title,

                n.message,

                n.notification_type,

                n.created_at,

                pn.is_read


            FROM parent_notifications pn


            INNER JOIN notifications n
                ON pn.notification_id = n.id


            WHERE pn.parent_id = %s

                AND n.status = 'Active'


            ORDER BY n.created_at DESC

        """, (session["parent_id"],))


        notifications = cursor.fetchall()


    finally:

        cursor.close()

        conn.close()


    # ==========================================
    # LOAD PAGE
    # ==========================================

    return render_template(

        "parent/notifications.html",

        parent_student=parent_student,

        notifications=notifications,

        active_page="notifications"

    )
# =====================================================
# PARENT PROFILE
# =====================================================

@app.route("/parent/profile")
def parent_profile():

    # ==========================================
    # CHECK PARENT LOGIN
    # ==========================================

    if "parent_id" not in session:
        return redirect("/login")


    # ==========================================
    # DATABASE CONNECTION
    # ==========================================

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    # ==========================================
    # GET COMPLETE PROFILE DATA
    # ==========================================

    cursor.execute("""
        SELECT

            /* ==================================
               PARENT DETAILS
            ================================== */

            p.parent_id,
            p.parent_name,
            p.parent_phone,
            p.username,
            p.profile_image AS parent_profile_image,
            p.created_at AS parent_created_at,


            /* ==================================
               STUDENT DETAILS
            ================================== */

            s.id AS student_id,
            s.student_name,
            s.roll_number,
            s.phone AS student_phone,
            s.email AS student_email,
            s.department,
            s.semester,
            s.boarding_point,
            s.stop_id,
            s.route_id AS student_route_id,
            s.bus_id AS student_bus_id,
            s.profile_image AS student_profile_image,


            /* ==================================
               BUS DETAILS
            ================================== */

            b.bus_id,
            b.bus_number,
            b.driver_name,
            b.capacity,
            b.occupied_seats,
            b.available_seats,


            /* ==================================
               ROUTE DETAILS
            ================================== */

            r.route_id,
            r.route_name,
            r.source,
            r.destination,
            r.distance,
            r.estimated_time,
            r.status AS route_status


        FROM parents p


        /* ======================================
           GET LINKED STUDENT
        ====================================== */

        LEFT JOIN students s
            ON p.student_id = s.id


        /* ======================================
           GET STUDENT BUS ASSIGNMENT
        ====================================== */

        LEFT JOIN student_bus_assignment sba
            ON s.id = sba.student_id


        /* ======================================
           GET BUS
        ====================================== */

        LEFT JOIN buses b
            ON sba.bus_id = b.bus_id


        /* ======================================
           GET ROUTE
        ====================================== */

        LEFT JOIN routes r
            ON b.route_id = r.route_id


        WHERE p.parent_id = %s

        LIMIT 1

    """, (session["parent_id"],))


    # ==========================================
    # FETCH PROFILE DATA
    # ==========================================

    profile_data = cursor.fetchone()


    # ==========================================
    # CLOSE DATABASE
    # ==========================================

    cursor.close()
    conn.close()


    # ==========================================
    # RENDER PROFILE PAGE
    # ==========================================

    return render_template(

        "parent/profile.html",

        profile_data=profile_data,

        active_page="profile"

    )
# ==========================================
# DRIVER DASHBOARD
# ==========================================

@app.route("/driver_dashboard")
def driver_dashboard():

    # -----------------------------
    # Check Driver Login Session
    # -----------------------------
    if "driver_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # =====================================================
    # Get Driver Information
    # =====================================================
    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id = %s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    # -----------------------------
    # Driver Not Found
    # -----------------------------
    if not driver:

        cursor.close()
        conn.close()

        session.clear()

        flash("Driver account not found.", "danger")

        return redirect(url_for("login"))

    # =====================================================
    # Get Assigned Bus
    # =====================================================
    cursor.execute("""
        SELECT *
        FROM buses
        WHERE bus_number = %s
    """, (driver["bus_number"],))

    bus = cursor.fetchone()

    # -----------------------------
    # Bus Not Found
    # -----------------------------
    if not bus:

        cursor.close()
        conn.close()

        flash("Assigned bus not found.", "warning")

        return redirect(url_for("login"))

    # =====================================================
    # Get Route Information
    # =====================================================
    cursor.execute("""
        SELECT *
        FROM routes
        WHERE route_id = %s
    """, (driver["route_id"],))

    route = cursor.fetchone()

    # -----------------------------
    # Route Not Found
    # -----------------------------
    if not route:

        cursor.close()
        conn.close()

        flash("Assigned route not found.", "warning")

        return redirect(url_for("login"))

    # =====================================================
    # Get Total Assigned Students
    # =====================================================
    cursor.execute("""
        SELECT COUNT(*) AS total_students
        FROM student_bus_assignment
        WHERE bus_id = %s
    """, (bus["bus_id"],))

    student_count = cursor.fetchone()["total_students"]

    # =====================================================
    # Get Latest Notifications
    # =====================================================
    cursor.execute("""
        SELECT *
        FROM notifications
        ORDER BY created_at DESC
        LIMIT 5
    """)

    notifications = cursor.fetchall()

    # =====================================================
    # Get Live Bus Location
    # =====================================================
    cursor.execute("""
        SELECT *
        FROM live_bus_location
        WHERE bus_id = %s
        ORDER BY updated_at DESC
        LIMIT 1
    """, (bus["bus_id"],))

    live_location = cursor.fetchone()

    from datetime import datetime

    current_hour = datetime.now().hour

    # =====================================================
    # Close Database Connection
    # =====================================================
    cursor.close()
    conn.close()

    # =====================================================
    # Load Driver Dashboard
    # =====================================================
    return render_template(
        "driver/dashboard.html",

        driver=driver,
        bus=bus,
        route=route,
        student_count=student_count,
        notifications=notifications,
        live_location=live_location,
        current_hour=current_hour
    )
    
# ==========================================
# DRIVER TRIP QR CODE
# ==========================================

@app.route("/driver/qr")
def driver_qr():

    # -----------------------------
    # Check Driver Login
    # -----------------------------

    if "driver_id" not in session:

        return redirect(url_for("login"))


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # -----------------------------
        # Get Active Trip
        # -----------------------------

        cursor.execute("""
            SELECT

                bt.*,
                b.bus_number,
                b.capacity,
                b.occupied_seats,
                b.available_seats

            FROM bus_trips bt

            JOIN buses b
            ON bt.bus_id = b.bus_id

            WHERE

                bt.driver_id = %s

                AND bt.status = 'ACTIVE'

            ORDER BY bt.trip_id DESC

            LIMIT 1
        """, (session["driver_id"],))


        trip = cursor.fetchone()


        if not trip:

            flash(
                "Please start the trip first to generate the QR Code.",
                "warning"
            )

            return redirect(url_for("driver_dashboard"))


        # -----------------------------
        # QR Scan URL
        # -----------------------------

        qr_url = url_for(

            "student_scan_bus_qr",

            trip_token=trip["trip_token"],

            _external=True

        )


        # -----------------------------
        # Generate QR Image
        # -----------------------------

        qr = qrcode.QRCode(

            version=1,

            box_size=10,

            border=4

        )


        qr.add_data(qr_url)

        qr.make(fit=True)


        qr_image = qr.make_image(

            fill_color="black",

            back_color="white"

        )


        # -----------------------------
        # Convert Image to Base64
        # -----------------------------

        buffer = BytesIO()

        qr_image.save(

            buffer,

            format="PNG"

        )


        qr_base64 = base64.b64encode(

            buffer.getvalue()

        ).decode("utf-8")


        return render_template(

            "driver/driver_qr.html",

            trip=trip,

            qr_base64=qr_base64

        )


    finally:

        cursor.close()
        conn.close()

# ==========================================
# DRIVER LIVE TRACKING
# ==========================================

@app.route("/driver/live_tracking")
def driver_live_tracking():

    # ==========================================
    # LOGIN CHECK
    # ==========================================

    if "driver_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ==========================================
    # GET DRIVER
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id = %s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    if not driver:

        cursor.close()
        conn.close()

        flash("Driver not found.", "danger")

        return redirect(url_for("driver_dashboard"))

    # ==========================================
    # GET BUS
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM buses
        WHERE bus_number = %s
    """, (driver["bus_number"],))

    bus = cursor.fetchone()

    if not bus:

        cursor.close()
        conn.close()

        flash("Bus not found.", "danger")

        return redirect(url_for("driver_dashboard"))

    # ==========================================
    # GET ROUTE
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM routes
        WHERE route_id = %s
    """, (driver["route_id"],))

    route = cursor.fetchone()

    # ==========================================
    # GET ROUTE STOPS
    # ==========================================

    cursor.execute("""
        SELECT
            id,
            route_id,
            stop_name,
            stop_order,
            latitude,
            longitude
        FROM bus_stops
        WHERE route_id = %s
        ORDER BY stop_order ASC
    """, (driver["route_id"],))

    route_stops = cursor.fetchall()

    # ==========================================
    # GET CURRENT STOP
    # ==========================================

    cursor.execute("""
        SELECT current_stop
        FROM live_bus_location
        WHERE bus_id = %s
    """, (bus["bus_id"],))

    live_data = cursor.fetchone()

    current_stop = ""

    if live_data and live_data["current_stop"]:
        current_stop = live_data["current_stop"]

    # ==========================================
    # FIND CURRENT STOP ORDER
    # ==========================================

    current_stop_order = 0

    for stop in route_stops:

        if stop["stop_name"] == current_stop:

            current_stop_order = stop["stop_order"]

            break

    # ==========================================
    # ROUTE PROGRESS
    # ==========================================

    total_stops = len(route_stops)

    completed_stops = current_stop_order

    remaining_stops = max(
        total_stops - current_stop_order,
        0
    )

    if total_stops > 0:

        progress_percentage = int(
            (completed_stops / total_stops) * 100
        )

        progress_percentage = min(
            max(progress_percentage, 0),
            100
        )

    else:

        progress_percentage = 0

    # ==========================================
    # NEXT STOP
    # ==========================================

    next_stop = "Destination Reached"

    for stop in route_stops:

        if stop["stop_order"] > current_stop_order:

            next_stop = stop["stop_name"]

            break

    # ==========================================
    # DISTANCE / ETA INITIAL VALUES
    #
    # These are updated LIVE by JavaScript
    # using the driver's GPS location.
    # ==========================================

    distance_remaining = "--"

    eta_to_next = "--"

    # ==========================================
    # CLOSE DATABASE
    # ==========================================

    cursor.close()
    conn.close()

    # ==========================================
    # SEND DATA TO TEMPLATE
    # ==========================================

    return render_template(
        "driver/live_tracking.html",

        driver=driver,

        bus=bus,

        route=route,

        route_stops=route_stops,

        current_stop=current_stop,

        current_stop_order=current_stop_order,

        total_stops=total_stops,

        completed_stops=completed_stops,

        remaining_stops=remaining_stops,

        progress_percentage=progress_percentage,

        next_stop=next_stop,

        distance_remaining=distance_remaining,

        eta_to_next=eta_to_next
    )
# ==========================================
# START TRIP
# ==========================================

@app.route("/driver/start_trip", methods=["POST"])
def start_trip():

    # -----------------------------
    # Driver Login Check
    # -----------------------------

    if "driver_id" not in session:

        return jsonify({
            "success": False,
            "message": "Login required."
        }), 401


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # -----------------------------
        # Get Driver
        # -----------------------------

        cursor.execute("""
            SELECT *
            FROM drivers
            WHERE id = %s
        """, (session["driver_id"],))

        driver = cursor.fetchone()


        if not driver:

            return jsonify({
                "success": False,
                "message": "Driver not found."
            })


        # -----------------------------
        # Get Assigned Bus
        # -----------------------------

        cursor.execute("""
            SELECT *
            FROM buses
            WHERE bus_number = %s
        """, (driver["bus_number"],))

        bus = cursor.fetchone()


        if not bus:

            return jsonify({
                "success": False,
                "message": "Assigned bus not found."
            })


        # -----------------------------
        # Check Existing Active Trip
        # -----------------------------

        cursor.execute("""
            SELECT *
            FROM bus_trips
            WHERE driver_id = %s
            AND status = 'ACTIVE'
            ORDER BY trip_id DESC
            LIMIT 1
        """, (driver["id"],))

        active_trip = cursor.fetchone()


        if active_trip:

            return jsonify({

                "success": True,

                "message": "Trip is already running.",

                "trip_token": active_trip["trip_token"]

            })


        # -----------------------------
        # Generate Unique QR Token
        # -----------------------------

        trip_token = secrets.token_urlsafe(32)


        # -----------------------------
        # Create New Bus Trip
        # -----------------------------

        cursor.execute("""
            INSERT INTO bus_trips (

                bus_id,
                driver_id,
                trip_token,
                status

            )

            VALUES (

                %s,
                %s,
                %s,
                'ACTIVE'

            )
        """, (

            bus["bus_id"],
            driver["id"],
            trip_token

        ))


        trip_id = cursor.lastrowid


        # -----------------------------
        # Reset Seat Availability
        # New Trip Starts
        # -----------------------------

        cursor.execute("""
            UPDATE buses
            SET
                occupied_seats = 0,
                available_seats = capacity
            WHERE bus_id = %s
        """, (bus["bus_id"],))


        # -----------------------------
        # Update Driver Status
        # -----------------------------

        cursor.execute("""
            UPDATE drivers
            SET

                status = 'On Trip',
                trip_status = 'On Trip'

            WHERE id = %s
        """, (driver["id"],))


        # -----------------------------
        # Insert Trip History
        # -----------------------------

        cursor.execute("""
            INSERT INTO trip_history (

                driver_id,
                bus_id,
                route_id,
                trip_type,
                trip_date,
                start_time,
                status

            )

            VALUES (

                %s,
                %s,
                %s,
                %s,
                CURDATE(),
                NOW(),
                'Running'

            )
        """, (

            driver["id"],
            bus["bus_id"],
            driver["route_id"],
            "Morning Pickup"

        ))


        # -----------------------------
        # Save Changes
        # -----------------------------

        conn.commit()


        return jsonify({

            "success": True,

            "message": "Trip Started Successfully.",

            "trip_id": trip_id,

            "trip_token": trip_token

        })


    except Exception as e:

        conn.rollback()

        print("START TRIP ERROR:", e)

        return jsonify({

            "success": False,

            "message": "Unable to start trip."

        }), 500


    finally:

        cursor.close()
        conn.close()
# ==========================================
# END TRIP
# ==========================================

@app.route("/driver/end_trip", methods=["POST"])
def end_trip():

    if "driver_id" not in session:

        return jsonify({

            "success": False,

            "message": "Login required."

        }), 401


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        # -----------------------------------
        # Get Driver
        # -----------------------------------

        cursor.execute("""
            SELECT *
            FROM drivers
            WHERE id = %s
        """, (session["driver_id"],))

        driver = cursor.fetchone()


        if not driver:

            return jsonify({

                "success": False,

                "message": "Driver not found."

            })


        # -----------------------------------
        # Complete Active Bus Trip
        # -----------------------------------

        cursor.execute("""
            UPDATE bus_trips

            SET

                end_time = NOW(),

                status = 'COMPLETED'

            WHERE

                driver_id = %s

                AND status = 'ACTIVE'
        """, (driver["id"],))


        # -----------------------------------
        # Update Driver Status
        # -----------------------------------

        cursor.execute("""
            UPDATE drivers

            SET

                status = 'Available',

                trip_status = 'Available'

            WHERE id = %s
        """, (driver["id"],))


        # -----------------------------------
        # Update Trip History
        # -----------------------------------

        cursor.execute("""
            UPDATE trip_history

            SET

                end_time = NOW(),

                status = 'Completed',

                end_lat = %s,

                end_lng = %s

            WHERE

                driver_id = %s

                AND status = 'Running'

            ORDER BY id DESC

            LIMIT 1
        """, (

            driver["current_lat"],
            driver["current_lng"],
            driver["id"]

        ))
        
        # ===================================
        # RESET BUS SEATS AFTER TRIP ENDS
        # ===================================
        
        cursor.execute("""
            UPDATE buses
            SET 
                occupied_seats = 0,
                available_seats = capacity
            WHERE bus_number = %s   
        """, (driver["bus_number"],))
        
        # -----------------------------------
        # Save Changes
        # -----------------------------------


        conn.commit()


        return jsonify({

            "success": True,

            "message": "Trip Completed Successfully."

        })


    except Exception as e:

        conn.rollback()

        print("END TRIP ERROR:", e)

        return jsonify({

            "success": False,

            "message": "Unable to complete trip."

        }), 500


    finally:

        cursor.close()
        conn.close()

# ==========================================
# UPDATE DRIVER LIVE LOCATION
# ==========================================

@app.route("/driver/update_location", methods=["POST"])
def update_location():

    # ======================================
    # DRIVER LOGIN CHECK
    # ======================================

    if "driver_id" not in session:

        return jsonify({

            "success": False,

            "message": "Driver not logged in."

        }), 401

    conn = None
    cursor = None

    try:

        # ======================================
        # GET JSON DATA
        # ======================================

        data = request.get_json()

        latitude = data.get("latitude")
        longitude = data.get("longitude")
        speed = data.get("speed", 0)

        if latitude is None or longitude is None:

            return jsonify({

                "success": False,

                "message": "Invalid GPS location."

            }), 400

        try:

            speed = int(float(speed))

        except:

            speed = 0

        # ======================================
        # DATABASE CONNECTION
        # ======================================

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)

        # ======================================
        # GET DRIVER DETAILS
        # ======================================

        cursor.execute("""

            SELECT *

            FROM drivers

            WHERE id=%s

        """, (

            session["driver_id"],

        ))

        driver = cursor.fetchone()

        if not driver:

            return jsonify({

                "success": False,

                "message": "Driver not found."

            }), 404

        # ======================================
        # GET BUS DETAILS
        # ======================================

        cursor.execute("""

            SELECT *

            FROM buses

            WHERE bus_number=%s

        """, (

            driver["bus_number"],

        ))

        bus = cursor.fetchone()

        if not bus:

            return jsonify({

                "success": False,

                "message": "Bus not assigned."

            }), 404

        # ======================================
        # UPDATE DRIVER TABLE
        # ======================================

        cursor.execute("""

            UPDATE drivers

            SET

                current_lat=%s,

                current_lng=%s,

                trip_status='On Trip',

                last_location_update=NOW()

            WHERE id=%s

        """, (

            latitude,

            longitude,

            driver["id"]

        ))

               # ======================================
        # CHECK LIVE BUS LOCATION
        # ======================================

        cursor.execute("""

            SELECT id

            FROM live_bus_location

            WHERE bus_id=%s

        """, (

            bus["bus_id"],

        ))

        live = cursor.fetchone()

        # ======================================
        # UPDATE LIVE LOCATION
        # ======================================

        if live:

            cursor.execute("""

                UPDATE live_bus_location

                SET

                    latitude=%s,

                    longitude=%s,

                    speed=%s,
                    
                    trip_status='Online',

                    updated_at=NOW()

                WHERE bus_id=%s

            """, (

                latitude,

                longitude,

                speed,

                bus["bus_id"]

            ))

        # ======================================
        # INSERT LIVE LOCATION
        # ======================================

        else:

            cursor.execute("""

                INSERT INTO live_bus_location(

                    bus_id,

                    latitude,

                    longitude,

                    current_stop,

                    speed,
                    
                    trip_status

                )

                VALUES(

                    %s,

                    %s,

                    %s,

                    '',

                    %s,
                    
                    'Online'

                )

            """, (

                bus["bus_id"],

                latitude,

                longitude,

                speed

            ))

        # ======================================
        # SAVE CHANGES
        # ======================================

        conn.commit()

        return jsonify({

            "success": True,

            "message": "Driver location updated successfully."

        })    
    except Exception as e:

        if conn:
            conn.rollback()

        print("UPDATE LOCATION ERROR:", e)

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# ==========================================
# GET DRIVER LIVE LOCATION
# ==========================================

@app.route("/driver/live_location")
def driver_live_location():

    if "driver_id" not in session:
        return jsonify({"success": False}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Driver
    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id=%s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    if not driver:

        cursor.close()
        conn.close()

        return jsonify({"success": False})

    # Bus
    cursor.execute("""
        SELECT bus_id
        FROM buses
        WHERE bus_number=%s
    """, (driver["bus_number"],))

    bus = cursor.fetchone()

    if not bus:

        cursor.close()
        conn.close()

        return jsonify({"success": False})

    # Live Location
    cursor.execute("""
        SELECT
            latitude,
            longitude,
            updated_at
        FROM live_bus_location
        WHERE bus_id=%s
    """, (bus["bus_id"],))

    live = cursor.fetchone()

    cursor.close()
    conn.close()

    if not live:

        return jsonify({
            "success": False
        })

    return jsonify({

        "success": True,

        "latitude": float(live["latitude"]),

        "longitude": float(live["longitude"]),

        "updated_at": str(live["updated_at"])

    })

# ==========================================
# DRIVER NOTIFICATIONS
# ==========================================

@app.route("/driver/notifications")
def driver_notifications():

    # --------------------------------------
    # DRIVER LOGIN CHECK
    # --------------------------------------

    if "driver_id" not in session:

        return redirect(url_for("login"))


    # --------------------------------------
    # DATABASE CONNECTION
    # --------------------------------------

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)


    try:

        # --------------------------------------
        # DRIVER INFORMATION
        # --------------------------------------

        cursor.execute("""
            SELECT *
            FROM drivers
            WHERE id = %s
        """, (session["driver_id"],))

        driver = cursor.fetchone()


        # --------------------------------------
        # GET ONLY THIS DRIVER'S NOTIFICATIONS
        # --------------------------------------

        cursor.execute("""
            SELECT

                n.id AS notification_id,

                n.title,

                n.message,

                n.notification_type,

                n.created_at,

                dn.is_read


            FROM driver_notifications dn


            INNER JOIN notifications n
                ON dn.notification_id = n.id


            WHERE dn.driver_id = %s

                AND n.status = 'Active'


            ORDER BY n.created_at DESC

        """, (session["driver_id"],))


        notifications = cursor.fetchall()


    finally:

        cursor.close()

        conn.close()


    # --------------------------------------
    # LOAD PAGE
    # --------------------------------------

    return render_template(

        "driver/notifications.html",

        driver=driver,

        notifications=notifications

    )
# =========================================================
# DRIVER - STUDENTS
# =========================================================

@app.route("/driver/students")
def driver_students():

    # -----------------------------------------------------
    # Driver Login Check
    # -----------------------------------------------------
    if "driver_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # -----------------------------------------------------
    # Get Logged-in Driver
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id = %s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    if not driver:

        cursor.close()
        conn.close()

        session.clear()

        flash("Driver account not found.", "danger")

        return redirect(url_for("login"))

    # -----------------------------------------------------
    # Get Assigned Bus
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM buses
        WHERE bus_number = %s
    """, (driver["bus_number"],))

    bus = cursor.fetchone()

    if not bus:

        cursor.close()
        conn.close()

        flash("Assigned bus not found.", "warning")

        return redirect(url_for("driver_dashboard"))

    # -----------------------------------------------------
    # Get Students Assigned to This Bus
    #
    # We use the students.bus_id field because that field
    # exists in your current students table.
    # -----------------------------------------------------
    cursor.execute("""
        SELECT
            id,
            student_name,
            roll_number,
            phone,
            boarding_point,
            stop_id,
            route_id,
            bus_id,
            profile_image
        FROM students
        WHERE bus_id = %s
        ORDER BY student_name ASC
    """, (bus["bus_id"],))

    students = cursor.fetchall()

    # -----------------------------------------------------
    # Total Students
    # -----------------------------------------------------
    total_students = len(students)

    # -----------------------------------------------------
    # Close Database
    # -----------------------------------------------------
    cursor.close()
    conn.close()

    # -----------------------------------------------------
    # Render Page
    # -----------------------------------------------------
    return render_template(
        "driver/students.html",
        driver=driver,
        bus=bus,
        students=students,
        total_students=total_students
    )
    
# ==========================================
# DRIVER - MY BUS
# ==========================================

@app.route("/driver/my_bus")
def driver_my_bus():

    # ------------------------------------------
    # Check Driver Login
    # ------------------------------------------
    if "driver_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ------------------------------------------
    # Get Logged-in Driver
    # ------------------------------------------
    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id = %s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    if not driver:

        cursor.close()
        conn.close()

        session.clear()

        flash("Driver account not found.", "danger")

        return redirect(url_for("login"))

    # ------------------------------------------
    # Get Assigned Bus
    # ------------------------------------------
    cursor.execute("""
        SELECT *
        FROM buses
        WHERE bus_number = %s
    """, (driver["bus_number"],))

    bus = cursor.fetchone()

    if not bus:

        cursor.close()
        conn.close()

        flash("Assigned bus not found.", "warning")

        return redirect(url_for("driver_dashboard"))

    # ------------------------------------------
    # Get Assigned Route
    # ------------------------------------------
    cursor.execute("""
        SELECT *
        FROM routes
        WHERE route_id = %s
    """, (driver["route_id"],))

    route = cursor.fetchone()

    # ------------------------------------------
    # Get Latest Live Location
    # ------------------------------------------
    cursor.execute("""
        SELECT *
        FROM live_bus_location
        WHERE bus_id = %s
        ORDER BY updated_at DESC
        LIMIT 1
    """, (bus["bus_id"],))

    live_location = cursor.fetchone()

    # ------------------------------------------
    # Close Database
    # ------------------------------------------
    cursor.close()
    conn.close()

    # ------------------------------------------
    # Open My Bus Page
    # ------------------------------------------
    return render_template(
        "driver/my_bus.html",
        driver=driver,
        bus=bus,
        route=route,
        live_location=live_location
    )
    
# =========================================================
# DRIVER - ROUTE DETAILS
# =========================================================

@app.route("/driver/route_details")
def driver_route_details():

    # -----------------------------------------------------
    # DRIVER LOGIN CHECK
    # -----------------------------------------------------
    if "driver_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # -----------------------------------------------------
    # GET DRIVER
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id = %s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    if not driver:

        cursor.close()
        conn.close()

        session.clear()

        flash("Driver account not found.", "danger")

        return redirect(url_for("login"))

    # -----------------------------------------------------
    # GET ASSIGNED BUS
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM buses
        WHERE bus_number = %s
    """, (driver["bus_number"],))

    bus = cursor.fetchone()

    if not bus:

        cursor.close()
        conn.close()

        flash("Assigned bus not found.", "warning")

        return redirect(url_for("driver_dashboard"))

    # -----------------------------------------------------
    # GET ASSIGNED ROUTE
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM routes
        WHERE route_id = %s
    """, (driver["route_id"],))

    route = cursor.fetchone()

    if not route:

        cursor.close()
        conn.close()

        flash("Assigned route not found.", "warning")

        return redirect(url_for("driver_dashboard"))

    # -----------------------------------------------------
    # GET ROUTE STOPS
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM bus_stops
        WHERE route_id = %s
        ORDER BY stop_order ASC
    """, (driver["route_id"],))

    route_stops = cursor.fetchall()

    # -----------------------------------------------------
    # TOTAL STOPS
    # -----------------------------------------------------
    total_stops = len(route_stops)

    # -----------------------------------------------------
    # GET CURRENT LIVE LOCATION
    # -----------------------------------------------------
    cursor.execute("""
        SELECT *
        FROM live_bus_location
        WHERE bus_id = %s
        ORDER BY updated_at DESC
        LIMIT 1
    """, (bus["bus_id"],))

    live_location = cursor.fetchone()

    # -----------------------------------------------------
    # CURRENT STOP
    # -----------------------------------------------------
    current_stop = ""

    if live_location:

        current_stop = live_location.get("current_stop") or ""

    # -----------------------------------------------------
    # CURRENT STOP ORDER
    # -----------------------------------------------------
    current_stop_order = 0

    for stop in route_stops:

        if stop.get("stop_name") == current_stop:

            current_stop_order = stop.get("stop_order", 0)

            break

    # -----------------------------------------------------
    # CLOSE DATABASE
    # -----------------------------------------------------
    cursor.close()
    conn.close()

    # -----------------------------------------------------
    # RENDER ROUTE DETAILS
    # -----------------------------------------------------
    return render_template(
        "driver/route_details.html",

        driver=driver,

        bus=bus,

        route=route,

        route_stops=route_stops,

        total_stops=total_stops,

        current_stop=current_stop,

        current_stop_order=current_stop_order,

        live_location=live_location
    )
    
# ==========================================
# DRIVER TRIP HISTORY
# ==========================================

@app.route("/driver/trip_history")
def driver_trip_history():

    # ------------------------------------------
    # Driver Login Check
    # ------------------------------------------

    if "driver_id" not in session:

        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # ------------------------------------------
        # Get Logged-in Driver
        # ------------------------------------------

        cursor.execute("""
            SELECT *
            FROM drivers
            WHERE id = %s
        """, (session["driver_id"],))

        driver = cursor.fetchone()

        if not driver:

            session.clear()

            flash("Driver account not found.", "danger")

            return redirect(url_for("login"))

        # ------------------------------------------
        # Get Trip History
        # ------------------------------------------

        cursor.execute("""
            SELECT
                th.id,
                th.trip_date,
                th.trip_type,
                th.start_time,
                th.end_time,
                th.status,
                b.bus_number,
                r.route_name
            FROM trip_history th

            LEFT JOIN buses b
                ON th.bus_id = b.bus_id

            LEFT JOIN routes r
                ON th.route_id = r.route_id

            WHERE th.driver_id = %s

            ORDER BY
                th.trip_date DESC,
                th.start_time DESC,
                th.id DESC
        """, (driver["id"],))

        trips = cursor.fetchall()

        # ------------------------------------------
        # Total Trips
        # ------------------------------------------

        total_trips = len(trips)

        return render_template(
            "driver/trip_history.html",
            driver=driver,
            trips=trips,
            total_trips=total_trips
        )

    finally:

        cursor.close()
        conn.close()

        
# ==========================================================
# DRIVER - SEND EMERGENCY ALERT
# ==========================================================

@app.route("/driver/emergency", methods=["POST"])
def driver_emergency():

    # ======================================================
    # CHECK DRIVER LOGIN
    # ======================================================

    if "driver_id" not in session:

        return jsonify({
            "success": False,
            "message": "Driver not logged in."
        }), 401


    driver_id = session["driver_id"]


    # ======================================================
    # GET JSON DATA
    # ======================================================

    data = request.get_json(silent=True) or {}


    emergency_type = (
        data.get("emergency_type", "")
        or ""
    ).strip()


    latitude = data.get("latitude")

    longitude = data.get("longitude")


    message = (
        data.get("message", "")
        or ""
    ).strip()


    # ======================================================
    # VALID EMERGENCY TYPES
    # ======================================================

    valid_emergency_types = [

        "Accident",

        "Medical Emergency",

        "Bus Breakdown",

        "SOS / Other Emergency"

    ]


    if emergency_type not in valid_emergency_types:

        return jsonify({

            "success": False,

            "message": "Invalid emergency type."

        }), 400


    # ======================================================
    # VALIDATE GPS
    # ======================================================

    if latitude is not None:

        try:

            latitude = float(latitude)

        except (TypeError, ValueError):

            return jsonify({

                "success": False,

                "message": "Invalid latitude."

            }), 400


    if longitude is not None:

        try:

            longitude = float(longitude)

        except (TypeError, ValueError):

            return jsonify({

                "success": False,

                "message": "Invalid longitude."

            }), 400


    # ======================================================
    # DATABASE CONNECTION
    # ======================================================

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)


    try:

        # ==================================================
        # GET LOGGED-IN DRIVER
        # ==================================================

        cursor.execute(
            """
            SELECT
                id,
                driver_name,
                bus_number,
                route_id,
                current_lat,
                current_lng
            FROM drivers
            WHERE id = %s
            """,
            (driver_id,)
        )


        driver = cursor.fetchone()


        if not driver:

            return jsonify({

                "success": False,

                "message": "Driver record not found."

            }), 404


        # ==================================================
        # GET DRIVER BUS
        # ==================================================

        cursor.execute(
            """
            SELECT
                bus_id,
                bus_number,
                route_id
            FROM buses
            WHERE bus_number = %s
            LIMIT 1
            """,
            (driver["bus_number"],)
        )


        bus = cursor.fetchone()


        # ==================================================
        # GET BUS ID
        # ==================================================

        bus_id = None

        if bus:

            bus_id = bus["bus_id"]


        # ==================================================
        # GET ROUTE ID
        #
        # Driver table already contains route_id.
        # Use that as the primary source.
        # If unavailable, use bus.route_id.
        # ==================================================

        route_id = driver["route_id"]


        if route_id is None and bus:

            route_id = bus["route_id"]


        # ==================================================
        # CHECK ROUTE
        # ==================================================

        if route_id is not None:

            cursor.execute(
                """
                SELECT route_id
                FROM routes
                WHERE route_id = %s
                LIMIT 1
                """,
                (route_id,)
            )

            route = cursor.fetchone()


            if not route:

                route_id = None


        # ==================================================
        # FALLBACK GPS FROM DRIVER TABLE
        #
        # If JavaScript could not send GPS but the driver
        # already has current location stored in database,
        # use that location.
        # ==================================================

        if latitude is None:

            latitude = driver["current_lat"]


        if longitude is None:

            longitude = driver["current_lng"]


        # ==================================================
        # DEFAULT MESSAGE
        # ==================================================

        if not message:

            if emergency_type == "Accident":

                message = (
                    "The driver has reported a bus accident. "
                    "Immediate attention is required."
                )


            elif emergency_type == "Medical Emergency":

                message = (
                    "The driver has reported a medical emergency. "
                    "Immediate medical assistance may be required."
                )


            elif emergency_type == "Bus Breakdown":

                message = (
                    "The driver has reported a bus breakdown "
                    "or technical issue."
                )


            elif emergency_type == "SOS / Other Emergency":

                message = (
                    "The driver has sent an urgent SOS / "
                    "emergency alert."
                )


            else:

                message = (
                    "The driver has reported an emergency."
                )


        # ==================================================
        # INSERT EMERGENCY ALERT
        # ==================================================

        cursor.execute(
            """
            INSERT INTO emergency_alerts
            (
                driver_id,
                emergency_type,
                bus_id,
                route_id,
                latitude,
                longitude,
                message,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'Pending'
            )
            """,
            (
                driver_id,
                emergency_type,
                bus_id,
                route_id,
                latitude,
                longitude,
                message
            )
        )


        # ==================================================
        # GET NEW EMERGENCY ID
        # ==================================================

        emergency_id = cursor.lastrowid


        # ==================================================
        # COMMIT
        # ==================================================

        conn.commit()


        # ==================================================
        # TERMINAL LOG
        # ==================================================

        print(
            "=========================================="
        )

        print(
            "EMERGENCY ALERT CREATED"
        )

        print(
            "Emergency ID:",
            emergency_id
        )

        print(
            "Driver ID:",
            driver_id
        )

        print(
            "Driver Name:",
            driver["driver_name"]
        )

        print(
            "Emergency Type:",
            emergency_type
        )

        print(
            "Bus Number:",
            driver["bus_number"]
        )

        print(
            "Bus ID:",
            bus_id
        )

        print(
            "Route ID:",
            route_id
        )

        print(
            "Latitude:",
            latitude
        )

        print(
            "Longitude:",
            longitude
        )

        print(
            "Status: Pending"
        )

        print(
            "=========================================="
        )


        # ==================================================
        # RETURN SUCCESS
        # ==================================================

        return jsonify({

            "success": True,

            "message":
                "Emergency alert sent successfully.",

            "emergency_id":
                emergency_id,

            "driver_id":
                driver_id,

            "driver_name":
                driver["driver_name"],

            "emergency_type":
                emergency_type,

            "bus_id":
                bus_id,

            "bus_number":
                driver["bus_number"],

            "route_id":
                route_id,

            "latitude":
                latitude,

            "longitude":
                longitude,

            "status":
                "Pending"

        }), 201


    # ======================================================
    # ERROR HANDLING
    # ======================================================

    except Exception as error:

        conn.rollback()


        print(
            "=========================================="
        )

        print(
            "DRIVER EMERGENCY ERROR:"
        )

        print(
            str(error)
        )

        print(
            "=========================================="
        )


        return jsonify({

            "success": False,

            "message":
                "Unable to create emergency alert.",

            "error":
                str(error)

        }), 500


    # ======================================================
    # CLOSE DATABASE
    # ======================================================

    finally:

        cursor.close()

        conn.close()
        
@app.route("/driver/settings")
def driver_settings():

    if "driver_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id = %s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    cursor.close()
    conn.close()

    if not driver:
        session.clear()
        flash("Driver account not found.", "danger")
        return redirect(url_for("login"))

    return render_template(
        "driver/settings.html",
        driver=driver
    )
    
# ==========================================
# DRIVER MY PROFILE
# ==========================================

@app.route("/driver/profile")
def driver_profile():

    # ------------------------------------------
    # Driver Login Check
    # ------------------------------------------

    if "driver_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ------------------------------------------
    # Get Driver Information
    # ------------------------------------------

    cursor.execute("""
        SELECT *
        FROM drivers
        WHERE id = %s
    """, (session["driver_id"],))

    driver = cursor.fetchone()

    # ------------------------------------------
    # Driver Not Found
    # ------------------------------------------

    if not driver:

        cursor.close()
        conn.close()

        session.clear()

        flash("Driver account not found.", "danger")

        return redirect(url_for("login"))

    # ------------------------------------------
    # Get Assigned Bus
    # ------------------------------------------

    cursor.execute("""
        SELECT *
        FROM buses
        WHERE bus_number = %s
    """, (driver["bus_number"],))

    bus = cursor.fetchone()

    # ------------------------------------------
    # Get Assigned Route
    # ------------------------------------------

    cursor.execute("""
        SELECT *
        FROM routes
        WHERE route_id = %s
    """, (driver["route_id"],))

    route = cursor.fetchone()

    # ------------------------------------------
    # Close Database
    # ------------------------------------------

    cursor.close()
    conn.close()

    # ------------------------------------------
    # Render Profile
    # ------------------------------------------

    return render_template(
        "driver/profile.html",
        driver=driver,
        bus=bus,
        route=route
    )
    
# =====================================================
# DRIVER CHANGE PASSWORD
# =====================================================

@app.route("/driver/change-password", methods=["GET", "POST"])
def driver_change_password():

    # ------------------------------------------
    # Driver Login Check
    # ------------------------------------------

    if "driver_id" not in session:
        return redirect(url_for("login"))

    # ------------------------------------------
    # POST - Change Password
    # ------------------------------------------

    if request.method == "POST":

        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # ------------------------------------------
        # Empty Field Check
        # ------------------------------------------

        if not current_password or not new_password or not confirm_password:

            flash(
                "Please fill in all password fields.",
                "danger"
            )

            return redirect(url_for("driver_change_password"))

        # ------------------------------------------
        # New Password Match
        # ------------------------------------------

        if new_password != confirm_password:

            flash(
                "New password and confirm password do not match.",
                "danger"
            )

            return redirect(url_for("driver_change_password"))

        # ------------------------------------------
        # Password Length
        # ------------------------------------------

        if len(new_password) < 8:

            flash(
                "New password must contain at least 8 characters.",
                "danger"
            )

            return redirect(url_for("driver_change_password"))

        # ------------------------------------------
        # Get Driver
        # ------------------------------------------

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                driver_name,
                password
            FROM drivers
            WHERE id=%s
        """, (session["driver_id"],))

        driver = cursor.fetchone()

        # ------------------------------------------
        # Driver Not Found
        # ------------------------------------------

        if not driver:

            cursor.close()
            conn.close()

            session.clear()

            flash(
                "Driver account not found.",
                "danger"
            )

            return redirect(url_for("login"))

        # ------------------------------------------
        # Verify Current Password
        # ------------------------------------------

        try:

            ph.verify(
                driver["password"],
                current_password
            )

        except VerifyMismatchError:

            cursor.close()
            conn.close()

            flash(
                "Current password is incorrect.",
                "danger"
            )

            return redirect(url_for("driver_change_password"))

        # ------------------------------------------
        # Prevent Same Password
        # ------------------------------------------

        try:

            if ph.verify(driver["password"], new_password):

                cursor.close()
                conn.close()

                flash(
                    "New password must be different from your current password.",
                    "warning"
                )

                return redirect(url_for("driver_change_password"))

        except VerifyMismatchError:

            pass

        # ------------------------------------------
        # Hash New Password
        # ------------------------------------------

        new_password_hash = ph.hash(new_password)

        # ------------------------------------------
        # Update Password
        # ------------------------------------------

        cursor.execute("""
            UPDATE drivers
            SET password=%s
            WHERE id=%s
        """, (
            new_password_hash,
            driver["id"]
        ))

        conn.commit()

        cursor.close()
        conn.close()

        # ------------------------------------------
        # Success
        # ------------------------------------------

        flash(
            "Password changed successfully.",
            "success"
        )

        return redirect(url_for("driver_profile"))

    # ------------------------------------------
    # GET
    # ------------------------------------------

    return render_template(
        "driver/change_password.html"
    )
    
# =====================================================
# STUDENT - SAVE FCM TOKEN
# =====================================================

@app.route("/student/save-fcm-token", methods=["POST"])
def save_student_fcm_token():

    # -----------------------------------------
    # CHECK STUDENT LOGIN
    # -----------------------------------------

    if "student_id" not in session:

        return {
            "success": False,
            "message": "Student not logged in"
        }, 401


    # -----------------------------------------
    # GET TOKEN FROM JAVASCRIPT
    # -----------------------------------------

    data = request.get_json()

    fcm_token = data.get("fcm_token")


    # -----------------------------------------
    # VALIDATE TOKEN
    # -----------------------------------------

    if not fcm_token:

        return {
            "success": False,
            "message": "FCM token is missing"
        }, 400


    # -----------------------------------------
    # DATABASE CONNECTION
    # -----------------------------------------

    conn = get_db_connection()

    cursor = conn.cursor()


    try:

        # -----------------------------------------
        # CHECK IF TOKEN ALREADY EXISTS
        # -----------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM student_fcm_tokens
            WHERE student_id = %s
            AND fcm_token = %s
            """,
            (
                session["student_id"],
                fcm_token
            )
        )

        existing_token = cursor.fetchone()


        # -----------------------------------------
        # INSERT TOKEN IF NEW
        # -----------------------------------------

        if not existing_token:

            cursor.execute(
                """
                INSERT INTO student_fcm_tokens
                (
                    student_id,
                    fcm_token
                )
                VALUES
                (
                    %s,
                    %s
                )
                """,
                (
                    session["student_id"],
                    fcm_token
                )
            )

            conn.commit()


        return {
            "success": True,
            "message": "FCM token saved successfully"
        }


    except Exception as e:

        conn.rollback()

        print("FCM Token Error:", str(e))

        return {
            "success": False,
            "message": str(e)
        }, 500


    finally:

        cursor.close()

        conn.close()
        
# =====================================================
# PARENT - SAVE FCM TOKEN
# =====================================================

@app.route("/parent/save-fcm-token", methods=["POST"])
def save_parent_fcm_token():

    # CHECK PARENT LOGIN
    if "parent_id" not in session:

        return {
            "success": False,
            "message": "Parent not logged in"
        }, 401


    # GET DATA
    data = request.get_json()

    if not data:

        return {
            "success": False,
            "message": "Invalid request data"
        }, 400


    fcm_token = data.get("fcm_token")


    # VALIDATE TOKEN
    if not fcm_token:

        return {
            "success": False,
            "message": "FCM token is missing"
        }, 400


    # DATABASE CONNECTION
    conn = get_db_connection()
    cursor = conn.cursor()


    try:

        # CHECK WHETHER TOKEN ALREADY EXISTS
        cursor.execute(
            """
            SELECT id
            FROM parent_fcm_tokens
            WHERE parent_id = %s
            AND fcm_token = %s
            """,
            (
                session["parent_id"],
                fcm_token
            )
        )

        existing_token = cursor.fetchone()


        # INSERT ONLY IF NEW
        if not existing_token:

            cursor.execute(
                """
                INSERT INTO parent_fcm_tokens
                (
                    parent_id,
                    fcm_token
                )
                VALUES
                (
                    %s,
                    %s
                )
                """,
                (
                    session["parent_id"],
                    fcm_token
                )
            )

            conn.commit()


        return {
            "success": True,
            "message": "Parent FCM token saved successfully"
        }


    except Exception as e:

        conn.rollback()

        print("Parent FCM Token Error:", str(e))

        return {
            "success": False,
            "message": str(e)
        }, 500


    finally:

        cursor.close()
        conn.close()
        
# =====================================================
# DRIVER - SAVE FCM TOKEN
# =====================================================

@app.route("/driver/save-fcm-token", methods=["POST"])
def save_driver_fcm_token():

    # CHECK DRIVER LOGIN
    if "driver_id" not in session:

        return {
            "success": False,
            "message": "Driver not logged in"
        }, 401


    # GET TOKEN FROM JAVASCRIPT
    data = request.get_json()

    if not data:

        return {
            "success": False,
            "message": "Invalid request data"
        }, 400


    fcm_token = data.get("fcm_token")


    # VALIDATE TOKEN
    if not fcm_token:

        return {
            "success": False,
            "message": "FCM token is missing"
        }, 400


    # DATABASE CONNECTION
    conn = get_db_connection()
    cursor = conn.cursor()


    try:

        # CHECK IF TOKEN ALREADY EXISTS
        cursor.execute(
            """
            SELECT id
            FROM driver_fcm_tokens
            WHERE driver_id = %s
            AND fcm_token = %s
            """,
            (
                session["driver_id"],
                fcm_token
            )
        )

        existing_token = cursor.fetchone()


        # INSERT TOKEN IF NEW
        if not existing_token:

            cursor.execute(
                """
                INSERT INTO driver_fcm_tokens
                (
                    driver_id,
                    fcm_token
                )
                VALUES
                (
                    %s,
                    %s
                )
                """,
                (
                    session["driver_id"],
                    fcm_token
                )
            )

            conn.commit()


        return {
            "success": True,
            "message": "Driver FCM token saved successfully"
        }


    except Exception as e:

        conn.rollback()

        print(
            "Driver FCM Token Error:",
            str(e)
        )

        return {
            "success": False,
            "message": str(e)
        }, 500


    finally:

        cursor.close()
        conn.close()
# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    # ======================================
    # DRIVER LOGOUT
    # ======================================

    if "driver_id" in session:

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)

        # ----------------------------------
        # Get Driver Bus Number
        # ----------------------------------

        cursor.execute("""

            SELECT bus_number

            FROM drivers

            WHERE id=%s

        """, (

            session["driver_id"],

        ))

        driver = cursor.fetchone()

        if driver:

            # ----------------------------------
            # Get Bus ID
            # ----------------------------------

            cursor.execute("""

                SELECT bus_id

                FROM buses

                WHERE bus_number=%s

            """, (

                driver["bus_number"],

            ))

            bus = cursor.fetchone()

            if bus:

                # ----------------------------------
                # Set Driver Offline
                # ----------------------------------

                cursor.execute("""

                    UPDATE live_bus_location

                    SET

                        speed=0,

                        trip_status='Offline',

                        updated_at=NOW()

                    WHERE bus_id=%s

                """, (

                    bus["bus_id"],

                ))

                conn.commit()

        cursor.close()

        conn.close()

    # ======================================
    # CLEAR SESSION
    # ======================================

    session.clear()

    flash("Logged out successfully.", "success")

    return redirect("/login")


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)