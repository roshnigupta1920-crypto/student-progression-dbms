-- =====================================================================
-- Student Academic Progression and Portfolio Management System
-- 10 REAL-TIME INDIAN DEMO RECORDS PER SECTION (College Evaluation Ready)
-- =====================================================================
-- Run schema.sql first, then run this file to populate all 8 tables.

USE student_progression;

-- ---------------------------------------------------------------------
-- 1. STUDENTS (10 Realistic Indian Student Records)
-- ---------------------------------------------------------------------
INSERT INTO students (student_id, roll_no, first_name, last_name, email, phone, admission_year, current_status) VALUES
(1, '23CS001', 'Aarav', 'Sharma', 'aarav.sharma@college.edu', '9820145672', 2023, 'Active'),
(2, '23CS014', 'Sneha', 'Kulkarni', 'sneha.kulkarni@college.edu', '9819234567', 2023, 'Active'),
(3, '22CS088', 'Rohan', 'Nair', 'rohan.nair@college.edu', '9845123456', 2022, 'Active'),
(4, '20CS042', 'Priya', 'Menon', 'priya.menon@college.edu', '9741234567', 2020, 'Graduated'),
(5, '21CS099', 'Arjun', 'Patel', 'arjun.patel@college.edu', '9924567890', 2021, 'Dropped'),
(6, '23IT023', 'Ananya', 'Iyer', 'ananya.iyer@college.edu', '9840123456', 2023, 'Active'),
(7, '22CS056', 'Aditya', 'Verma', 'aditya.verma@college.edu', '9415123456', 2022, 'Active'),
(8, '23CS077', 'Tanvi', 'Deshmukh', 'tanvi.deshmukh@college.edu', '9822345678', 2023, 'Active'),
(9, '21IT015', 'Mohammed Zaid', 'Khan', 'zaid.khan@college.edu', '9833456789', 2021, 'Graduated'),
(10, '24CS003', 'Riya', 'Sengupta', 'riya.sengupta@college.edu', '9830123456', 2024, 'Active')
ON DUPLICATE KEY UPDATE roll_no=VALUES(roll_no), first_name=VALUES(first_name), last_name=VALUES(last_name), email=VALUES(email);

-- ---------------------------------------------------------------------
-- 2. ACADEMIC HISTORY (10 Pre-College Records: 10th & 12th/Diploma)
-- ---------------------------------------------------------------------
INSERT INTO academic_history (history_id, student_id, education_level, institution, completion_year, marks_obtained, marks_total, percentage) VALUES
(1, 1, 'Secondary', 'St. Xavier High School, Fort, Mumbai (CBSE)', 2021, 465.00, 500.00, 93.00),
(2, 1, 'Higher Secondary', 'D.G. Ruparel Junior College, Matunga, Mumbai (State Board)', 2023, 540.00, 600.00, 90.00),
(3, 2, 'Secondary', 'Kendriya Vidyalaya No. 1, Pune (CBSE)', 2021, 455.00, 500.00, 91.00),
(4, 2, 'Higher Secondary', 'Fergusson Junior College, Pune (Maharashtra HSC)', 2023, 515.00, 600.00, 85.83),
(5, 3, 'Secondary', 'National Public School, Indiranagar, Bengaluru (ICSE)', 2020, 480.00, 500.00, 96.00),
(6, 3, 'Higher Secondary', 'St. Joseph Pre-University College, Bengaluru (Karnataka PU Board)', 2022, 565.00, 600.00, 94.17),
(7, 4, 'Secondary', 'Delhi Public School, R.K. Puram, New Delhi (CBSE)', 2018, 478.00, 500.00, 95.60),
(8, 4, 'Higher Secondary', 'Delhi Public School, R.K. Puram, New Delhi (CBSE)', 2020, 560.00, 600.00, 93.33),
(9, 5, 'Secondary', 'Shree Vallabh Ashram English Medium School, Vadodara (GSEB)', 2019, 410.00, 500.00, 82.00),
(10, 5, 'Diploma', 'Government Polytechnic, Ahmedabad (GTU Diploma Engg)', 2021, 840.00, 1000.00, 84.00)
ON DUPLICATE KEY UPDATE student_id=VALUES(student_id), education_level=VALUES(education_level), institution=VALUES(institution);

-- ---------------------------------------------------------------------
-- 3. SUBJECTS (10 Curriculum Courses: Theory & Laboratory Courses)
-- ---------------------------------------------------------------------
INSERT INTO subjects (subject_id, subject_code, subject_name, subject_type, credits) VALUES
(1, 'CS201', 'Data Structures and Algorithms', 'Theory', 4.0),
(2, 'CS202', 'Database Management Systems', 'Theory', 4.0),
(3, 'CS203', 'Computer Organization and Architecture', 'Theory', 3.0),
(4, 'CS204', 'Operating Systems and System Programming', 'Theory', 4.0),
(5, 'CS205', 'DBMS and SQL Laboratory', 'Lab', 1.5),
(6, 'CS206', 'Data Structures and Algorithms Lab', 'Lab', 1.5),
(7, 'CS301', 'Web Application Development', 'Theory', 3.0),
(8, 'CS302', 'Computer Networks and Security', 'Theory', 4.0),
(9, 'CS303', 'Full-Stack Web Development Laboratory', 'Lab', 1.5),
(10, 'CS304', 'Network Systems and Packet Analysis Lab', 'Lab', 1.5)
ON DUPLICATE KEY UPDATE subject_code=VALUES(subject_code), subject_name=VALUES(subject_name), subject_type=VALUES(subject_type);

-- ---------------------------------------------------------------------
-- 4. SEMESTERS (10+ Progression Records with SGPA/CGPA & Gaps)
-- ---------------------------------------------------------------------
INSERT INTO semesters (semester_id, student_id, semester_no, academic_year, sgpa, cgpa, is_gap_after, gap_years, remarks) VALUES
(1, 1, 1, '2023-2024', 8.75, 8.75, FALSE, 0, 'First Class with Distinction'),
(2, 1, 2, '2023-2024', 9.10, 8.92, FALSE, 0, 'Institute Merit List Rank 3'),
(3, 1, 3, '2024-2025', 9.25, 9.03, FALSE, 0, 'Deans Honor Roll'),
(4, 2, 1, '2023-2024', 8.40, 8.40, FALSE, 0, 'Regular First Class'),
(5, 2, 2, '2023-2024', 7.95, 8.18, TRUE, 1, 'Approved medical hiatus for surgery & rehabilitation'),
(6, 2, 3, '2025-2026', 8.80, 8.39, FALSE, 0, 'Resumed academics post-hiatus with distinction'),
(7, 3, 1, '2022-2023', 9.20, 9.20, FALSE, 0, 'Department Topper'),
(8, 3, 2, '2022-2023', 9.45, 9.32, FALSE, 0, 'Perfect 10 in Discrete Math and Algorithms'),
(9, 4, 8, '2023-2024', 9.50, 9.15, FALSE, 0, 'Graduated with University Gold Medal'),
(10, 7, 3, '2023-2024', 8.15, 8.22, FALSE, 0, 'Cleared core engineering coursework')
ON DUPLICATE KEY UPDATE student_id=VALUES(student_id), semester_no=VALUES(semester_no);

-- ---------------------------------------------------------------------
-- 5. SEMESTER SUBJECT MARKS (10 Detailed Examination Scores)
-- ---------------------------------------------------------------------
INSERT INTO semester_subject_marks (mark_id, semester_id, subject_id, internal_marks, external_marks, practical_marks, total_marks, max_marks, grade) VALUES
(1, 3, 1, 28.50, 64.00, NULL, 92.50, 100.00, 'O'),
(2, 3, 2, 29.00, 66.50, NULL, 95.50, 100.00, 'O'),
(3, 3, 5, 24.00, NULL, 24.50, 48.50, 50.00, 'O'),
(4, 3, 6, 23.50, NULL, 24.00, 47.50, 50.00, 'A+'),
(5, 5, 1, 24.00, 51.00, NULL, 75.00, 100.00, 'B+'),
(6, 5, 2, 25.50, 53.50, NULL, 79.00, 100.00, 'A'),
(7, 5, 5, 21.00, NULL, 22.00, 43.00, 50.00, 'A'),
(8, 8, 1, 29.50, 68.00, NULL, 97.50, 100.00, 'O'),
(9, 8, 2, 30.00, 69.00, NULL, 99.00, 100.00, 'O'),
(10, 8, 5, 25.00, NULL, 25.00, 50.00, 50.00, 'O')
ON DUPLICATE KEY UPDATE semester_id=VALUES(semester_id), subject_id=VALUES(subject_id);

-- ---------------------------------------------------------------------
-- 6. SEMINARS (10 Categorized Indian Academic & Industry Seminars)
-- ---------------------------------------------------------------------
INSERT INTO seminars (seminar_id, student_id, title, seminar_type, organizer, event_date, certificate_url) VALUES
(1, 1, 'Scalable B-Tree Indexing and Query Plans in Modern DBMS', 'Internal', 'Department Seminar Committee', '2024-03-15', 'https://certificates.college.edu/cs/23cs001-dbms.pdf'),
(2, 1, 'Next-Generation Vector Databases for AI and LLM Retrieval', 'External', 'IEEE Bombay Section Conference', '2024-08-22', 'https://ieee-bombay.org/verify/SEM-2024-9981'),
(3, 2, 'ACID vs BASE Consistency in Cloud Storage Engines', 'Internal', 'Open Source Student Forum, Pune', '2024-02-10', 'https://certificates.college.edu/cs/23cs014-acid.pdf'),
(4, 3, 'Query Optimization and Execution Internals in MySQL 8.0 InnoDB', 'External', 'ACM India Annual Technical Summit', '2023-11-18', 'https://acm-india.org/verify/ROHAN-NAIR-2023'),
(5, 4, 'Resilient Microservices Architecture and Circuit Breakers', 'External', 'CSI National Computing Convention', '2022-04-05', 'https://csi-india.org/cert/PM402'),
(6, 6, 'Formal Verification of Cryptographic Key Exchanges in TLS 1.3', 'External', 'IIT Madras Shaastra Research Symposium', '2024-01-20', 'https://shaastra.org/cert/2024-IYER-23'),
(7, 7, 'Automated CI/CD Deployment Pipelines Using Docker & Kubernetes', 'Internal', 'Computer Engineering Colloquium', '2023-09-14', 'https://certificates.college.edu/cs/22cs056-devops.pdf'),
(8, 8, 'Semantic Knowledge Graphs and Natural Language Embeddings', 'External', 'IEEE Pune Section Student Colloquium', '2024-04-12', 'https://ieeepune.org/verify/TANVI-DESHMUKH-2024'),
(9, 9, 'Zero-Trust Architecture and API Gateway Resilience', 'External', 'National Cyber Security Conclave, New Delhi', '2023-03-25', 'https://cyberconclave.gov.in/verify/MZK-2023-99'),
(10, 10, 'Graph Relational Modeling in High-Performance Social Networks', 'Internal', 'Freshers Technical Orientation Cell', '2024-10-05', 'https://certificates.college.edu/cs/24cs003-graph.pdf')
ON DUPLICATE KEY UPDATE student_id=VALUES(student_id), title=VALUES(title);

-- ---------------------------------------------------------------------
-- 7. ACTIVITIES (10 Portfolio Records: Technical, Co-curricular, Extra-curricular)
-- ---------------------------------------------------------------------
INSERT INTO activities (activity_id, student_id, title, activity_type, role, organizer, activity_date, certificate_url) VALUES
(1, 1, 'Smart India Hackathon (SIH 2024) Campus Round', 'Technical', 'Team Lead & Database Architect', 'Ministry of Education Innovation Cell, GoI', '2024-09-20', 'https://sih.gov.in/cert/23CS001'),
(2, 1, 'National Youth Parliament & Inter-College Debate', 'Co-curricular', 'Best Speaker (1st Runner Up)', 'Literary & Debating Society', '2024-01-14', 'https://college.edu/debsoc/2024-01'),
(3, 1, 'West Zone Inter-University Football Tournament', 'Extra-curricular', 'Midfielder & Vice Captain', 'Association of Indian Universities (AIU)', '2023-12-10', 'https://aiusports.org/football/2023-sharma'),
(4, 2, 'ACM-W All-India Women in Tech Hackathon', 'Technical', 'National Grand Finalist', 'ACM-W India Council', '2024-03-08', 'https://acmindia.org/wit-2024/23CS014'),
(5, 3, 'e-Yantra National Autonomous Robotics Challenge', 'Technical', 'First Place & Gold Medalist', 'IIT Bombay e-Yantra Robotics Lab', '2023-10-12', 'https://eyantra.iitb.ac.in/cert/RN-88'),
(6, 3, 'NSS Rural Health Camp & Blood Donation Drive', 'Extra-curricular', 'Student Volunteer Coordinator', 'National Service Scheme (NSS Cell)', '2023-08-15', 'https://nss.gov.in/volunteer/2023-88'),
(7, 4, 'Technovanza All-India Technical Symposium', 'Co-curricular', 'Overall Student Convener', 'College Student Council', '2022-02-24', 'https://technovanza.org/cert/pm-convener'),
(8, 6, 'TCS CodeVita Global Coding Championship', 'Technical', 'Global Round 2 Qualifier (Rank 142)', 'Tata Consultancy Services', '2023-11-05', 'https://codevita.tcs.com/verify/IYER-23IT'),
(9, 8, 'Maharashtra State Inter-University Cultural Dance Fest', 'Extra-curricular', 'First Prize (Kathak Solo)', 'Directorate of Cultural Affairs, Maharashtra', '2024-02-18', 'https://cultural.maharashtra.gov.in/cert/TD-2024'),
(10, 9, 'Cisco NetAcad All-India Packet Tracer Contest', 'Technical', 'State Level Winner (Maharashtra)', 'Cisco Networking Academy India', '2022-10-30', 'https://netacad.com/verify/ZAID-KHAN-2022')
ON DUPLICATE KEY UPDATE student_id=VALUES(student_id), title=VALUES(title);

-- ---------------------------------------------------------------------
-- 8. DROP / GAP YEARS (10 Realistic Academic Hiatus Records)
-- ---------------------------------------------------------------------
INSERT INTO drop_years (drop_id, student_id, year_start, year_end, reason) VALUES
(1, 2, 2024, 2025, 'Approved medical hiatus and rehabilitation following spinal surgery after Semester 2; officially resumed in July 2025.'),
(2, 5, 2022, 2024, 'Formal academic leave to pursue full-time entrepreneurship and launch an agritech IoT hardware startup supported by college incubator.'),
(3, 7, 2021, 2022, 'One-year drop post-Higher Secondary (Class 12) dedicated to intensive JEE Advanced and state CET examination preparation.'),
(4, 9, 2020, 2021, 'Academic hiatus taken after Class 12 due to family financial emergency and medical crisis during COVID-19 pandemic; resumed upon scholarship award.'),
(5, 8, 2022, 2023, 'One-year gap interval after 12th standard for national-level cultural Visharad examination in Kathak alongside entrance preparation.'),
(6, 3, 2021, 2022, 'Hiatus year taken before B.Tech admission for national science research fellowship training and KVPY scholarship preparation.'),
(7, 4, 2019, 2020, 'One-year gap interval after Class 12 for medical entrance exam (NEET) before choosing B.Tech in Computer Engineering.'),
(8, 6, 2022, 2023, 'Family inter-state relocation from Chennai to Mumbai post-12th standard and engineering entrance re-attempt.'),
(9, 10, 2023, 2024, 'One-year study leave following 12th CBSE for West Bengal Joint Entrance Examination (WBJEE) intensive preparation.'),
(10, 1, 2022, 2023, 'One-year academic gap interval after Higher Secondary for JEE preparation and national mathematics Olympiad participation.')
ON DUPLICATE KEY UPDATE student_id=VALUES(student_id), year_start=VALUES(year_start), year_end=VALUES(year_end);

-- =====================================================================
-- End of 10 Real-Time Indian Records Seed File
-- =====================================================================
