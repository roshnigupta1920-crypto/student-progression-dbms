import os
import sqlite3
import pandas as pd
import streamlit as st
import requests

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Student Academic Progression & Portfolio DBMS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# DATABASE HELPER
# -----------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "student_progression.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def query_df(query, params=()):
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params)

def execute_db(query, params=()):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        last_id = cur.lastrowid
        trigger_apps_script_sync()
        return last_id

def trigger_apps_script_sync():
    """Trigger Google Apps Script Webhook if configured."""
    appscript_url = os.getenv(
        "GOOGLE_APPSCRIPT_URL",
        "https://script.google.com/macros/s/AKfycbwPD_i-qs01BAxF0m4a7RfbSDHHmhB_5BI4SSUneAbrWxuHch8NngG4-qJZ3GgUr4gpWQ/exec"
    )
    if appscript_url:
        try:
            requests.get(appscript_url, timeout=10)
        except Exception:
            pass

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
st.sidebar.markdown("## 🎓 **Student DBMS**")
st.sidebar.caption("Progression & Portfolio Management")

nav_choice = st.sidebar.radio(
    "Navigation",
    [
        "1. Dashboard",
        "2. Students Directory",
        "3. Academic History",
        "4. Semester Results",
        "5. Subject & Lab Marks",
        "6. Seminars",
        "7. Activities",
        "8. Drop / Gap Years",
        "9. Google Sheets Sync",
        "10. Documentation"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("🟢 **Database: Active** (SQLite / MySQL Ready)")
st.sidebar.caption("Streamlit Cloud Production Deployment")

# -----------------------------------------------------------------------------
# 1. DASHBOARD
# -----------------------------------------------------------------------------
if nav_choice == "1. Dashboard":
    st.title("🎓 Academic & Portfolio Dashboard")
    st.markdown("Real-time overview of student academic progression, drop years, and achievement portfolios.")

    students_df = query_df("SELECT * FROM students")
    total_students = len(students_df)
    active_students = len(students_df[students_df['current_status'] == 'Active']) if total_students else 0
    grad_count = len(students_df[students_df['current_status'] == 'Graduated']) if total_students else 0
    drop_count = len(students_df[students_df['current_status'] == 'Dropped']) if total_students else 0
    
    seminars_cnt = query_df("SELECT COUNT(*) as c FROM seminars")['c'][0]
    activities_cnt = query_df("SELECT COUNT(*) as c FROM activities")['c'][0]

    # Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Students", f"{total_students}", "Enrolled")
    c2.metric("Active Students", f"{active_students}", "Currently Studying")
    c3.metric("Graduated / Dropped", f"{grad_count} / {drop_count}")
    c4.metric("Seminars / Activities", f"{seminars_cnt} / {activities_cnt}")

    st.markdown("---")

    # Charts Section
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📊 Enrollment Status Distribution")
        if total_students > 0:
            status_counts = students_df['current_status'].value_counts()
            st.bar_chart(status_counts)
    
    with col_right:
        st.subheader("📈 Semester-wise Average SGPA")
        sem_df = query_df("SELECT 'Sem ' || semester_no as sem, AVG(sgpa) as avg_sgpa FROM semesters GROUP BY semester_no ORDER BY semester_no")
        if not sem_df.empty:
            sem_df = sem_df.set_index('sem')
            st.bar_chart(sem_df['avg_sgpa'])

    st.markdown("---")
    st.subheader("📋 Enrolled Students Directory")
    st.dataframe(students_df[['roll_no', 'first_name', 'last_name', 'email', 'phone', 'admission_year', 'current_status']], use_container_width=True)

# -----------------------------------------------------------------------------
# 2. STUDENTS DIRECTORY & MANAGEMENT
# -----------------------------------------------------------------------------
elif nav_choice == "2. Students Directory":
    st.title("👥 Students Directory & Management")
    st.markdown("View, search, filter, and register new student records.")

    tab1, tab2 = st.tabs(["📋 View & Search Students", "➕ Register New Student"])

    with tab1:
        search_q = st.text_input("🔍 Search by name or roll number:")
        query = "SELECT * FROM students"
        params = ()
        if search_q:
            query += " WHERE roll_no LIKE ? OR first_name LIKE ? OR last_name LIKE ?"
            p = f"%{search_q}%"
            params = (p, p, p)
        df = query_df(query, params)
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Register a New Student")
        with st.form("add_student_form"):
            c1, c2 = st.columns(2)
            roll_no = c1.text_input("Roll Number *", placeholder="e.g. 24CS101")
            status = c2.selectbox("Current Status", ["Active", "Graduated", "Dropped", "On Leave"])
            
            c3, c4 = st.columns(2)
            fname = c3.text_input("First Name *", placeholder="First Name")
            lname = c4.text_input("Last Name *", placeholder="Last Name")

            c5, c6 = st.columns(2)
            email = c5.text_input("Email Address", placeholder="name@college.edu")
            phone = c6.text_input("Phone Number", placeholder="10-digit mobile")
            
            year = st.number_input("Admission Year", min_value=2015, max_value=2030, value=2024)
            submitted = st.form_submit_button("💾 Save Student & Auto-Sync to Google Sheets")

            if submitted:
                if not roll_no or not fname or not lname:
                    st.error("Roll Number, First Name, and Last Name are required.")
                else:
                    try:
                        execute_db(
                            "INSERT INTO students (roll_no, first_name, last_name, email, phone, admission_year, current_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (roll_no, fname, lname, email, phone, int(year), status)
                        )
                        st.success(f"✅ Student '{fname} {lname}' ({roll_no}) successfully registered and synced with Google Sheets!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error registering student: {e}")

# -----------------------------------------------------------------------------
# 3. ACADEMIC HISTORY
# -----------------------------------------------------------------------------
elif nav_choice == "3. Academic History":
    st.title("📚 Secondary & Higher Secondary Academic History")
    st.markdown("Track qualification benchmarks (10th, 12th, Diploma) prior to engineering enrollment.")
    df = query_df("""
        SELECT s.roll_no, s.first_name || ' ' || s.last_name as student_name, 
               h.education_level, h.institution, h.completion_year, h.marks_obtained, h.marks_total, h.percentage
        FROM academic_history h
        JOIN students s ON s.student_id = h.student_id
        ORDER BY s.roll_no, h.completion_year
    """)
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# 4. SEMESTER RESULTS
# -----------------------------------------------------------------------------
elif nav_choice == "4. Semester Results":
    st.title("📈 Semester Results & Academic Progression")
    st.markdown("Track SGPA, cumulative CGPA, and formal academic gap indicators semester-by-semester.")
    df = query_df("""
        SELECT s.roll_no, s.first_name || ' ' || s.last_name as student_name,
               sem.semester_no, sem.academic_year, sem.sgpa, sem.cgpa,
               CASE WHEN sem.is_gap_after=1 THEN 'YES' ELSE 'NO' END as gap_after,
               sem.gap_years, sem.remarks
        FROM semesters sem
        JOIN students s ON s.student_id = sem.student_id
        ORDER BY s.roll_no, sem.semester_no
    """)
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. SUBJECT & LAB MARKS
# -----------------------------------------------------------------------------
elif nav_choice == "5. Subject & Lab Marks":
    st.title("📝 Subject & Lab Marks Evaluation")
    st.markdown("Detailed internal, external, practical scores, and final grades.")
    df = query_df("""
        SELECT st.roll_no, st.first_name || ' ' || st.last_name as student_name,
               s.semester_no, sub.subject_code, sub.subject_name, sub.subject_type,
               m.internal_marks, m.external_marks, m.practical_marks, m.total_marks, m.grade
        FROM semester_subject_marks m
        JOIN semesters s ON s.semester_id = m.semester_id
        JOIN students st ON st.student_id = s.student_id
        JOIN subjects sub ON sub.subject_id = m.subject_id
        ORDER BY st.roll_no, s.semester_no
    """)
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. SEMINARS
# -----------------------------------------------------------------------------
elif nav_choice == "6. Seminars":
    st.title("🎤 Seminars & Workshops")
    st.markdown("Track technical internal and external seminar presentations.")
    df = query_df("""
        SELECT s.roll_no, s.first_name || ' ' || s.last_name as student_name,
               sem.title, sem.seminar_type, sem.organizer, sem.event_date
        FROM seminars sem
        JOIN students s ON s.student_id = sem.student_id
        ORDER BY sem.event_date DESC
    """)
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# 7. ACTIVITIES
# -----------------------------------------------------------------------------
elif nav_choice == "7. Activities":
    st.title("🏆 Co-curricular & Extra-curricular Activities")
    st.markdown("Hackathons, sports, technical clubs, and university festivals.")
    df = query_df("""
        SELECT s.roll_no, s.first_name || ' ' || s.last_name as student_name,
               a.title, a.activity_type, a.role, a.organizer, a.activity_date
        FROM activities a
        JOIN students s ON s.student_id = a.student_id
        ORDER BY a.activity_date DESC
    """)
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# 8. DROP / GAP YEARS
# -----------------------------------------------------------------------------
elif nav_choice == "8. Drop / Gap Years":
    st.title("⏸️ Recorded Academic Drop Years")
    st.markdown("Document approved medical hiatuses, competitive entrance preparation, or entrepreneurship leaves.")
    df = query_df("""
        SELECT s.roll_no, s.first_name || ' ' || s.last_name as student_name,
               d.year_start, d.year_end, (d.year_end - d.year_start) as duration_years, d.reason
        FROM drop_years d
        JOIN students s ON s.student_id = d.student_id
        ORDER BY d.year_start DESC
    """)
    st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# 9. GOOGLE SHEETS SYNC
# -----------------------------------------------------------------------------
elif nav_choice == "9. Google Sheets Sync":
    st.title("☁️ Google Sheets Synchronization")
    st.markdown("One-way automated synchronization from relational tables to Google Sheets spreadsheet worksheets.")

    sheet_url = "https://docs.google.com/spreadsheets/d/1XnDIzjttKEEMuhzKA2b7p-L8hWiqMCrY4nQEFw98swk/edit"
    appscript_url = "https://script.google.com/macros/s/AKfycbwPD_i-qs01BAxF0m4a7RfbSDHHmhB_5BI4SSUneAbrWxuHch8NngG4-qJZ3GgUr4gpWQ/exec"

    st.info(f"Connected Spreadsheet: [Open Google Sheet]({sheet_url})")

    if st.button("🔄 Trigger Real-Time Sync to Google Sheets", type="primary"):
        with st.spinner("Pinging Google Apps Script Webhook..."):
            try:
                res = requests.get(appscript_url, timeout=20)
                if res.status_code == 200:
                    st.success("✅ Successfully triggered Google Sheets Sync! Open your sheet to see the updated records.")
                else:
                    st.warning(f"Response status: {res.status_code}")
            except Exception as e:
                st.error(f"Sync failed: {e}")

# -----------------------------------------------------------------------------
# 10. DOCUMENTATION
# -----------------------------------------------------------------------------
elif nav_choice == "10. Documentation":
    st.title("📖 Documentation & System Architecture")
    st.markdown("""
    ### System Architecture
    - **Frontend**: Streamlit + Bootstrap CSS Styling
    - **Database**: 3NF Normalized Relational Schema (8 Tables)
    - **Integrations**: Google Sheets via Apps Script Webhook
    
    ### Relational Tables:
    1. `students` (Student Master Table - 8 Columns)
    2. `academic_history` (10th/12th/Diploma Benchmarks)
    3. `semesters` (SGPA, CGPA, Academic Gaps)
    4. `subjects` (Curriculum Theory and Laboratory Courses)
    5. `semester_subject_marks` (Marks and Grades Evaluation)
    6. `seminars` (Internal & External Presentations)
    7. `activities` (Co-curricular & Extra-curricular)
    8. `drop_years` (Academic Drop Intervals & Justifications)
    """)
