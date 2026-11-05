
import sqlite3
import os

# Database location
DB_FOLDER = "database"
DB_PATH = os.path.join(DB_FOLDER, "roster.db")


def get_connection():
    os.makedirs(DB_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Pods table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pods (
            pod_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pod_name TEXT NOT NULL UNIQUE,
            pod_lead_id INTEGER
        )
    """)

    # 2. Employees table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            email TEXT UNIQUE,
            pod_id INTEGER,
            role TEXT DEFAULT 'Employee',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (pod_id) REFERENCES pods(pod_id)
        )
    """)

    # 3. Brands table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    # 4. Processes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processes (
            process_id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_name TEXT NOT NULL UNIQUE
        )
    """)

    # 5. Brand process operating rules
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brand_process_rules (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            operating_days TEXT NOT NULL,
            min_staffing INTEGER DEFAULT 1,
            FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
            FOREIGN KEY (process_id) REFERENCES processes(process_id),
            UNIQUE (brand_id, process_id)
        )
    """)

    # 6. Employee assignments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
            FOREIGN KEY (process_id) REFERENCES processes(process_id),
            UNIQUE (employee_id, brand_id, process_id)
        )
    """)

    # 7. Employee weekly offs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_weekly_offs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            UNIQUE (employee_id, weekday),
            CHECK (weekday BETWEEN 0 AND 6)
        )
    """)

    # 8. Planned leaves and comp-offs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leaves (
            leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            leave_date TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            status TEXT DEFAULT 'Approved',
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            UNIQUE (employee_id, leave_date)
        )
    """)

    # 9. Public holidays
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            holiday_id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday_date TEXT NOT NULL UNIQUE,
            holiday_name TEXT NOT NULL
        )
    """)

    # 10. Generated roster entries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roster_entries (
            roster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            roster_date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id),
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
            FOREIGN KEY (process_id) REFERENCES processes(process_id),
            UNIQUE (assignment_id, roster_date)
        )
    """)

    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roster_conflicts (
            conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
            roster_date TEXT NOT NULL,
            brand_id INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            required_staff INTEGER NOT NULL,
            assigned_staff INTEGER NOT NULL,
            issue TEXT NOT NULL,
            FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
            FOREIGN KEY (process_id) REFERENCES processes(process_id),
            UNIQUE (roster_date, brand_id, process_id)
        )
    """)


    
# Add new scheduling rule columns if they do not exist

    cursor.execute("PRAGMA table_info(brand_process_rules)")
    existing_columns = [
        column[1] for column in cursor.fetchall()
    ]

    if "holiday_policy" not in existing_columns:
        cursor.execute("""
            ALTER TABLE brand_process_rules
            ADD COLUMN holiday_policy TEXT NOT NULL DEFAULT 'OFF'
        """)

    if "daily_staffing" not in existing_columns:
        cursor.execute("""
            ALTER TABLE brand_process_rules
            ADD COLUMN daily_staffing TEXT NOT NULL DEFAULT '{}'
        """)




    conn.commit()
    conn.close()

    print("Database and tables created successfully!")


if __name__ == "__main__":
    create_tables()
