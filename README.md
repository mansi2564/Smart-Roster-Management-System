# Smart Roster Management System

A browser-based application built to help operations managers manage employees, brands, processes, employee availability, and monthly work schedules.

## 1. Project Overview

The Smart Roster Management System automates monthly roster generation for multiple brands and operational processes. It considers employee assignments, weekly offs, approved leaves, comp-offs, public holidays, operating days, and minimum staffing requirements.

The application also provides conflict detection and manual employee reassignment to help managers handle scheduling changes.

## 2. Technology Stack

- **Programming Language:** Python
- **Web Framework:** Streamlit
- **Database:** SQLite
- **Data Processing:** Pandas
- **Visualizations:** Plotly

## 3. Features

- Employee management: Add, view, search, and deactivate employees.
- Brand and process management: Add brands and processes and configure operating rules.
- Pod management: Organize employees into operational pods.
- Employee assignments: Assign employees to brands and processes.
- Availability management: Configure weekly offs, leaves, comp-offs, and holidays.
- Monthly roster generation: Generate schedules based on configured rules and employee availability.
- Conflict detection: Identify staffing shortages, double bookings, weekly-off violations, leave violations, and other scheduling issues.
- Manual reassignment: Allow managers to replace an assigned employee with another eligible employee.
- Dashboard: Display employee, brand, process, assignment, roster, and conflict information.
- CSV export: Download roster information for further use.

## 4. Sample Dataset

The application uses fictional sample data to demonstrate realistic operational scenarios.

| Data | Count |
|---|---:|
| Employees | 50 |
| Operational pods | 5 |
| Brands | 35 |
| Processes | 5 |
| Employee assignments | 77 |

The sample data includes 28 single-resource brands and 7 multi-resource brands, representing approximately an 80:20 distribution.

## 5. Project Structure

```text
Smart Roster Management System/
│
├── app.py
├── database.py
├── sample_data.py
├── scheduler.py
├── validator.py
├── requirements.txt
├── README.md
│
├── database/
│   └── roster.db
│
└── pages/
    ├── Employees.py
    ├── Brands.py
    ├── Assignment.py
    ├── Availability.py
    ├── MonthlyRoster.py
    └── Conflicts.py
```

## 6. Installation and Setup

### Prerequisites

- Python 3.10 or later
- pip

### Step 1: Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd "Smart Roster Management System"
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Initialize sample data

Run the sample data script only when creating or resetting the sample database:

```bash
python sample_data.py
```

**Note:** Running this script again resets the sample data.

### Step 4: Run the application

```bash
streamlit run app.py
```

The application will open in your browser.

## 7. Scheduling Approach

The scheduling engine follows a rule-based approach.

1. Retrieve active employees, assignments, brand-process rules, weekly offs, approved leaves, and holidays.
2. Identify the operating days and staffing requirements for each brand and process.
3. Filter employees who are eligible to work on each date.
4. Prioritize scheduling tasks with fewer eligible employees.
5. Allocate employees while considering their existing monthly workload.
6. Prevent an employee from receiving more than one roster assignment on the same date.
7. Record staffing shortages when the available employees cannot satisfy the required coverage.

The generated roster can be reviewed and validated separately.

## 8. Tell Us How You Think

### 1. How did you model employees, brands, processes, pods, and their relationships?

I used a relational database with separate tables for employees, brands, processes, pods, assignments, and brand-process rules.

Employees belong to operational pods and can be assigned to one or more brands and processes. The assignments table connects employees with brands and processes. This structure avoids unnecessary duplication and makes it easier to add or modify assignments.

### 2. How does your system generate a roster and determine whether it satisfies the required constraints?

The scheduler uses a rule-based algorithm. It checks operating days, employee assignments, weekly offs, approved leaves, holidays, and minimum staffing requirements.

It prioritizes tasks with fewer eligible employees and distributes assignments based on monthly workload. A separate validation module checks the generated roster for scheduling violations and coverage shortages.

### 3. How did you handle the difference between single-resource brands and brands with multiple employees?

The system uses employee-to-brand-process assignments rather than assuming that every brand has the same number of employees.

A single-resource brand can have one employee assigned across its configured processes, while multi-resource brands can have separate employees for different processes or multiple employees assigned to the same process.

### 4. What happens when an employee manages all processes for a brand but is unavailable on a required working day?

The scheduler excludes employees who are on an approved leave or weekly off. If no eligible assigned employee is available, the system records a minimum staffing shortage.

The manager can review the conflict and use manual reassignment when another eligible employee is available.

### 5. How does your system handle conflicting requirements or insufficient staffing?

The system prioritizes configured operating rules and employee availability. It prevents double booking and checks weekly-off, leave, holiday, and non-operating-day violations.

If the required staffing cannot be achieved, the system records the shortage instead of silently treating the roster as fully covered. The manager can review these issues on the conflict detection page.

### 6. Which parts of the process did you automate, and which did you leave under human control? Why?

Monthly roster generation and conflict detection are automated to reduce repetitive manual work.

Employee management, assignment configuration, availability updates, operating-rule changes, and manual reassignment remain under manager control. This provides flexibility because operational requirements can change.

### 7. If the company doubled its team and brand count, what would you change about your solution?

I would consider migrating from SQLite to PostgreSQL, improving database indexing, optimizing scheduling queries, and introducing role-based access control.

I would also improve the scheduling algorithm to support larger teams, more complex constraints, and scalable deployment.

### 8. If you had one additional week to work on this, what would you improve first?

I would first improve the scheduling algorithm to reduce staffing shortages and distribute workload more fairly. I would also add more detailed pod-wise, brand-wise, process-wise, and employee-wise roster views, followed by a roster approval workflow.

## 9. Future Improvements

- Advanced workload balancing and fair weekly-off distribution.
- More detailed roster views for different stakeholders.
- Automatic revalidation after availability changes.
- Backup employee recommendations.
- Role-based access and approval workflows.
- Excel export and notifications.

## 10. Author

**Developed as part of the DataStraw Tech Internship Assessment.**