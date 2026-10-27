import os
import re
import mysql.connector

DB_PASS = "rozz@123"
DATABASES = ["student_progress.db", "student_progress"]

def split_sql(sql_text):
    statements = []
    current = []
    in_single = False
    in_double = False
    in_backtick = False
    i = 0
    n = len(sql_text)
    while i < n:
        c = sql_text[i]
        if c == "'" and not in_double and not in_backtick:
            if in_single and i + 1 < n and sql_text[i+1] == "'":
                current.append("''")
                i += 2
                continue
            in_single = not in_single
            current.append(c)
        elif c == '"' and not in_single and not in_backtick:
            in_double = not in_double
            current.append(c)
        elif c == '`' and not in_single and not in_double:
            in_backtick = not in_backtick
            current.append(c)
        elif c == '-' and i + 1 < n and sql_text[i+1] == '-' and not in_single and not in_double and not in_backtick:
            while i < n and sql_text[i] != '\n':
                i += 1
            continue
        elif c == ';' and not in_single and not in_double and not in_backtick:
            s = ''.join(current).strip()
            if s:
                statements.append(s)
            current = []
        else:
            current.append(c)
        i += 1
    s = ''.join(current).strip()
    if s:
        statements.append(s)
    return statements

def setup_database(dbname):
    print(f"\n--- Setting up MySQL database: [{dbname}] ---")
    root_conn = mysql.connector.connect(host="localhost", port=3307, user="root", password=DB_PASS)
    root_cur = root_conn.cursor()
    root_cur.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    root_cur.close()
    root_conn.close()

    conn = mysql.connector.connect(host="localhost", port=3307, user="root", password=DB_PASS, database=dbname, autocommit=True)
    cur = conn.cursor()

    base_dir = os.path.dirname(__file__)
    schema_file = os.path.join(base_dir, "schema.sql")
    seed_file = os.path.join(base_dir, "seed.sql")

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_stmts = split_sql(f.read())
    for s in schema_stmts:
        if s.upper().startswith("CREATE DATABASE") or s.upper().startswith("USE "):
            continue
        cur.execute(s)
    print("Schema created successfully!")

    with open(seed_file, "r", encoding="utf-8") as f:
        seed_stmts = split_sql(f.read())
    for s in seed_stmts:
        if s.upper().startswith("USE "):
            continue
        cur.execute(s)
    print("Seed data populated successfully!")

    cur.execute("SHOW TABLES;")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables ({len(tables)}): {', '.join(tables)}")

    cur.execute("SELECT COUNT(*) FROM students;")
    count = cur.fetchone()[0]
    print(f"Total students in {dbname}: {count}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    for db in DATABASES:
        setup_database(db)
    print("\nAll database setups finished successfully!")
