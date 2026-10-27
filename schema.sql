CREATE DATABASE IF NOT EXISTS student_progression
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_progression;

CREATE TABLE IF NOT EXISTS students (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  roll_no VARCHAR(30) NOT NULL UNIQUE,
  first_name VARCHAR(80) NOT NULL,
  last_name VARCHAR(80) NOT NULL,
  email VARCHAR(150) UNIQUE,
  phone VARCHAR(25),
  admission_year YEAR,
  current_status ENUM('Active','Graduated','Dropped','On Leave') NOT NULL DEFAULT 'Active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS academic_history (
  history_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  education_level ENUM('Secondary','Higher Secondary','Diploma','Other') NOT NULL,
  institution VARCHAR(180),
  completion_year YEAR,
  marks_obtained DECIMAL(7,2),
  marks_total DECIMAL(7,2),
  percentage DECIMAL(5,2),
  CONSTRAINT fk_history_student FOREIGN KEY (student_id)
    REFERENCES students(student_id) ON DELETE CASCADE,
  CONSTRAINT chk_history_marks CHECK (marks_obtained IS NULL OR marks_obtained >= 0),
  CONSTRAINT chk_history_total CHECK (marks_total IS NULL OR marks_total > 0),
  CONSTRAINT chk_history_percentage CHECK (percentage IS NULL OR percentage BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS semesters (
  semester_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  semester_no TINYINT NOT NULL,
  academic_year VARCHAR(9),
  sgpa DECIMAL(4,2),
  cgpa DECIMAL(4,2),
  is_gap_after BOOLEAN NOT NULL DEFAULT FALSE,
  gap_years TINYINT NOT NULL DEFAULT 0,
  remarks VARCHAR(255),
  UNIQUE KEY uq_student_semester (student_id, semester_no),
  CONSTRAINT fk_semester_student FOREIGN KEY (student_id)
    REFERENCES students(student_id) ON DELETE CASCADE,
  CONSTRAINT chk_semester_no CHECK (semester_no BETWEEN 1 AND 12),
  CONSTRAINT chk_sgpa CHECK (sgpa IS NULL OR sgpa BETWEEN 0 AND 10),
  CONSTRAINT chk_cgpa CHECK (cgpa IS NULL OR cgpa BETWEEN 0 AND 10),
  CONSTRAINT chk_gap_years CHECK (gap_years BETWEEN 0 AND 10)
);

CREATE TABLE IF NOT EXISTS subjects (
  subject_id INT AUTO_INCREMENT PRIMARY KEY,
  subject_code VARCHAR(30) NOT NULL UNIQUE,
  subject_name VARCHAR(150) NOT NULL,
  subject_type ENUM('Theory','Lab') NOT NULL,
  credits DECIMAL(4,1) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS semester_subject_marks (
  mark_id INT AUTO_INCREMENT PRIMARY KEY,
  semester_id INT NOT NULL,
  subject_id INT NOT NULL,
  internal_marks DECIMAL(6,2),
  external_marks DECIMAL(6,2),
  practical_marks DECIMAL(6,2),
  total_marks DECIMAL(6,2),
  max_marks DECIMAL(6,2) NOT NULL DEFAULT 100,
  grade VARCHAR(5),
  UNIQUE KEY uq_semester_subject (semester_id, subject_id),
  CONSTRAINT fk_mark_semester FOREIGN KEY (semester_id)
    REFERENCES semesters(semester_id) ON DELETE CASCADE,
  CONSTRAINT fk_mark_subject FOREIGN KEY (subject_id)
    REFERENCES subjects(subject_id) ON DELETE CASCADE,
  CONSTRAINT chk_internal_marks CHECK (internal_marks IS NULL OR internal_marks BETWEEN 0 AND 100),
  CONSTRAINT chk_external_marks CHECK (external_marks IS NULL OR external_marks BETWEEN 0 AND 100),
  CONSTRAINT chk_practical_marks CHECK (practical_marks IS NULL OR practical_marks BETWEEN 0 AND 100),
  CONSTRAINT chk_total_marks CHECK (total_marks IS NULL OR total_marks >= 0),
  CONSTRAINT chk_max_marks CHECK (max_marks > 0)
);

CREATE TABLE IF NOT EXISTS seminars (
  seminar_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  title VARCHAR(180) NOT NULL,
  seminar_type ENUM('Internal','External') NOT NULL,
  organizer VARCHAR(180),
  event_date DATE,
  certificate_url VARCHAR(500),
  CONSTRAINT fk_seminar_student FOREIGN KEY (student_id)
    REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
  activity_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  title VARCHAR(180) NOT NULL,
  activity_type ENUM('Technical','Co-curricular','Extra-curricular') NOT NULL,
  role VARCHAR(100),
  organizer VARCHAR(180),
  activity_date DATE,
  certificate_url VARCHAR(500),
  CONSTRAINT fk_activity_student FOREIGN KEY (student_id)
    REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drop_years (
  drop_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  year_start YEAR NOT NULL,
  year_end YEAR NOT NULL,
  reason VARCHAR(255),
  CONSTRAINT fk_drop_student FOREIGN KEY (student_id)
    REFERENCES students(student_id) ON DELETE CASCADE,
  CONSTRAINT chk_drop_years CHECK (year_end >= year_start)
);

-- Example subjects can be inserted using the GUI or SQL.
