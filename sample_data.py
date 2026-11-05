
import json
from database import create_tables, get_connection


def seed_data():

    # Make sure database tables exist
    create_tables()

    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing sample data before reseeding
    tables = [
        "roster_entries",
        "leaves",
        "employee_weekly_offs",
        "assignments",
        "brand_process_rules",
        "holidays",
        "employees",
        "brands",
        "processes",
        "pods"
    ]

    for table in tables:
        cursor.execute(f"DELETE FROM {table}")

    # ---------------------------------
    # 1. CREATE OPERATIONAL PODS
    # ---------------------------------

    pod_names = [
        "Alpha Pod",
        "Beta Pod",
        "Gamma Pod",
        "Delta Pod",
        "Omega Pod"
    ]

    pod_ids = {}

    for pod in pod_names:
        cursor.execute(
            "INSERT INTO pods (pod_name) VALUES (?)",
            (pod,)
        )
        pod_ids[pod] = cursor.lastrowid

    # ---------------------------------
    # 2. CREATE 50 EMPLOYEES
    # ---------------------------------

    employee_names = [
        "Aarav Sharma", "Ananya Patel", "Rohan Mehta",
        "Priya Shah", "Arjun Verma", "Sneha Joshi",
        "Kabir Nair", "Ishita Rao", "Vivaan Gupta",
        "Neha Kulkarni", "Aditya Desai", "Kavya Iyer",
        "Rahul Mishra", "Diya Kapoor", "Ayaan Khan",
        "Meera Reddy", "Dev Malhotra", "Riya Sinha",
        "Karan Bhat", "Aditi Menon", "Siddharth Jain",
        "Pooja Nair", "Varun Pillai", "Tanya Bose",
        "Nikhil Roy", "Shreya Das", "Manav Arora",
        "Ira Chawla", "Yash Thakur", "Sana Sheikh",
        "Omkar Patil", "Mira Ghosh", "Atharva More",
        "Simran Kaur", "Harsh Vora", "Anika Sen",
        "Krish Shah", "Tanvi Rao", "Reyansh Gupta",
        "Avni Joshi", "Dhruv Nair", "Nisha Verma",
        "Samar Kapoor", "Esha Mehta", "Ritvik Das",
        "Myra Kulkarni", "Neil Fernandes", "Sara Khan",
        "Aarohi Iyer", "Ishaan Desai"
    ]

    employee_ids = []

    for i, name in enumerate(employee_names):

        # 10 employees in each pod
        pod_index = i // 10
        pod = pod_names[pod_index]
        pod_id = pod_ids[pod]

        # First employee in each pod is the pod lead
        role = "Pod Lead" if i % 10 == 0 else "Employee"

        email = f"employee{i + 1}@datastraw-demo.com"

        cursor.execute("""
            INSERT INTO employees
            (employee_name, email, pod_id, role)
            VALUES (?, ?, ?, ?)
        """, (name, email, pod_id, role))

        employee_ids.append(cursor.lastrowid)

    # Assign pod leads after employees are created
    for i, pod in enumerate(pod_names):

        lead_id = employee_ids[i * 10]

        cursor.execute("""
            UPDATE pods
            SET pod_lead_id = ?
            WHERE pod_id = ?
        """, (lead_id, pod_ids[pod]))

    # ---------------------------------
    # 3. CREATE 35 BRANDS
    # ---------------------------------

    brand_names = [
        "UrbanNest", "GlowCart", "PureLiving",
        "StyleSphere", "FreshBasket", "NovaWear",
        "TrendTrove", "DailyHarvest", "LuxeLane",
        "FitFusion", "HomeBliss", "SkinStory",
        "TechNest", "PetPalace", "FoodCloud",
        "CraftCorner", "EcoEssentials", "ModernMuse",
        "SmartChoice", "NatureGlow", "UrbanThreads",
        "EliteLiving", "QuickMart", "DreamDecor",
        "WellnessHub", "PrimeStyle", "FreshAura",
        "TheDailyCo", "BrightBasket", "VelvetVibe",
        "GreenRoot", "NextGenStore", "CozyCorner",
        "VitalVogue", "HappyHomes"
    ]

    brand_ids = []

    for brand in brand_names:

        cursor.execute("""
            INSERT INTO brands (brand_name, description)
            VALUES (?, ?)
        """, (brand, "Sample D2C client brand"))

        brand_ids.append(cursor.lastrowid)

    # ---------------------------------
    # 4. CREATE PROCESSES
    # ---------------------------------

    process_names = [
        "Customer Support",
        "Abandoned Cart Conversion",
        "Retention",
        "Non-Delivery Report",
        "Other Operations"
    ]

    process_ids = {}

    for process in process_names:

        cursor.execute("""
            INSERT INTO processes (process_name)
            VALUES (?)
        """, (process,))

        process_ids[process] = cursor.lastrowid

    # Process operating calendars
    process_days = {
        "Customer Support": [0, 1, 2, 3, 4, 5, 6],
        "Abandoned Cart Conversion": [0, 1, 2, 3, 4, 5],
        "Retention": [0, 1, 2, 3, 4],
        "Non-Delivery Report": [0, 1, 2, 3, 4, 5, 6],
        "Other Operations": [0, 1, 2, 3, 4, 5]
    }

    # ---------------------------------
    # 5. CREATE BRAND PROCESS RULES
    # ---------------------------------

    secondary_processes = [
        "Abandoned Cart Conversion",
        "Retention",
        "Non-Delivery Report",
        "Other Operations"
    ]

    # First 28 brands: single dedicated employee
    for i in range(28):

        brand_id = brand_ids[i]
        employee_id = employee_ids[i]

        # Each brand has two processes
        selected_processes = [
            "Customer Support",
            secondary_processes[i % 4]
        ]

        for process in selected_processes:

            process_id = process_ids[process]

            cursor.execute("""
                INSERT INTO brand_process_rules
                (brand_id, process_id, operating_days, min_staffing)
                VALUES (?, ?, ?, ?)
            """, (
                brand_id,
                process_id,
                json.dumps(process_days[process]),
                1
            ))

            # Same employee handles all processes
            # assigned to this brand
            cursor.execute("""
                INSERT INTO assignments
                (employee_id, brand_id, process_id)
                VALUES (?, ?, ?)
            """, (employee_id, brand_id, process_id))

    # ---------------------------------
    # 6. MULTI-RESOURCE BRANDS
    # ---------------------------------

    multi_processes = [
        ("Customer Support", "Retention"),
        ("Abandoned Cart Conversion", "Customer Support"),
        ("Retention", "Non-Delivery Report"),
        ("Non-Delivery Report", "Customer Support"),
        ("Other Operations", "Retention"),
        ("Customer Support", "Non-Delivery Report"),
        ("Abandoned Cart Conversion", "Other Operations")
    ]

    # Remaining 7 brands have 3 employees each
    for i in range(7):

        brand_index = 28 + i
        brand_id = brand_ids[brand_index]

        first_process, second_process = multi_processes[i]

        first_process_id = process_ids[first_process]
        second_process_id = process_ids[second_process]

        # First process needs two employees
        cursor.execute("""
            INSERT INTO brand_process_rules
            (brand_id, process_id, operating_days, min_staffing)
            VALUES (?, ?, ?, ?)
        """, (
            brand_id,
            first_process_id,
            json.dumps(process_days[first_process]),
            2
        ))

        # Second process needs one employee
        cursor.execute("""
            INSERT INTO brand_process_rules
            (brand_id, process_id, operating_days, min_staffing)
            VALUES (?, ?, ?, ?)
        """, (
            brand_id,
            second_process_id,
            json.dumps(process_days[second_process]),
            1
        ))

        # Three employees allocated to each brand
        start = 28 + (i * 3)

        assigned_employees = employee_ids[start:start + 3]

        for employee_id in assigned_employees[:2]:

            cursor.execute("""
                INSERT INTO assignments
                (employee_id, brand_id, process_id)
                VALUES (?, ?, ?)
            """, (employee_id, brand_id, first_process_id))

        cursor.execute("""
            INSERT INTO assignments
            (employee_id, brand_id, process_id)
            VALUES (?, ?, ?)
        """, (assigned_employees[2], brand_id, second_process_id))

    # Employee 50 remains available as a flexible reserve.
    # They can be assigned to a brand through the application.

    # ---------------------------------
    # 7. EMPLOYEE WEEKLY OFFS
    # ---------------------------------

    for i, employee_id in enumerate(employee_ids):

        # Spread weekly offs across all 7 weekdays
        weekday = i % 7

        cursor.execute("""
            INSERT INTO employee_weekly_offs
            (employee_id, weekday)
            VALUES (?, ?)
        """, (employee_id, weekday))

    # ---------------------------------
    # 8. SAMPLE LEAVES
    # ---------------------------------

    sample_leaves = [
        (employee_ids[2], "2026-11-10", "Planned Leave", "Approved"),
        (employee_ids[7], "2026-11-12", "Planned Leave", "Approved"),
        (employee_ids[15], "2026-11-16", "Comp-Off", "Approved"),
        (employee_ids[22], "2026-11-18", "Planned Leave", "Pending"),
        (employee_ids[30], "2026-11-20", "Planned Leave", "Approved")
    ]

    cursor.executemany("""
        INSERT INTO leaves
        (employee_id, leave_date, leave_type, status)
        VALUES (?, ?, ?, ?)
    """, sample_leaves)

    # ---------------------------------
    # 9. SAMPLE PUBLIC HOLIDAYS
    # ---------------------------------

    holidays = [
        ("2026-01-26", "Republic Day"),
        ("2026-08-15", "Independence Day"),
        ("2026-10-02", "Gandhi Jayanti"),
        ("2026-11-14", "Sample Regional Holiday")
    ]

    cursor.executemany("""
        INSERT INTO holidays
        (holiday_date, holiday_name)
        VALUES (?, ?)
    """, holidays)

    conn.commit()
    conn.close()

    print("\nSample data generated successfully!")
    print("Employees: 50")
    print("Brands: 35")
    print("Single-resource brands: 28")
    print("Multi-resource brands: 7")
    print("Operational pods: 5")
    print("Processes: 5")
    print("Assigned employees: 49")
    print("Flexible reserve employees: 1")


if __name__ == "__main__":
    seed_data()
