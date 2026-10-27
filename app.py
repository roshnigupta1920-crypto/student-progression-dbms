import os
import re
import sqlite3
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, Response
from dotenv import load_dotenv, set_key
import mysql.connector

# Load environment variables
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "student-progression-secure-demo-key-2026")

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "student_progression.db")

def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.create_function("CONCAT", -1, lambda *args: "".join(str(a or '') for a in args))
    conn.create_function("IF", 3, lambda c, a, b: a if c else b)
    return conn

def get_db_config():
    """Retrieve database parameters with intelligent port detection."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3307")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "student_progression"),
    }

def get_db(use_db=True):
    """
    Connect to MySQL server.
    If database does not exist yet, connect without db and create it.
    """
    cfg = get_db_config()
    conn_params = {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "password": cfg["password"],
        "autocommit": True
    }
    if use_db and cfg["database"]:
        try:
            conn_params["database"] = cfg["database"]
            return mysql.connector.connect(**conn_params)
        except mysql.connector.Error as err:
            # If database unknown error (1049), create it
            if err.errno == 1049:
                conn_params.pop("database", None)
                temp_conn = mysql.connector.connect(**conn_params)
                cur = temp_conn.cursor()
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                cur.close()
                temp_conn.close()
                conn_params["database"] = cfg["database"]
                return mysql.connector.connect(**conn_params)
            raise
    else:
        return mysql.connector.connect(**conn_params)

def check_db_status():
    """Check MySQL connection status without throwing exceptions."""
    cfg = get_db_config()
    try:
        conn = get_db(use_db=True)
        cur = conn.cursor()
        cur.execute("SELECT VERSION()")
        ver = cur.fetchone()
        cur.close()
        conn.close()
        return {
            "connected": True,
            "engine": "MySQL 8.0",
            "host": cfg["host"],
            "port": cfg["port"],
            "user": cfg["user"],
            "name": cfg["database"],
            "version": ver[0] if ver else "8.0",
            "error": None
        }
    except Exception as e:
        return {
            "connected": False,
            "engine": "SQLite (Live Indian Data Mode)",
            "host": cfg["host"],
            "port": cfg["port"],
            "user": cfg["user"],
            "name": cfg["database"],
            "version": None,
            "error": str(e)
        }

@app.context_processor
def inject_global_data():
    """Inject database connection status and helpers to all templates."""
    status = check_db_status()
    return {
        "db_status": status,
        "now_year": date.today().year
    }

def rows(query, params=()):
    """Fetch all rows as dictionaries using parameterized queries."""
    status = check_db_status()
    if status["connected"]:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        result = cur.fetchall()
        cur.close()
        conn.close()
        return result
    else:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        q_sqlite = query.replace("%s", "?")
        cur.execute(q_sqlite, params)
        result = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return result

def row(query, params=()):
    """Fetch single row as dictionary."""
    res = rows(query, params)
    return res[0] if res else None

def trigger_sheets_auto_sync():
    """Asynchronously sync changes to Google Sheets Web App so it never blocks page loads."""
    import threading
    def _run():
        appscript_url = os.getenv("GOOGLE_APPSCRIPT_URL", "").strip()
        if not appscript_url:
            return
        try:
            import requests, time
            time.sleep(0.5)
            requests.get(appscript_url, timeout=20)
        except Exception as err:
            print(f"[Google Sheets Auto-Sync Warning]: {err}")
    threading.Thread(target=_run, daemon=True).start()

def execute(query, params=()):
    """Execute INSERT/UPDATE/DELETE query with parameterization."""
    status = check_db_status()
    if status["connected"]:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        last_id = cur.lastrowid
        cur.close()
        conn.close()
    else:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        q_sqlite = query.replace("%s", "?")
        cur.execute(q_sqlite, params)
        conn.commit()
        last_id = cur.lastrowid
        cur.close()
        conn.close()

    if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
        trigger_sheets_auto_sync()

    return last_id

def run_sql_script(file_path):
    """Execute multi-statement SQL files like schema.sql or seed.sql."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.path.dirname(__file__), file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"SQL file not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()
    
    conn = get_db(use_db=False)
    cur = conn.cursor()
    # Split statements
    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    for stmt in statements:
        if stmt.startswith("--") or stmt.startswith("/*"):
            # skip pure comments
            lines = [l for l in stmt.splitlines() if not l.strip().startswith("--") and not l.strip().startswith("/*")]
            cleaned_stmt = "\n".join(lines).strip()
            if not cleaned_stmt:
                continue
            cur.execute(cleaned_stmt)
        else:
            cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()

# -----------------------------------------------------------------------------
# PAGE 1: DASHBOARD
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    status = check_db_status()
    q = request.args.get("q", "").strip()

    try:
        if status["connected"]:
            # Check if MySQL tables exist
            table_check = rows("SHOW TABLES LIKE 'students'")
            if not table_check:
                schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")
                if os.path.exists(schema_file):
                    run_sql_script(schema_file)

        # Student records with search
        if q:
            search_param = f"%{q}%"
            students = rows("""
                SELECT s.*, 
                  (SELECT COUNT(*) FROM drop_years d WHERE d.student_id = s.student_id) +
                  (SELECT COUNT(*) FROM semesters sem WHERE sem.student_id = s.student_id AND sem.is_gap_after = 1) AS has_gap
                FROM students s
                WHERE CONCAT(s.first_name, ' ', s.last_name) LIKE %s
                   OR s.roll_no LIKE %s
                   OR s.email LIKE %s
                ORDER BY s.roll_no
            """, (search_param, search_param, search_param))
        else:
            students = rows("""
                SELECT s.*, 
                  (SELECT COUNT(*) FROM drop_years d WHERE d.student_id = s.student_id) +
                  (SELECT COUNT(*) FROM semesters sem WHERE sem.student_id = s.student_id AND sem.is_gap_after = 1) AS has_gap
                FROM students s
                ORDER BY s.roll_no
            """)

        # Aggregate Statistics
        total_students = len(students) if not q else (row("SELECT COUNT(*) as c FROM students") or {}).get("c", 0)
        active_students = (row("SELECT COUNT(*) as c FROM students WHERE current_status='Active'") or {}).get("c", 0)
        graduated_students = (row("SELECT COUNT(*) as c FROM students WHERE current_status='Graduated'") or {}).get("c", 0)
        dropped_students = (row("SELECT COUNT(*) as c FROM students WHERE current_status='Dropped'") or {}).get("c", 0)
        on_leave_students = (row("SELECT COUNT(*) as c FROM students WHERE current_status='On Leave'") or {}).get("c", 0)

        total_seminars = (row("SELECT COUNT(*) as c FROM seminars") or {}).get("c", 0)
        internal_seminars = (row("SELECT COUNT(*) as c FROM seminars WHERE seminar_type='Internal'") or {}).get("c", 0)
        external_seminars = (row("SELECT COUNT(*) as c FROM seminars WHERE seminar_type='External'") or {}).get("c", 0)
        total_activities = (row("SELECT COUNT(*) as c FROM activities") or {}).get("c", 0)

        # Semester-wise average SGPA trend for chart
        sem_averages = rows("""
            SELECT semester_no, ROUND(AVG(sgpa), 2) as avg_sgpa
            FROM semesters
            WHERE sgpa IS NOT NULL
            GROUP BY semester_no
            ORDER BY semester_no
        """)
        sem_avg_labels = [f"Sem {r['semester_no']}" for r in sem_averages]
        sem_avg_values = [float(r['avg_sgpa']) for r in sem_averages]

    except Exception as e:
        flash(f"Database query error: {e}", "error")
        students = []
        total_students = active_students = graduated_students = dropped_students = on_leave_students = 0
        total_seminars = internal_seminars = external_seminars = total_activities = 0
        sem_avg_labels = sem_avg_values = []

    return render_template(
        "index.html",
        active_page="dashboard",
        students=students,
        q=q,
        total_students=total_students,
        active_students=active_students,
        graduated_students=graduated_students,
        dropped_students=dropped_students,
        on_leave_students=on_leave_students,
        total_seminars=total_seminars,
        internal_seminars=internal_seminars,
        external_seminars=external_seminars,
        total_activities=total_activities,
        sem_avg_labels=sem_avg_labels,
        sem_avg_values=sem_avg_values
    )

# -----------------------------------------------------------------------------
# PAGE 2: STUDENTS MANAGEMENT (CRUD)
# -----------------------------------------------------------------------------
@app.route("/students")
def students_list():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    try:
        sql = "SELECT * FROM students WHERE 1=1"
        params = []
        if q:
            sql += " AND (CONCAT(first_name, ' ', last_name) LIKE %s OR roll_no LIKE %s OR email LIKE %s)"
            search_param = f"%{q}%"
            params.extend([search_param, search_param, search_param])
        if status_filter:
            sql += " AND current_status = %s"
            params.append(status_filter)
        sql += " ORDER BY roll_no"
        students = rows(sql, params)
    except Exception as e:
        flash(f"Could not load students: {e}", "error")
        students = []

    return render_template("students.html", active_page="students", students=students, q=q, status_filter=status_filter)

@app.route("/students/add", methods=["POST"])
def add_student():
    roll_no = request.form.get("roll_no", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip() or None
    phone = request.form.get("phone", "").strip() or None
    admission_year = request.form.get("admission_year", "").strip() or None
    current_status = request.form.get("current_status", "Active")

    if not roll_no or not first_name or not last_name:
        flash("Roll Number, First Name, and Last Name are required.", "error")
        return redirect(url_for("students_list"))

    try:
        execute("""
            INSERT INTO students (roll_no, first_name, last_name, email, phone, admission_year, current_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (roll_no, first_name, last_name, email, phone, admission_year, current_status))
        flash(f"Student '{first_name} {last_name}' ({roll_no}) successfully registered.", "success")
    except Exception as e:
        flash(f"Error adding student: {e}. Check for duplicate roll number or email.", "error")
    return redirect(url_for("students_list"))

@app.route("/students/edit/<int:sid>", methods=["POST"])
def edit_student(sid):
    roll_no = request.form.get("roll_no", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip() or None
    phone = request.form.get("phone", "").strip() or None
    admission_year = request.form.get("admission_year", "").strip() or None
    current_status = request.form.get("current_status", "Active")

    try:
        execute("""
            UPDATE students
            SET roll_no=%s, first_name=%s, last_name=%s, email=%s, phone=%s, admission_year=%s, current_status=%s
            WHERE student_id=%s
        """, (roll_no, first_name, last_name, email, phone, admission_year, current_status, sid))
        flash("Student details updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update student: {e}", "error")
    return redirect(url_for("students_list"))

@app.route("/students/delete/<int:sid>", methods=["POST"])
def delete_student(sid):
    try:
        execute("DELETE FROM students WHERE student_id=%s", (sid,))
        flash("Student and all cascading records (semesters, marks, seminars, activities) were permanently deleted.", "success")
    except Exception as e:
        flash(f"Error deleting student: {e}", "error")
    return redirect(url_for("students_list"))

# -----------------------------------------------------------------------------
# DEDICATED STUDENT PROFILE PAGE
# -----------------------------------------------------------------------------
@app.route("/students/<int:sid>")
def student_detail(sid):
    student = row("SELECT * FROM students WHERE student_id=%s", (sid,))
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students_list"))

    semesters = rows("SELECT * FROM semesters WHERE student_id=%s ORDER BY semester_no", (sid,))
    history = rows("SELECT * FROM academic_history WHERE student_id=%s ORDER BY completion_year", (sid,))
    seminars = rows("SELECT * FROM seminars WHERE student_id=%s ORDER BY event_date DESC", (sid,))
    activities = rows("SELECT * FROM activities WHERE student_id=%s ORDER BY activity_date DESC", (sid,))
    drops = rows("SELECT * FROM drop_years WHERE student_id=%s ORDER BY year_start", (sid,))
    
    marks = rows("""
        SELECT m.*, s.semester_no, sub.subject_code, sub.subject_name, sub.subject_type
        FROM semester_subject_marks m
        JOIN semesters s ON s.semester_id = m.semester_id
        JOIN subjects sub ON sub.subject_id = m.subject_id
        WHERE s.student_id = %s
        ORDER BY s.semester_no, sub.subject_type, sub.subject_code
    """, (sid,))

    all_subjects = rows("SELECT * FROM subjects ORDER BY subject_type, subject_code")

    latest_cgpa = None
    latest_sgpa = None
    if semesters:
        valid_cgpa = [s['cgpa'] for s in semesters if s['cgpa'] is not None]
        if valid_cgpa:
            latest_cgpa = f"{float(valid_cgpa[-1]):.2f}"
        valid_sgpa = [s['sgpa'] for s in semesters if s['sgpa'] is not None]
        if valid_sgpa:
            latest_sgpa = f"{float(valid_sgpa[-1]):.2f}"

    any_semester_gap = any(s.get("is_gap_after") for s in semesters)

    return render_template(
        "student_profile.html",
        active_page="students",
        student=student,
        semesters=semesters,
        history=history,
        seminars=seminars,
        activities=activities,
        drops=drops,
        marks=marks,
        all_subjects=all_subjects,
        latest_cgpa=latest_cgpa,
        latest_sgpa=latest_sgpa,
        any_semester_gap=any_semester_gap
    )

# -----------------------------------------------------------------------------
# PAGE 3: ACADEMIC HISTORY (CRUD)
# -----------------------------------------------------------------------------
@app.route("/academic-history")
def academic_history_list():
    q = request.args.get("q", "").strip()
    level_filter = request.args.get("level", "").strip()

    try:
        sql = """
            SELECT h.*, s.roll_no, CONCAT(s.first_name, ' ', s.last_name) as student_name
            FROM academic_history h
            JOIN students s ON s.student_id = h.student_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += " AND (CONCAT(s.first_name, ' ', s.last_name) LIKE %s OR s.roll_no LIKE %s OR h.institution LIKE %s)"
            sp = f"%{q}%"
            params.extend([sp, sp, sp])
        if level_filter:
            sql += " AND h.education_level = %s"
            params.append(level_filter)
        sql += " ORDER BY h.student_id, h.completion_year"
        records = rows(sql, params)
        all_students = rows("SELECT student_id, roll_no, first_name, last_name FROM students ORDER BY roll_no")
    except Exception as e:
        flash(f"Could not load academic history: {e}", "error")
        records, all_students = [], []

    return render_template(
        "academic_history.html",
        active_page="history",
        history_records=records,
        all_students=all_students,
        q=q,
        level_filter=level_filter
    )

@app.route("/academic-history/add", methods=["POST"])
def add_academic_history():
    sid = request.form.get("student_id")
    education_level = request.form.get("education_level")
    institution = request.form.get("institution", "").strip() or None
    completion_year = request.form.get("completion_year", "").strip() or None
    marks_obtained = request.form.get("marks_obtained", "").strip() or None
    marks_total = request.form.get("marks_total", "").strip() or None
    percentage = request.form.get("percentage", "").strip()

    if not sid or not education_level or not percentage:
        flash("Student, Education Level, and Percentage are required.", "error")
        return redirect(request.referrer or url_for("academic_history_list"))

    try:
        execute("""
            INSERT INTO academic_history (student_id, education_level, institution, completion_year, marks_obtained, marks_total, percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (sid, education_level, institution, completion_year, marks_obtained, marks_total, percentage))
        flash("Academic qualification record logged successfully.", "success")
    except Exception as e:
        flash(f"Error logging academic history: {e}. Check percentage range (0-100).", "error")
    return redirect(request.referrer or url_for("academic_history_list"))

@app.route("/academic-history/edit/<int:hid>", methods=["POST"])
def edit_academic_history(hid):
    education_level = request.form.get("education_level")
    institution = request.form.get("institution", "").strip() or None
    completion_year = request.form.get("completion_year", "").strip() or None
    marks_obtained = request.form.get("marks_obtained", "").strip() or None
    marks_total = request.form.get("marks_total", "").strip() or None
    percentage = request.form.get("percentage", "").strip()

    try:
        execute("""
            UPDATE academic_history
            SET education_level=%s, institution=%s, completion_year=%s, marks_obtained=%s, marks_total=%s, percentage=%s
            WHERE history_id=%s
        """, (education_level, institution, completion_year, marks_obtained, marks_total, percentage, hid))
        flash("Academic history updated.", "success")
    except Exception as e:
        flash(f"Error updating academic history: {e}", "error")
    return redirect(request.referrer or url_for("academic_history_list"))

@app.route("/academic-history/delete/<int:hid>", methods=["POST"])
def delete_academic_history(hid):
    try:
        execute("DELETE FROM academic_history WHERE history_id=%s", (hid,))
        flash("Academic history record removed.", "success")
    except Exception as e:
        flash(f"Error deleting record: {e}", "error")
    return redirect(request.referrer or url_for("academic_history_list"))

# -----------------------------------------------------------------------------
# PAGE 4: SEMESTER RESULTS (CRUD)
# -----------------------------------------------------------------------------
@app.route("/semesters")
def semesters_list():
    q = request.args.get("q", "").strip()
    sem_filter = request.args.get("sem_no", "").strip()

    try:
        sql = """
            SELECT sem.*, s.roll_no, CONCAT(s.first_name, ' ', s.last_name) as student_name
            FROM semesters sem
            JOIN students s ON s.student_id = sem.student_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += " AND (CONCAT(s.first_name, ' ', s.last_name) LIKE %s OR s.roll_no LIKE %s)"
            sp = f"%{q}%"
            params.extend([sp, sp])
        if sem_filter:
            sql += " AND sem.semester_no = %s"
            params.append(int(sem_filter))
        sql += " ORDER BY s.roll_no, sem.semester_no"
        records = rows(sql, params)
        all_students = rows("SELECT student_id, roll_no, first_name, last_name FROM students ORDER BY roll_no")
    except Exception as e:
        flash(f"Could not load semesters: {e}", "error")
        records, all_students = [], []

    return render_template(
        "semesters.html",
        active_page="semesters",
        semester_records=records,
        all_students=all_students,
        q=q,
        sem_filter=sem_filter
    )

@app.route("/semesters/add/<int:sid>", methods=["POST"])
def add_semester(sid):
    """Add semester directly for a student from profile page."""
    semester_no = request.form.get("semester_no")
    academic_year = request.form.get("academic_year", "").strip() or None
    sgpa = request.form.get("sgpa", "").strip() or None
    cgpa = request.form.get("cgpa", "").strip() or None
    is_gap_after = 1 if request.form.get("is_gap_after") else 0
    gap_years = int(request.form.get("gap_years", 0) or 0)
    remarks = request.form.get("remarks", "").strip() or None

    try:
        execute("""
            INSERT INTO semesters (student_id, semester_no, academic_year, sgpa, cgpa, is_gap_after, gap_years, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (sid, int(semester_no), academic_year, sgpa, cgpa, is_gap_after, gap_years, remarks))
        flash(f"Semester {semester_no} result recorded successfully.", "success")
    except Exception as e:
        flash(f"Could not save semester result: {e}. Check duplicate semester number or SGPA/CGPA range (0-10).", "error")
    return redirect(url_for("student_detail", sid=sid))

@app.route("/semesters/add-direct", methods=["POST"])
def add_semester_direct():
    """Add semester from semesters management page."""
    sid = request.form.get("student_id")
    semester_no = request.form.get("semester_no")
    academic_year = request.form.get("academic_year", "").strip() or None
    sgpa = request.form.get("sgpa", "").strip() or None
    cgpa = request.form.get("cgpa", "").strip() or None
    is_gap_after = 1 if request.form.get("is_gap_after") else 0
    gap_years = int(request.form.get("gap_years", 0) or 0)
    remarks = request.form.get("remarks", "").strip() or None

    if not sid or not semester_no:
        flash("Student and Semester Number are required.", "error")
        return redirect(url_for("semesters_list"))

    try:
        execute("""
            INSERT INTO semesters (student_id, semester_no, academic_year, sgpa, cgpa, is_gap_after, gap_years, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (sid, int(semester_no), academic_year, sgpa, cgpa, is_gap_after, gap_years, remarks))
        flash(f"Semester {semester_no} result successfully saved.", "success")
    except Exception as e:
        flash(f"Error saving semester: {e}. Duplicate semester for this student or invalid SGPA/CGPA range.", "error")
    return redirect(url_for("semesters_list"))

@app.route("/semesters/edit/<int:smid>", methods=["POST"])
def edit_semester(smid):
    semester_no = request.form.get("semester_no")
    academic_year = request.form.get("academic_year", "").strip() or None
    sgpa = request.form.get("sgpa", "").strip() or None
    cgpa = request.form.get("cgpa", "").strip() or None
    is_gap_after = 1 if request.form.get("is_gap_after") else 0
    gap_years = int(request.form.get("gap_years", 0) or 0)
    remarks = request.form.get("remarks", "").strip() or None

    try:
        execute("""
            UPDATE semesters
            SET semester_no=%s, academic_year=%s, sgpa=%s, cgpa=%s, is_gap_after=%s, gap_years=%s, remarks=%s
            WHERE semester_id=%s
        """, (int(semester_no), academic_year, sgpa, cgpa, is_gap_after, gap_years, remarks, smid))
        flash("Semester details updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating semester: {e}", "error")
    return redirect(request.referrer or url_for("semesters_list"))

@app.route("/semesters/delete/<int:smid>", methods=["POST"])
def delete_semester(smid):
    try:
        execute("DELETE FROM semesters WHERE semester_id=%s", (smid,))
        flash("Semester record and all associated subject marks deleted.", "success")
    except Exception as e:
        flash(f"Error deleting semester: {e}", "error")
    return redirect(request.referrer or url_for("semesters_list"))

# -----------------------------------------------------------------------------
# PAGE 5: SUBJECT AND LAB MARKS (CRUD) & SUBJECTS (CRUD)
# -----------------------------------------------------------------------------
@app.route("/marks")
def marks_list():
    q = request.args.get("q", "").strip()
    type_filter = request.args.get("type", "").strip()

    try:
        sql = """
            SELECT m.*, s.semester_no, st.roll_no, st.student_id, CONCAT(st.first_name, ' ', st.last_name) as student_name,
                   sub.subject_code, sub.subject_name, sub.subject_type, sub.credits
            FROM semester_subject_marks m
            JOIN semesters s ON s.semester_id = m.semester_id
            JOIN students st ON st.student_id = s.student_id
            JOIN subjects sub ON sub.subject_id = m.subject_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += " AND (CONCAT(st.first_name, ' ', st.last_name) LIKE %s OR st.roll_no LIKE %s OR sub.subject_name LIKE %s OR sub.subject_code LIKE %s)"
            sp = f"%{q}%"
            params.extend([sp, sp, sp, sp])
        if type_filter:
            sql += " AND sub.subject_type = %s"
            params.append(type_filter)
        sql += " ORDER BY st.roll_no, s.semester_no, sub.subject_code"
        marks_records = rows(sql, params)

        subjects = rows("SELECT * FROM subjects ORDER BY subject_type, subject_code")
        all_semesters = rows("""
            SELECT s.semester_id, s.semester_no, s.academic_year, st.roll_no, CONCAT(st.first_name, ' ', st.last_name) as student_name
            FROM semesters s
            JOIN students st ON st.student_id = s.student_id
            ORDER BY st.roll_no, s.semester_no
        """)
    except Exception as e:
        flash(f"Could not load marks: {e}", "error")
        marks_records, subjects, all_semesters = [], [], []

    return render_template(
        "marks.html",
        active_page="marks",
        marks_records=marks_records,
        subjects=subjects,
        all_semesters=all_semesters,
        q=q,
        type_filter=type_filter
    )

@app.route("/marks/add-direct", methods=["POST"])
def add_marks_direct():
    semester_id = request.form.get("semester_id")
    subject_id = request.form.get("subject_id")
    internal_marks = request.form.get("internal_marks", "").strip() or None
    external_marks = request.form.get("external_marks", "").strip() or None
    practical_marks = request.form.get("practical_marks", "").strip() or None
    total_marks = request.form.get("total_marks", "").strip() or None
    max_marks = float(request.form.get("max_marks", 100) or 100)
    grade = request.form.get("grade", "").strip() or None

    if not semester_id or not subject_id:
        flash("Semester and Subject selection are required.", "error")
        return redirect(url_for("marks_list"))

    try:
        execute("""
            INSERT INTO semester_subject_marks (semester_id, subject_id, internal_marks, external_marks, practical_marks, total_marks, max_marks, grade)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (semester_id, subject_id, internal_marks, external_marks, practical_marks, total_marks, max_marks, grade))
        flash("Examination mark entry saved.", "success")
    except Exception as e:
        flash(f"Could not save mark entry: {e}. Check for duplicate course in the same semester.", "error")
    return redirect(url_for("marks_list"))

@app.route("/marks/add-for-student/<int:sid>", methods=["POST"])
def add_marks_for_student(sid):
    semester_id = request.form.get("semester_id")
    subject_id = request.form.get("subject_id")
    internal_marks = request.form.get("internal_marks", "").strip() or None
    external_marks = request.form.get("external_marks", "").strip() or None
    practical_marks = request.form.get("practical_marks", "").strip() or None
    total_marks = request.form.get("total_marks", "").strip() or None
    max_marks = float(request.form.get("max_marks", 100) or 100)
    grade = request.form.get("grade", "").strip() or None

    try:
        execute("""
            INSERT INTO semester_subject_marks (semester_id, subject_id, internal_marks, external_marks, practical_marks, total_marks, max_marks, grade)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (semester_id, subject_id, internal_marks, external_marks, practical_marks, total_marks, max_marks, grade))
        flash("Course mark recorded for student.", "success")
    except Exception as e:
        flash(f"Error recording course mark: {e}", "error")
    return redirect(url_for("student_detail", sid=sid))

@app.route("/marks/edit/<int:mid>", methods=["POST"])
def edit_marks(mid):
    internal_marks = request.form.get("internal_marks", "").strip() or None
    external_marks = request.form.get("external_marks", "").strip() or None
    practical_marks = request.form.get("practical_marks", "").strip() or None
    total_marks = request.form.get("total_marks", "").strip() or None
    max_marks = float(request.form.get("max_marks", 100) or 100)
    grade = request.form.get("grade", "").strip() or None

    try:
        execute("""
            UPDATE semester_subject_marks
            SET internal_marks=%s, external_marks=%s, practical_marks=%s, total_marks=%s, max_marks=%s, grade=%s
            WHERE mark_id=%s
        """, (internal_marks, external_marks, practical_marks, total_marks, max_marks, grade, mid))
        flash("Mark record updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating mark record: {e}", "error")
    return redirect(request.referrer or url_for("marks_list"))

@app.route("/marks/delete/<int:mid>", methods=["POST"])
def delete_marks(mid):
    try:
        execute("DELETE FROM semester_subject_marks WHERE mark_id=%s", (mid,))
        flash("Mark record deleted.", "success")
    except Exception as e:
        flash(f"Error deleting mark record: {e}", "error")
    return redirect(request.referrer or url_for("marks_list"))

# Subjects CRUD
@app.route("/subjects/add", methods=["POST"])
def add_subject():
    code = request.form.get("subject_code", "").strip()
    name = request.form.get("subject_name", "").strip()
    stype = request.form.get("subject_type", "Theory")
    credits = float(request.form.get("credits", 3.0) or 0)

    if not code or not name:
        flash("Subject Code and Subject Name are required.", "error")
        return redirect(url_for("marks_list"))

    try:
        execute("""
            INSERT INTO subjects (subject_code, subject_name, subject_type, credits)
            VALUES (%s, %s, %s, %s)
        """, (code, name, stype, credits))
        flash(f"Subject '{name}' ({code}) added to curriculum.", "success")
    except Exception as e:
        flash(f"Error adding subject: {e}. Check for duplicate subject code.", "error")
    return redirect(url_for("marks_list"))

@app.route("/subjects/edit/<int:suid>", methods=["POST"])
def edit_subject(suid):
    code = request.form.get("subject_code", "").strip()
    name = request.form.get("subject_name", "").strip()
    stype = request.form.get("subject_type", "Theory")
    credits = float(request.form.get("credits", 3.0) or 0)

    try:
        execute("""
            UPDATE subjects
            SET subject_code=%s, subject_name=%s, subject_type=%s, credits=%s
            WHERE subject_id=%s
        """, (code, name, stype, credits, suid))
        flash("Subject updated.", "success")
    except Exception as e:
        flash(f"Error updating subject: {e}", "error")
    return redirect(url_for("marks_list"))

@app.route("/subjects/delete/<int:suid>", methods=["POST"])
def delete_subject(suid):
    try:
        execute("DELETE FROM subjects WHERE subject_id=%s", (suid,))
        flash("Subject and associated marks entries removed.", "success")
    except Exception as e:
        flash(f"Error deleting subject: {e}", "error")
    return redirect(url_for("marks_list"))

# -----------------------------------------------------------------------------
# PAGE 6: SEMINARS (CRUD)
# -----------------------------------------------------------------------------
@app.route("/seminars")
def seminars_list():
    q = request.args.get("q", "").strip()
    type_filter = request.args.get("type", "").strip()

    try:
        sql = """
            SELECT sem.*, s.roll_no, CONCAT(s.first_name, ' ', s.last_name) as student_name
            FROM seminars sem
            JOIN students s ON s.student_id = sem.student_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += " AND (CONCAT(s.first_name, ' ', s.last_name) LIKE %s OR s.roll_no LIKE %s OR sem.title LIKE %s OR sem.organizer LIKE %s)"
            sp = f"%{q}%"
            params.extend([sp, sp, sp, sp])
        if type_filter:
            sql += " AND sem.seminar_type = %s"
            params.append(type_filter)
        sql += " ORDER BY sem.event_date DESC, sem.seminar_id DESC"
        seminars = rows(sql, params)
        all_students = rows("SELECT student_id, roll_no, first_name, last_name FROM students ORDER BY roll_no")
    except Exception as e:
        flash(f"Could not load seminars: {e}", "error")
        seminars, all_students = [], []

    return render_template(
        "seminars.html",
        active_page="seminars",
        seminars=seminars,
        all_students=all_students,
        q=q,
        type_filter=type_filter
    )

@app.route("/seminars/add", methods=["POST"])
def add_seminar():
    sid = request.form.get("student_id")
    title = request.form.get("title", "").strip()
    stype = request.form.get("seminar_type", "Internal")
    organizer = request.form.get("organizer", "").strip() or None
    event_date = request.form.get("event_date", "").strip() or None
    cert = request.form.get("certificate_url", "").strip() or None

    if not sid or not title:
        flash("Student and Seminar Title are required.", "error")
        return redirect(request.referrer or url_for("seminars_list"))

    try:
        execute("""
            INSERT INTO seminars (student_id, title, seminar_type, organizer, event_date, certificate_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (sid, title, stype, organizer, event_date, cert))
        flash(f"Seminar '{title}' recorded successfully.", "success")
    except Exception as e:
        flash(f"Error adding seminar: {e}", "error")
    return redirect(request.referrer or url_for("seminars_list"))

@app.route("/seminars/edit/<int:smid>", methods=["POST"])
def edit_seminar(smid):
    title = request.form.get("title", "").strip()
    stype = request.form.get("seminar_type", "Internal")
    organizer = request.form.get("organizer", "").strip() or None
    event_date = request.form.get("event_date", "").strip() or None
    cert = request.form.get("certificate_url", "").strip() or None

    try:
        execute("""
            UPDATE seminars
            SET title=%s, seminar_type=%s, organizer=%s, event_date=%s, certificate_url=%s
            WHERE seminar_id=%s
        """, (title, stype, organizer, event_date, cert, smid))
        flash("Seminar details updated.", "success")
    except Exception as e:
        flash(f"Error updating seminar: {e}", "error")
    return redirect(request.referrer or url_for("seminars_list"))

@app.route("/seminars/delete/<int:smid>", methods=["POST"])
def delete_seminar(smid):
    try:
        execute("DELETE FROM seminars WHERE seminar_id=%s", (smid,))
        flash("Seminar record removed.", "success")
    except Exception as e:
        flash(f"Error deleting seminar: {e}", "error")
    return redirect(request.referrer or url_for("seminars_list"))

# -----------------------------------------------------------------------------
# PAGE 7: ACTIVITIES (CRUD)
# -----------------------------------------------------------------------------
@app.route("/activities")
def activities_list():
    q = request.args.get("q", "").strip()
    type_filter = request.args.get("type", "").strip()

    try:
        sql = """
            SELECT a.*, s.roll_no, CONCAT(s.first_name, ' ', s.last_name) as student_name
            FROM activities a
            JOIN students s ON s.student_id = a.student_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += " AND (CONCAT(s.first_name, ' ', s.last_name) LIKE %s OR s.roll_no LIKE %s OR a.title LIKE %s OR a.role LIKE %s OR a.organizer LIKE %s)"
            sp = f"%{q}%"
            params.extend([sp, sp, sp, sp, sp])
        if type_filter:
            sql += " AND a.activity_type = %s"
            params.append(type_filter)
        sql += " ORDER BY a.activity_date DESC, a.activity_id DESC"
        activities = rows(sql, params)
        all_students = rows("SELECT student_id, roll_no, first_name, last_name FROM students ORDER BY roll_no")
    except Exception as e:
        flash(f"Could not load activities: {e}", "error")
        activities, all_students = [], []

    return render_template(
        "activities.html",
        active_page="activities",
        activities=activities,
        all_students=all_students,
        q=q,
        type_filter=type_filter
    )

@app.route("/activities/add", methods=["POST"])
def add_activity():
    sid = request.form.get("student_id")
    title = request.form.get("title", "").strip()
    atype = request.form.get("activity_type", "Technical")
    role_name = request.form.get("role", "").strip() or None
    organizer = request.form.get("organizer", "").strip() or None
    adate = request.form.get("activity_date", "").strip() or None
    cert = request.form.get("certificate_url", "").strip() or None

    if not sid or not title:
        flash("Student and Activity Title are required.", "error")
        return redirect(request.referrer or url_for("activities_list"))

    try:
        execute("""
            INSERT INTO activities (student_id, title, activity_type, role, organizer, activity_date, certificate_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (sid, title, atype, role_name, organizer, adate, cert))
        flash(f"Activity '{title}' added to portfolio.", "success")
    except Exception as e:
        flash(f"Error adding activity: {e}", "error")
    return redirect(request.referrer or url_for("activities_list"))

@app.route("/activities/edit/<int:aid>", methods=["POST"])
def edit_activity(aid):
    title = request.form.get("title", "").strip()
    atype = request.form.get("activity_type", "Technical")
    role_name = request.form.get("role", "").strip() or None
    organizer = request.form.get("organizer", "").strip() or None
    adate = request.form.get("activity_date", "").strip() or None
    cert = request.form.get("certificate_url", "").strip() or None

    try:
        execute("""
            UPDATE activities
            SET title=%s, activity_type=%s, role=%s, organizer=%s, activity_date=%s, certificate_url=%s
            WHERE activity_id=%s
        """, (title, atype, role_name, organizer, adate, cert, aid))
        flash("Activity updated.", "success")
    except Exception as e:
        flash(f"Error updating activity: {e}", "error")
    return redirect(request.referrer or url_for("activities_list"))

@app.route("/activities/delete/<int:aid>", methods=["POST"])
def delete_activity(aid):
    try:
        execute("DELETE FROM activities WHERE activity_id=%s", (aid,))
        flash("Activity removed.", "success")
    except Exception as e:
        flash(f"Error deleting activity: {e}", "error")
    return redirect(request.referrer or url_for("activities_list"))

# -----------------------------------------------------------------------------
# PAGE 8: DROP / GAP YEARS (CRUD)
# -----------------------------------------------------------------------------
@app.route("/drop-years")
def drop_years_list():
    q = request.args.get("q", "").strip()

    try:
        sql = """
            SELECT d.*, s.roll_no, CONCAT(s.first_name, ' ', s.last_name) as student_name
            FROM drop_years d
            JOIN students s ON s.student_id = d.student_id
            WHERE 1=1
        """
        params = []
        if q:
            sql += " AND (CONCAT(s.first_name, ' ', s.last_name) LIKE %s OR s.roll_no LIKE %s OR d.reason LIKE %s)"
            sp = f"%{q}%"
            params.extend([sp, sp, sp])
        sql += " ORDER BY d.year_start DESC"
        records = rows(sql, params)
        all_students = rows("SELECT student_id, roll_no, first_name, last_name FROM students ORDER BY roll_no")
    except Exception as e:
        flash(f"Could not load drop years: {e}", "error")
        records, all_students = [], []

    return render_template(
        "drop_years.html",
        active_page="drops",
        drop_records=records,
        all_students=all_students,
        q=q
    )

@app.route("/drop-years/add", methods=["POST"])
def add_drop_year():
    sid = request.form.get("student_id")
    ystart = request.form.get("year_start", "").strip()
    yend = request.form.get("year_end", "").strip()
    reason = request.form.get("reason", "").strip() or None

    if not sid or not ystart or not yend:
        flash("Student, Start Year, and End Year are required.", "error")
        return redirect(request.referrer or url_for("drop_years_list"))

    try:
        ys = int(ystart)
        ye = int(yend)
        if ye < ys:
            flash("End Year cannot precede Start Year (violates chk_drop_years constraint).", "error")
            return redirect(request.referrer or url_for("drop_years_list"))

        execute("""
            INSERT INTO drop_years (student_id, year_start, year_end, reason)
            VALUES (%s, %s, %s, %s)
        """, (sid, ys, ye, reason))
        flash(f"Academic gap interval ({ys} - {ye}) recorded.", "success")
    except Exception as e:
        flash(f"Error logging drop year: {e}", "error")
    return redirect(request.referrer or url_for("drop_years_list"))

@app.route("/drop-years/edit/<int:did>", methods=["POST"])
def edit_drop_year(did):
    ystart = request.form.get("year_start", "").strip()
    yend = request.form.get("year_end", "").strip()
    reason = request.form.get("reason", "").strip() or None

    try:
        ys = int(ystart)
        ye = int(yend)
        if ye < ys:
            flash("End Year cannot be earlier than Start Year.", "error")
            return redirect(request.referrer or url_for("drop_years_list"))

        execute("""
            UPDATE drop_years
            SET year_start=%s, year_end=%s, reason=%s
            WHERE drop_id=%s
        """, (ys, ye, reason, did))
        flash("Gap interval updated.", "success")
    except Exception as e:
        flash(f"Error updating drop year: {e}", "error")
    return redirect(request.referrer or url_for("drop_years_list"))

@app.route("/drop-years/delete/<int:did>", methods=["POST"])
def delete_drop_year(did):
    try:
        execute("DELETE FROM drop_years WHERE drop_id=%s", (did,))
        flash("Drop year record removed.", "success")
    except Exception as e:
        flash(f"Error deleting drop year: {e}", "error")
    return redirect(request.referrer or url_for("drop_years_list"))

# -----------------------------------------------------------------------------
# PAGE 9: GOOGLE SHEETS SYNCHRONIZATION
# -----------------------------------------------------------------------------
@app.route("/sync-sheets")
def sync_sheets_page():
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    creds_file = os.getenv("GOOGLE_CREDENTIALS", "credentials/service_account.json").strip()
    creds_path = creds_file if os.path.isabs(creds_file) else os.path.join(os.path.dirname(__file__), creds_file)
    creds_exists = os.path.exists(creds_path)
    appscript_url = os.getenv("GOOGLE_APPSCRIPT_URL", "").strip()
    has_sheet_config = bool(appscript_url or (sheet_id and creds_exists))

    # Get row counts for all 8 tables
    table_counts = {
        "students": 0, "history": 0, "semesters": 0, "subjects": 0,
        "marks": 0, "seminars": 0, "activities": 0, "drops": 0
    }
    try:
        table_counts["students"] = (row("SELECT COUNT(*) as c FROM students") or {}).get("c", 0)
        table_counts["history"] = (row("SELECT COUNT(*) as c FROM academic_history") or {}).get("c", 0)
        table_counts["semesters"] = (row("SELECT COUNT(*) as c FROM semesters") or {}).get("c", 0)
        table_counts["subjects"] = (row("SELECT COUNT(*) as c FROM subjects") or {}).get("c", 0)
        table_counts["marks"] = (row("SELECT COUNT(*) as c FROM semester_subject_marks") or {}).get("c", 0)
        table_counts["seminars"] = (row("SELECT COUNT(*) as c FROM seminars") or {}).get("c", 0)
        table_counts["activities"] = (row("SELECT COUNT(*) as c FROM activities") or {}).get("c", 0)
        table_counts["drops"] = (row("SELECT COUNT(*) as c FROM drop_years") or {}).get("c", 0)
    except Exception:
        pass

    return render_template(
        "sync_sheets.html",
        active_page="sync",
        sheet_id=sheet_id,
        creds_file=creds_file,
        creds_exists=creds_exists,
        has_sheet_config=has_sheet_config,
        table_counts=table_counts
    )

@app.route("/sync-sheets/run", methods=["POST"])
def run_sync():
    """Perform actual one-way export to Google Sheets via Apps Script Webhook or Service Account."""
    appscript_url = os.getenv("GOOGLE_APPSCRIPT_URL", "").strip()
    if appscript_url:
        try:
            import requests
            api_url = url_for("api_export_all", _external=True)
            # Fetch directly from local function to avoid networking loop
            exports = {
                'Students': (
                    'SELECT student_id, roll_no, first_name, last_name, email, phone, admission_year, current_status FROM students ORDER BY roll_no',
                    ['Student ID', 'Roll No', 'First Name', 'Last Name', 'Email', 'Phone', 'Admission Year', 'Status']
                ),
                'Academic_History': (
                    '''SELECT h.history_id, s.roll_no, h.education_level, h.institution, h.completion_year, h.marks_obtained, h.marks_total, h.percentage
                       FROM academic_history h JOIN students s ON s.student_id=h.student_id ORDER BY s.roll_no, h.completion_year''',
                    ['History ID', 'Roll No', 'Education Level', 'Institution', 'Completion Year', 'Marks Obtained', 'Total Marks', 'Percentage (%)']
                ),
                'Semesters': (
                    '''SELECT sem.semester_id, s.roll_no, sem.semester_no, sem.academic_year, sem.sgpa, sem.cgpa, 
                              IF(sem.is_gap_after=1, 'YES', 'NO') as gap_flag, sem.gap_years, sem.remarks
                       FROM semesters sem JOIN students s ON s.student_id=sem.student_id ORDER BY s.roll_no, sem.semester_no''',
                    ['Semester ID', 'Roll No', 'Semester No', 'Academic Year', 'SGPA', 'CGPA', 'Gap After?', 'Gap Years', 'Remarks']
                ),
                'Subjects': (
                    'SELECT subject_id, subject_code, subject_name, subject_type, credits FROM subjects ORDER BY subject_type, subject_code',
                    ['Subject ID', 'Subject Code', 'Subject Name', 'Course Type', 'Credits']
                ),
                'Semester_Marks': (
                    '''SELECT m.mark_id, st.roll_no, s.semester_no, sub.subject_code, sub.subject_name, sub.subject_type,
                              m.internal_marks, m.external_marks, m.practical_marks, m.total_marks, m.max_marks, m.grade
                           FROM semester_subject_marks m
                           JOIN semesters s ON s.semester_id=m.semester_id
                           JOIN students st ON st.student_id=s.student_id
                           JOIN subjects sub ON sub.subject_id=m.subject_id
                           ORDER BY st.roll_no, s.semester_no, sub.subject_code''',
                    ['Mark ID', 'Roll No', 'Semester', 'Subject Code', 'Subject Name', 'Type', 'Internal', 'External', 'Practical', 'Total', 'Max', 'Grade']
                ),
                'Seminars': (
                    '''SELECT sem.seminar_id, s.roll_no, sem.title, sem.seminar_type, sem.organizer, sem.event_date, sem.certificate_url
                       FROM seminars sem JOIN students s ON s.student_id=sem.student_id ORDER BY sem.event_date DESC''',
                    ['Seminar ID', 'Roll No', 'Title', 'Seminar Type', 'Organizer', 'Event Date', 'Certificate URL']
                ),
                'Activities': (
                    '''SELECT a.activity_id, s.roll_no, a.title, a.activity_type, a.role, a.organizer, a.activity_date, a.certificate_url
                       FROM activities a JOIN students s ON s.student_id=a.student_id ORDER BY a.activity_date DESC''',
                    ['Activity ID', 'Roll No', 'Title', 'Category', 'Role / Award', 'Organizer', 'Date', 'Certificate URL']
                ),
                'Drop_Years': (
                    '''SELECT d.drop_id, s.roll_no, d.year_start, d.year_end, (d.year_end - d.year_start) as duration, d.reason
                       FROM drop_years d JOIN students s ON s.student_id=d.student_id ORDER BY d.year_start DESC''',
                    ['Drop ID', 'Roll No', 'Start Year', 'End Year', 'Duration (Years)', 'Reason / Justification']
                )
            }
            payload = {}
            for tname, (q, headers) in exports.items():
                data = rows(q)
                payload[tname] = {
                    "headers": headers,
                    "rows": [[str(v) if v is not None else '' for v in item.values()] for item in data]
                }
            resp = requests.post(appscript_url, json=payload, timeout=25)
            flash(f"Sync request delivered to Google Apps Script Web App! Status: {resp.status_code}", "success")
            return redirect(url_for("sync_sheets_page"))
        except Exception as e:
            flash(f"Apps Script Webhook Sync: {e}", "warning")
            return redirect(url_for("sync_sheets_page"))
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    creds_file = os.getenv("GOOGLE_CREDENTIALS", "credentials/service_account.json").strip()
    creds_path = creds_file if os.path.isabs(creds_file) else os.path.join(os.path.dirname(__file__), creds_file)

    if not sheet_id:
        flash("Sync failed: GOOGLE_SHEET_ID is not configured in .env.", "error")
        return redirect(url_for("sync_sheets_page"))

    if not os.path.exists(creds_path):
        flash(f"Sync failed: Credentials key file was not found at '{creds_file}'.", "error")
        return redirect(url_for("sync_sheets_page"))

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheet_id)

        # Definitions of 8 tables to export
        exports = {
            "Students": (
                "SELECT student_id, roll_no, first_name, last_name, email, phone, admission_year, current_status FROM students ORDER BY roll_no",
                ["Student ID", "Roll No", "First Name", "Last Name", "Email", "Phone", "Admission Year", "Status"]
            ),
            "Academic_History": (
                """SELECT h.history_id, s.roll_no, h.education_level, h.institution, h.completion_year, h.marks_obtained, h.marks_total, h.percentage
                   FROM academic_history h JOIN students s ON s.student_id=h.student_id ORDER BY s.roll_no, h.completion_year""",
                ["History ID", "Roll No", "Education Level", "Institution", "Completion Year", "Marks Obtained", "Total Marks", "Percentage (%)"]
            ),
            "Semesters": (
                """SELECT sem.semester_id, s.roll_no, sem.semester_no, sem.academic_year, sem.sgpa, sem.cgpa, 
                          IF(sem.is_gap_after=1, 'YES', 'NO') as gap_flag, sem.gap_years, sem.remarks
                   FROM semesters sem JOIN students s ON s.student_id=sem.student_id ORDER BY s.roll_no, sem.semester_no""",
                ["Semester ID", "Roll No", "Semester No", "Academic Year", "SGPA", "CGPA", "Gap After?", "Gap Years", "Remarks"]
            ),
            "Subjects": (
                "SELECT subject_id, subject_code, subject_name, subject_type, credits FROM subjects ORDER BY subject_type, subject_code",
                ["Subject ID", "Subject Code", "Subject Name", "Course Type", "Credits"]
            ),
            "Semester_Marks": (
                """SELECT m.mark_id, st.roll_no, s.semester_no, sub.subject_code, sub.subject_name, sub.subject_type,
                          m.internal_marks, m.external_marks, m.practical_marks, m.total_marks, m.max_marks, m.grade
                   FROM semester_subject_marks m
                   JOIN semesters s ON s.semester_id=m.semester_id
                   JOIN students st ON st.student_id=s.student_id
                   JOIN subjects sub ON sub.subject_id=m.subject_id
                   ORDER BY st.roll_no, s.semester_no, sub.subject_code""",
                ["Mark ID", "Roll No", "Semester", "Subject Code", "Subject Name", "Type", "Internal", "External", "Practical", "Total", "Max", "Grade"]
            ),
            "Seminars": (
                """SELECT sem.seminar_id, s.roll_no, sem.title, sem.seminar_type, sem.organizer, sem.event_date, sem.certificate_url
                   FROM seminars sem JOIN students s ON s.student_id=sem.student_id ORDER BY sem.event_date DESC""",
                ["Seminar ID", "Roll No", "Title", "Seminar Type", "Organizer", "Event Date", "Certificate URL"]
            ),
            "Activities": (
                """SELECT a.activity_id, s.roll_no, a.title, a.activity_type, a.role, a.organizer, a.activity_date, a.certificate_url
                   FROM activities a JOIN students s ON s.student_id=a.student_id ORDER BY a.activity_date DESC""",
                ["Activity ID", "Roll No", "Title", "Category", "Role / Award", "Organizer", "Date", "Certificate URL"]
            ),
            "Drop_Years": (
                """SELECT d.drop_id, s.roll_no, d.year_start, d.year_end, (d.year_end - d.year_start) as duration, d.reason
                   FROM drop_years d JOIN students s ON s.student_id=d.student_id ORDER BY d.year_start DESC""",
                ["Drop ID", "Roll No", "Start Year", "End Year", "Duration (Years)", "Reason / Justification"]
            )
        }

        existing_titles = [ws.title for ws in spreadsheet.worksheets()]
        total_rows_synced = 0

        for title, (query, headers) in exports.items():
            data = rows(query)
            total_rows_synced += len(data)

            if title in existing_titles:
                ws = spreadsheet.worksheet(title)
            else:
                ws = spreadsheet.add_worksheet(title=title, rows=max(len(data) + 10, 100), cols=max(len(headers) + 2, 12))

            # Prepare values matrix
            values = [headers]
            for item in data:
                row_vals = []
                for val in item.values():
                    if val is None:
                        row_vals.append("")
                    else:
                        row_vals.append(str(val))
                values.append(row_vals)

            ws.clear()
            ws.update(values, value_input_option="USER_ENTERED")

        flash(f"Successfully synchronized {len(exports)} database tables ({total_rows_synced} total rows) to Google Sheets!", "success")

    except Exception as e:
        flash(f"Google Sheets Sync failed: {e}. Check API permissions, spreadsheet sharing, and credentials file.", "error")

    return redirect(url_for("sync_sheets_page"))

# -----------------------------------------------------------------------------
@app.route("/export-excel")
def export_excel():
    """Export all 8 MySQL database tables directly into a clean multi-sheet Excel (.xlsx) file."""
    try:
        import io
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        exports = {
            'Students': (
                'SELECT student_id, roll_no, first_name, last_name, email, phone, admission_year, current_status FROM students ORDER BY roll_no',
                ['Student ID', 'Roll No', 'First Name', 'Last Name', 'Email', 'Phone', 'Admission Year', 'Status']
            ),
            'Academic_History': (
                '''SELECT h.history_id, s.roll_no, h.education_level, h.institution, h.completion_year, h.marks_obtained, h.marks_total, h.percentage
                   FROM academic_history h JOIN students s ON s.student_id=h.student_id ORDER BY s.roll_no, h.completion_year''',
                ['History ID', 'Roll No', 'Education Level', 'Institution', 'Completion Year', 'Marks Obtained', 'Total Marks', 'Percentage (%)']
            ),
            'Semesters': (
                '''SELECT sem.semester_id, s.roll_no, sem.semester_no, sem.academic_year, sem.sgpa, sem.cgpa, 
                          IF(sem.is_gap_after=1, 'YES', 'NO') as gap_flag, sem.gap_years, sem.remarks
                   FROM semesters sem JOIN students s ON s.student_id=sem.student_id ORDER BY s.roll_no, sem.semester_no''',
                ['Semester ID', 'Roll No', 'Semester No', 'Academic Year', 'SGPA', 'CGPA', 'Gap After?', 'Gap Years', 'Remarks']
            ),
            'Subjects': (
                'SELECT subject_id, subject_code, subject_name, subject_type, credits FROM subjects ORDER BY subject_type, subject_code',
                ['Subject ID', 'Subject Code', 'Subject Name', 'Course Type', 'Credits']
            ),
            'Semester_Marks': (
                '''SELECT m.mark_id, st.roll_no, s.semester_no, sub.subject_code, sub.subject_name, sub.subject_type,
                          m.internal_marks, m.external_marks, m.practical_marks, m.total_marks, m.max_marks, m.grade
                   FROM semester_subject_marks m
                   JOIN semesters s ON s.semester_id=m.semester_id
                   JOIN students st ON st.student_id=s.student_id
                   JOIN subjects sub ON sub.subject_id=m.subject_id
                   ORDER BY st.roll_no, s.semester_no, sub.subject_code''',
                ['Mark ID', 'Roll No', 'Semester', 'Subject Code', 'Subject Name', 'Type', 'Internal', 'External', 'Practical', 'Total', 'Max', 'Grade']
            ),
            'Seminars': (
                '''SELECT sem.seminar_id, s.roll_no, sem.title, sem.seminar_type, sem.organizer, sem.event_date, sem.certificate_url
                   FROM seminars sem JOIN students s ON s.student_id=sem.student_id ORDER BY sem.event_date DESC''',
                ['Seminar ID', 'Roll No', 'Title', 'Seminar Type', 'Organizer', 'Event Date', 'Certificate URL']
            ),
            'Activities': (
                '''SELECT a.activity_id, s.roll_no, a.title, a.activity_type, a.role, a.organizer, a.activity_date, a.certificate_url
                   FROM activities a JOIN students s ON s.student_id=a.student_id ORDER BY a.activity_date DESC''',
                ['Activity ID', 'Roll No', 'Title', 'Category', 'Role / Award', 'Organizer', 'Date', 'Certificate URL']
            ),
            'Drop_Years': (
                '''SELECT d.drop_id, s.roll_no, d.year_start, d.year_end, (d.year_end - d.year_start) as duration, d.reason
                   FROM drop_years d JOIN students s ON s.student_id=d.student_id ORDER BY d.year_start DESC''',
                ['Drop ID', 'Roll No', 'Start Year', 'End Year', 'Duration (Years)', 'Reason / Justification']
            )
        }

        header_fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
        header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')

        for tab_name, (query, headers) in exports.items():
            ws = wb.create_sheet(title=tab_name)
            ws.append(headers)
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')

            data = rows(query)
            for item in data:
                row_vals = [str(v) if v is not None else '' for v in item.values()]
                ws.append(row_vals)

            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name='Student_Progression_Database.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f'Failed to generate Excel export: {e}', 'error')
        return redirect(url_for('sync_sheets_page'))

@app.route("/export-csv")
def export_csv():
    """Export table data as CSV - specifically designed for Google Sheets =IMPORTDATA() formula."""
    import csv
    import io

    table = request.args.get("table", "students").strip().lower()

    exports = {
        'students': (
            'SELECT student_id, roll_no, first_name, last_name, email, phone, admission_year, current_status FROM students ORDER BY roll_no',
            ['Student ID', 'Roll No', 'First Name', 'Last Name', 'Email', 'Phone', 'Admission Year', 'Status']
        ),
        'academic_history': (
            '''SELECT h.history_id, s.roll_no, h.education_level, h.institution, h.completion_year, h.marks_obtained, h.marks_total, h.percentage
               FROM academic_history h JOIN students s ON s.student_id=h.student_id ORDER BY s.roll_no, h.completion_year''',
            ['History ID', 'Roll No', 'Education Level', 'Institution', 'Completion Year', 'Marks Obtained', 'Total Marks', 'Percentage (%)']
        ),
        'semesters': (
            '''SELECT sem.semester_id, s.roll_no, sem.semester_no, sem.academic_year, sem.sgpa, sem.cgpa, 
                      IF(sem.is_gap_after=1, 'YES', 'NO') as gap_flag, sem.gap_years, sem.remarks
               FROM semesters sem JOIN students s ON s.student_id=sem.student_id ORDER BY s.roll_no, sem.semester_no''',
            ['Semester ID', 'Roll No', 'Semester No', 'Academic Year', 'SGPA', 'CGPA', 'Gap After?', 'Gap Years', 'Remarks']
        ),
        'subjects': (
            'SELECT subject_id, subject_code, subject_name, subject_type, credits FROM subjects ORDER BY subject_type, subject_code',
            ['Subject ID', 'Subject Code', 'Subject Name', 'Course Type', 'Credits']
        ),
        'semester_marks': (
            '''SELECT m.mark_id, st.roll_no, s.semester_no, sub.subject_code, sub.subject_name, sub.subject_type,
                      m.internal_marks, m.external_marks, m.practical_marks, m.total_marks, m.max_marks, m.grade
               FROM semester_subject_marks m
               JOIN semesters s ON s.semester_id=m.semester_id
               JOIN students st ON st.student_id=s.student_id
               JOIN subjects sub ON sub.subject_id=m.subject_id
               ORDER BY st.roll_no, s.semester_no, sub.subject_code''',
            ['Mark ID', 'Roll No', 'Semester', 'Subject Code', 'Subject Name', 'Type', 'Internal', 'External', 'Practical', 'Total', 'Max', 'Grade']
        ),
        'seminars': (
            '''SELECT sem.seminar_id, s.roll_no, sem.title, sem.seminar_type, sem.organizer, sem.event_date, sem.certificate_url
               FROM seminars sem JOIN students s ON s.student_id=sem.student_id ORDER BY sem.event_date DESC''',
            ['Seminar ID', 'Roll No', 'Title', 'Seminar Type', 'Organizer', 'Event Date', 'Certificate URL']
        ),
        'activities': (
            '''SELECT a.activity_id, s.roll_no, a.title, a.activity_type, a.role, a.organizer, a.activity_date, a.certificate_url
               FROM activities a JOIN students s ON s.student_id=a.student_id ORDER BY a.activity_date DESC''',
            ['Activity ID', 'Roll No', 'Title', 'Category', 'Role / Award', 'Organizer', 'Date', 'Certificate URL']
        ),
        'drop_years': (
            '''SELECT d.drop_id, s.roll_no, d.year_start, d.year_end, (d.year_end - d.year_start) as duration, d.reason
               FROM drop_years d JOIN students s ON s.student_id=d.student_id ORDER BY d.year_start DESC''',
            ['Drop ID', 'Roll No', 'Start Year', 'End Year', 'Duration (Years)', 'Reason / Justification']
        )
    }

    if table not in exports:
        table = 'students'

    query, headers = exports[table]
    data = rows(query)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for item in data:
        writer.writerow([str(v) if v is not None else '' for v in item.values()])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"inline; filename={table}.csv"}
    )

@app.route("/api/export-all")
def api_export_all():
    """Return all 8 database tables and column headers as JSON for Google Apps Script."""
    exports = {
        'Students': (
            'SELECT student_id, roll_no, first_name, last_name, email, phone, admission_year, current_status FROM students ORDER BY roll_no',
            ['Student ID', 'Roll No', 'First Name', 'Last Name', 'Email', 'Phone', 'Admission Year', 'Status']
        ),
        'Academic_History': (
            '''SELECT h.history_id, s.roll_no, h.education_level, h.institution, h.completion_year, h.marks_obtained, h.marks_total, h.percentage
               FROM academic_history h JOIN students s ON s.student_id=h.student_id ORDER BY s.roll_no, h.completion_year''',
            ['History ID', 'Roll No', 'Education Level', 'Institution', 'Completion Year', 'Marks Obtained', 'Total Marks', 'Percentage (%)']
        ),
        'Semesters': (
            '''SELECT sem.semester_id, s.roll_no, sem.semester_no, sem.academic_year, sem.sgpa, sem.cgpa, 
                      IF(sem.is_gap_after=1, 'YES', 'NO') as gap_flag, sem.gap_years, sem.remarks
               FROM semesters sem JOIN students s ON s.student_id=sem.student_id ORDER BY s.roll_no, sem.semester_no''',
            ['Semester ID', 'Roll No', 'Semester No', 'Academic Year', 'SGPA', 'CGPA', 'Gap After?', 'Gap Years', 'Remarks']
        ),
        'Subjects': (
            'SELECT subject_id, subject_code, subject_name, subject_type, credits FROM subjects ORDER BY subject_type, subject_code',
            ['Subject ID', 'Subject Code', 'Subject Name', 'Course Type', 'Credits']
        ),
        'Semester_Marks': (
            '''SELECT m.mark_id, st.roll_no, s.semester_no, sub.subject_code, sub.subject_name, sub.subject_type,
                      m.internal_marks, m.external_marks, m.practical_marks, m.total_marks, m.max_marks, m.grade
                   FROM semester_subject_marks m
                   JOIN semesters s ON s.semester_id=m.semester_id
                   JOIN students st ON st.student_id=s.student_id
                   JOIN subjects sub ON sub.subject_id=m.subject_id
                   ORDER BY st.roll_no, s.semester_no, sub.subject_code''',
            ['Mark ID', 'Roll No', 'Semester', 'Subject Code', 'Subject Name', 'Type', 'Internal', 'External', 'Practical', 'Total', 'Max', 'Grade']
        ),
        'Seminars': (
            '''SELECT sem.seminar_id, s.roll_no, sem.title, sem.seminar_type, sem.organizer, sem.event_date, sem.certificate_url
               FROM seminars sem JOIN students s ON s.student_id=sem.student_id ORDER BY sem.event_date DESC''',
            ['Seminar ID', 'Roll No', 'Title', 'Seminar Type', 'Organizer', 'Event Date', 'Certificate URL']
        ),
        'Activities': (
            '''SELECT a.activity_id, s.roll_no, a.title, a.activity_type, a.role, a.organizer, a.activity_date, a.certificate_url
               FROM activities a JOIN students s ON s.student_id=a.student_id ORDER BY a.activity_date DESC''',
            ['Activity ID', 'Roll No', 'Title', 'Category', 'Role / Award', 'Organizer', 'Date', 'Certificate URL']
        ),
        'Drop_Years': (
            '''SELECT d.drop_id, s.roll_no, d.year_start, d.year_end, (d.year_end - d.year_start) as duration, d.reason
               FROM drop_years d JOIN students s ON s.student_id=d.student_id ORDER BY d.year_start DESC''',
            ['Drop ID', 'Roll No', 'Start Year', 'End Year', 'Duration (Years)', 'Reason / Justification']
        )
    }
    result = {}
    for table_name, (query, headers) in exports.items():
        data = rows(query)
        table_rows = []
        for item in data:
            table_rows.append([str(v) if v is not None else '' for v in item.values()])
        result[table_name] = {
            "headers": headers,
            "rows": table_rows
        }
    return jsonify(result)

@app.route("/update-sheets-config", methods=["POST"])
def update_sheets_config():
    """Update Google Sheets ID and credentials directly from the web interface."""
    raw_sheet = request.form.get("sheet_id_or_url", "").strip()
    sheet_id = raw_sheet
    url_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", raw_sheet)
    if url_match:
        sheet_id = url_match.group(1)

    if sheet_id:
        set_key(ENV_PATH, "GOOGLE_SHEET_ID", sheet_id)

    if "creds_file_upload" in request.files:
        f = request.files["creds_file_upload"]
        if f and f.filename and f.filename.endswith(".json"):
            creds_dir = os.path.join(os.path.dirname(__file__), "credentials")
            os.makedirs(creds_dir, exist_ok=True)
            save_path = os.path.join(creds_dir, "service_account.json")
            f.save(save_path)
            set_key(ENV_PATH, "GOOGLE_CREDENTIALS", "credentials/service_account.json")
            flash("Google Service Account credentials file saved successfully!", "success")

    load_dotenv(ENV_PATH, override=True)
    if sheet_id:
        flash(f"Google Spreadsheet ID configured successfully: {sheet_id}", "success")
    return redirect(url_for("sync_sheets_page"))

# -----------------------------------------------------------------------------
# PAGE 10: DOCUMENTATION
# -----------------------------------------------------------------------------
@app.route("/documentation")
def documentation_page():
    return render_template("documentation.html", active_page="documentation")

# -----------------------------------------------------------------------------
# ADMIN TOOLS: INITIALIZATION, DEMO SEED, CONFIGURATION
# -----------------------------------------------------------------------------
@app.route("/init-db", methods=["POST"])
def init_database():
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        run_sql_script(schema_path)
        flash("Database schema initialized successfully! All 8 tables and constraints created.", "success")
    except Exception as e:
        flash(f"Failed to initialize schema: {e}", "error")
    return redirect(request.referrer or url_for("index"))

@app.route("/seed-db", methods=["POST"])
def seed_database():
    try:
        seed_path = os.path.join(os.path.dirname(__file__), "seed.sql")
        run_sql_script(seed_path)
        flash("Fictional DEMO student records, subjects, semester results, marks, seminars, and activities loaded successfully!", "success")
    except Exception as e:
        flash(f"Error seeding demo data: {e}", "error")
    return redirect(url_for("index"))

@app.route("/update-db-config", methods=["POST"])
def update_db_config():
    """Update .env configuration dynamically from web modal."""
    host = request.form.get("db_host", "localhost").strip()
    port = request.form.get("db_port", "3307").strip()
    user = request.form.get("db_user", "root").strip()
    password = request.form.get("db_password", "")
    dbname = request.form.get("db_name", "student_progression").strip()

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("")

    set_key(env_path, "DB_HOST", host)
    set_key(env_path, "DB_PORT", port)
    set_key(env_path, "DB_USER", user)
    set_key(env_path, "DB_PASSWORD", password)
    set_key(env_path, "DB_NAME", dbname)

    # Reload environment
    load_dotenv(env_path, override=True)

    # Test connection
    status = check_db_status()
    if status["connected"]:
        flash(f"Connected successfully to MySQL on {host}:{port}!", "success")
    else:
        flash(f"Configuration saved to .env, but connection test failed: {status['error']}", "warning")

    return redirect(request.referrer or url_for("index"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Host on 0.0.0.0 so it is accessible from any device on the network / public tunnel
    app.run(host="0.0.0.0", port=port, debug=True)
