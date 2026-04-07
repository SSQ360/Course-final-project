# COMP2116 Final Project — Course Registration System (Pilot)

This repository provides a **new software system** (non-game): a Course Registration System with student and administrator roles, course enrollment/drop, timetable conflict checks, capacity limits, prerequisite validation, and SQLite persistence.

## Graphical Abstract

```text
+-------------------+      +---------------------+      +-----------------------+
| Tkinter Login UI  | ---> | Role-based Panel    | ---> | Student/Admin Actions |
| (admin/student)   |      | (Student / Admin)   |      | enroll/drop/open/close|
+-------------------+      +---------------------+      +-----------------------+
          |                              |                           |
          v                              v                           v
   SQLite users table         Rule Engine (conflict,       SQLite courses/enrollments/
                              capacity, prerequisites)      prerequisites/completions
```

## 1) Purpose of the Software

### Software type
- Education / administrative information system

### Development process applied
- **Agile (iterative incremental)**

### Why Agile (vs Waterfall)
- Rules and UX (e.g., enrollment conflict messages) are easier to refine in short iterations with immediate testing.
- Student/admin features can be delivered incrementally while keeping a runnable pilot at all times.

### Possible usage / target market
- Small school departments for pilot-level course enrollment workflows
- Classroom software engineering demonstrations

## 2) Software Development Plan

### Development process
1. Iteration 1: data model and SQLite schema
2. Iteration 2: authentication + course listing
3. Iteration 3: enrollment/drop with rules (capacity/conflict/prerequisite)
4. Iteration 4: admin controls + documentation and demo prep

### Members (roles, responsibilities, portion)
> Replace placeholders before submission.

| Member | Role | Responsibilities | Portion |
|---|---|---|---|
| TO_BE_FILLED_A | PM/Analyst | requirement analysis, README/report writing | 35% |
| TO_BE_FILLED_B | Developer | database, rule engine, Tkinter UI | 45% |
| TO_BE_FILLED_C | QA/Demo | testing, scenario verification, video recording | 20% |

### Schedule
| Week | Planned work | Status |
|---|---|---|
| Week 1 | architecture + database schema | Done |
| Week 2 | student panel + enrollment rules | Done |
| Week 3 | admin panel + course management | Done |
| Week 4 | docs/video/submission packaging | In progress |

### Algorithm (core rules)
- **Time conflict**: reject enrollment when same day and time interval overlaps an existing schedule.
- **Capacity check**: reject enrollment when `enrolled >= capacity`.
- **Prerequisite check**: reject enrollment if required completed courses are missing.

### Current status
- Login with role-based views (`admin`, `student`)
- Student functions: view all courses, enroll, drop, view own schedule
- Admin functions: open/close course, create new course
- Rule engine: capacity, conflict, prerequisite validation
- SQLite persistence with seed data

### Future plan
- Password hashing and stronger account management
- Export timetable/report to CSV
- Web version (Flask/FastAPI) and API layer

## 3) Demo (Video URL)
- Demo URL: `TO_BE_FILLED_BEFORE_SUBMISSION`
- Recommended duration: 10–15 minutes

Demo should include:
- how to start the software
- student login and enrollment scenarios
- admin login and course open/close/create operations

## 4) Environment for Development and Running

### Programming language
- Python 3.10+

### Minimum requirements
- CPU: Any modern processor
- RAM: 2 GB+
- OS: macOS/Windows/Linux desktop with Tk support

### Required packages
- No third-party packages are required for core features
- Uses Python standard library only (`tkinter`, `sqlite3`, `pathlib`, etc.)

## 5) How to Run

From project root:

```bash
python3 -m src.app
```

Demo accounts:
- `admin / admin123`
- `alice / alice123`
- `bob / bob123`

## 6) Declaration

This project is an original academic software prototype.

Third-party/open-source usage:
- Python Standard Library modules only
- No external proprietary datasets/assets included

## 7) GitHub Submission Checklist

- [ ] Source code uploaded to GitHub
- [ ] README completed with real member names
- [ ] Demo video URL added
- [ ] Contribution form prepared for Canvas
- [ ] GitHub link submitted in Canvas
