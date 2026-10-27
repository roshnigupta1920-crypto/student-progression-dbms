# Student Academic Progression and Portfolio Management System

A production-grade, college-demo-ready web application built with **Python Flask**, **MySQL 8.0**, **Bootstrap 5**, **Chart.js**, and **Google Sheets API**.

---

## 🌟 Executive Overview
The **Student Academic Progression and Portfolio Management System** provides an integrated digital ecosystem for managing student demographic information, prior qualification benchmarks (Secondary 10th and Higher Secondary 12th/Diploma), multi-semester SGPA & CGPA progressions, theory vs laboratory examination marks, co-curricular/extra-curricular portfolios, and formal academic leave/drop intervals.

The database is rigorously modeled to satisfy **Third Normal Form (3NF)** with strict relational constraints, cascading operations, and real-time visualization of academic curves.

---

## 🚀 Key Features

### 1. 10 Dedicated Responsive Pages
1. **Dashboard (`/`):** Summary statistics (Total, Active, Graduated, Dropped, Seminars, Activities), three Chart.js visual analytics (Enrollment Status Doughnut, Semester-wise Average SGPA Bar, and Portfolio Category Split), search bar, and recent student directory.
2. **Students Management (`/students`):** Complete CRUD for students (Unique Roll No, First/Last Name, Email, Phone, Admission Year, Status) with search, status filters, and confirmation modals.
3. **Dedicated Student Profile (`/students/<id>`):** Interactive portfolio with personal details, dynamic SGPA/CGPA line progression chart with academic gap indicators, theory & lab marks tables, and quick action buttons.
4. **Academic History (`/academic-history`):** Complete CRUD for prior school records (Secondary 10th, Higher Secondary 12th, Diploma, Other) with percentage auto-calculation and level filtering.
5. **Semester Results (`/semesters`):** Multi-semester SGPA and CGPA tracking (1–12), academic year logging, gap years duration, and unique constraints per student-semester.
6. **Subject & Lab Marks (`/marks`):** Curriculum subject management (Code, Name, Type: Theory/Lab, Credits) and semester examination marks entry (Internal, External, Practical, Total, Max, Grade) with auto-sum assistance.
7. **Seminars (`/seminars`):** Category-segregated seminar logs (Internal Departmental vs External Conferences/IEEE) with certificate verification links and filter tabs.
8. **Activities Portfolio (`/activities`):** Extracurricular and co-curricular achievements categorized into Technical, Co-curricular, and Extra-curricular events with role and organizer tracking.
9. **Academic Drop / Gap Years (`/drop-years`):** Institutional audit of student academic breaks, hiatus duration calculation, rationale logging, and `CHECK (year_end >= year_start)` enforcement.
10. **Google Sheets Sync (`/sync-sheets`):** One-way synchronization dashboard exporting all 8 relational tables to separate spreadsheet worksheets using `gspread` and Google Cloud Service Account credentials.
11. **Interactive Documentation (`/documentation`):** Complete in-app technical reference, 3NF normalization justification, schema data dictionary, and College Viva Voce Q&A preparation.

---

## 🛠️ Technology Stack
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js.
- **Backend:** Python 3.10+ / Python 3.14, Flask 3.1.
- **Database:** MySQL 8.0 (InnoDB storage engine, UTF8MB4 encoding, 3NF schema, CHECK constraints, Cascading Foreign Keys).
- **Driver:** `mysql-connector-python` with parameterized SQL queries.
- **Cloud Integration:** Google Sheets API v4 & Google Drive API via `gspread` and `google-auth`.

---

## 📋 Relational Database Schema (3NF)

The database schema `student_progression` is composed of 8 normalized relational tables:
- `students`: Central student demographic profile (PK: `student_id`, Unique: `roll_no`, `email`).
- `academic_history`: Pre-college qualifying history (PK: `history_id`, FK: `student_id` ON DELETE CASCADE, Checks: percentage 0–100).
- `semesters`: Semester-wise SGPA and CGPA results (PK: `semester_id`, FK: `student_id` ON DELETE CASCADE, Unique: `uq_student_semester(student_id, semester_no)`, Checks: SGPA/CGPA 0–10).
- `subjects`: Departmental course catalog (PK: `subject_id`, Unique: `subject_code`, Type: `Theory` / `Lab`).
- `semester_subject_marks`: Junction table linking semesters to subjects (PK: `mark_id`, FKs: `semester_id`, `subject_id` ON DELETE CASCADE, Unique: `uq_semester_subject(semester_id, subject_id)`).
- `seminars`: Technical presentations (PK: `seminar_id`, FK: `student_id` ON DELETE CASCADE, Enum: `Internal`, `External`).
- `activities`: Accomplishments (PK: `activity_id`, FK: `student_id` ON DELETE CASCADE, Enum: `Technical`, `Co-curricular`, `Extra-curricular`).
- `drop_years`: Formal academic gap intervals (PK: `drop_id`, FK: `student_id` ON DELETE CASCADE, Check: `year_end >= year_start`).

---

## ⚙️ Setup and Installation (Windows)

### Step 1: Open Terminal in Project Folder
Open PowerShell or Command Prompt in the project folder:
```powershell
cd "d:\d drive data\Downloads\Student_Progression_DBMS_Project"
```

### Step 2: Install Dependencies
Install all required libraries using `pip`:
```powershell
pip install -r requirements.txt
```
*(Dependencies: `Flask`, `mysql-connector-python`, `python-dotenv`, `gspread`, `google-auth`)*

### Step 3: Configure `.env`
Create or edit `.env` in the project root:
```ini
# MySQL Configuration
# NOTE: Check whether your local MySQL runs on port 3307 or 3306
DB_HOST=localhost
DB_PORT=3307
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=student_progression

# Flask Security Secret Key
FLASK_SECRET_KEY=student-progression-secure-demo-key-2026

# Google Sheets API One-Way Synchronization (Optional)
GOOGLE_SHEET_ID=
GOOGLE_CREDENTIALS=credentials/service_account.json
```

### Step 4: Import Database Schema and Demo Seed Data
You can initialize the database using either **Method A** or **Method B**:

#### Method A: Using MySQL Command Line or MySQL Workbench
In MySQL Workbench, open and execute `schema.sql`, followed by `seed.sql`.
Alternatively, in PowerShell/Command Prompt:
```powershell
# Create database and tables
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -h localhost -P 3307 -u root -p < schema.sql

# Load fictional demo records
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -h localhost -P 3307 -u root -p < seed.sql
```

#### Method B: One-Click Web UI Initialization
1. Start the application (`python app.py`).
2. If MySQL credentials are connected, navigate to the Dashboard and click **Load Demo Seed Data**.
3. All tables and fictional students (`23CS001`, `23CS014`, `22CS088`, `20CS042`, `21CS099`) will be loaded automatically!

### Step 5: Start the Flask Web Server
```powershell
python app.py
```
Open your browser and navigate to:
**http://127.0.0.1:5000**

---

## 📊 Google Sheets One-Way Synchronization Setup
1. In the [Google Cloud Console](https://console.cloud.google.com/), enable the **Google Sheets API** and **Google Drive API**.
2. Create a **Service Account**, generate a JSON key, and save it as:
   `credentials/service_account.json`
3. Create a new Google Spreadsheet at [sheets.new](https://sheets.new).
4. Click **Share** on the Google Sheet and give **Editor** access to the service account client email (found in `service_account.json`).
5. Copy the Spreadsheet ID from the URL (`https://docs.google.com/spreadsheets/d/<ID>/edit`) into `.env` as `GOOGLE_SHEET_ID=<ID>`.
6. Navigate to **9. Google Sheets Sync** in the sidebar and click **Sync Now**.
7. The system will create and refresh 8 distinct worksheet tabs:
   - `Students`
   - `Academic_History`
   - `Semesters`
   - `Subjects`
   - `Semester_Marks`
   - `Seminars`
   - `Activities`
   - `Drop_Years`

---

## 🎓 College Demo & Viva Voce Quick Checklist
- [x] **Relational Schema:** 8 normalized tables in 3NF with Primary & Foreign keys.
- [x] **Referential Integrity:** `ON DELETE CASCADE` configured on all child tables.
- [x] **Integrity Constraints:** CHECK constraints for SGPA (0–10), CGPA (0–10), percentage (0–100), marks, and gap years (`year_end >= year_start`).
- [x] **Uniqueness Rules:** Unique Roll Numbers, Unique Emails, Composite Unique `(student_id, semester_no)`, and Composite Unique `(semester_id, subject_id)`.
- [x] **CRUD Operations:** Full Create, Read, Update, and Delete implemented for all 8 entities with parameterized queries.
- [x] **Dynamic Charts:** Chart.js SGPA/CGPA line curves, gap markers, and enrollment status doughnut graphs.
- [x] **Defensive Error Handling:** App does not crash if MySQL or Google credentials are offline; clear alerts guide the evaluator.
- [x] **Clean UI Design:** Modern white background with navy/dark blue accents, responsive sidebar, stat cards, and modals.
