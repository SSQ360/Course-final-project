from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "course_system.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin','student'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                start_minute INTEGER NOT NULL,
                end_minute INTEGER NOT NULL,
                capacity INTEGER NOT NULL,
                is_open INTEGER NOT NULL DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS prerequisites (
                course_id INTEGER NOT NULL,
                prereq_course_id INTEGER NOT NULL,
                PRIMARY KEY(course_id, prereq_course_id),
                FOREIGN KEY(course_id) REFERENCES courses(id),
                FOREIGN KEY(prereq_course_id) REFERENCES courses(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                UNIQUE(user_id, course_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS waitlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                queue_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, course_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
        """)
        # Lightweight migration for existing databases created before queue_order was introduced.
        cols = {row["name"] for row in c.execute("PRAGMA table_info(waitlists)").fetchall()}
        if "queue_order" not in cols:
            c.execute("ALTER TABLE waitlists ADD COLUMN queue_order INTEGER NOT NULL DEFAULT 0")
            c.execute(
                """
                WITH ranked AS (
                    SELECT id, ROW_NUMBER() OVER (PARTITION BY course_id ORDER BY created_at, id) AS rn
                    FROM waitlists
                )
                UPDATE waitlists
                SET queue_order = (SELECT rn FROM ranked WHERE ranked.id = waitlists.id)
                """
            )
        c.execute("""
            CREATE TABLE IF NOT EXISTS completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                UNIQUE(user_id, course_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
        """)

        c.execute("SELECT COUNT(*) as n FROM users")
        if c.fetchone()["n"] == 0:
            c.executemany(
                "INSERT INTO users(username, password, role) VALUES (?, ?, ?)",
                [
                    ("admin", "admin123", "admin"),
                    ("alice", "alice123", "student"),
                    ("bob", "bob123", "student"),
                ],
            )

        c.execute("SELECT COUNT(*) as n FROM courses")
        if c.fetchone()["n"] == 0:
            c.executemany(
                """
                INSERT INTO courses(code, title, day_of_week, start_minute, end_minute, capacity, is_open)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                [
                    ("COMP1001", "Programming Fundamentals", "Mon", 9 * 60, 11 * 60, 3),
                    ("COMP2002", "Data Structures", "Tue", 10 * 60, 12 * 60, 2),
                    ("COMP2116", "Software Engineering", "Wed", 14 * 60, 16 * 60, 2),
                    ("MATH1003", "Discrete Math", "Mon", 10 * 60, 12 * 60, 2),
                ],
            )

            c.execute("SELECT id, code FROM courses")
            ids = {row["code"]: row["id"] for row in c.fetchall()}
            c.execute(
                "INSERT OR IGNORE INTO prerequisites(course_id, prereq_course_id) VALUES (?, ?)",
                (ids["COMP2002"], ids["COMP1001"]),
            )
            c.execute(
                "INSERT OR IGNORE INTO prerequisites(course_id, prereq_course_id) VALUES (?, ?)",
                (ids["COMP2116"], ids["COMP2002"]),
            )

            c.execute("SELECT id FROM users WHERE username='alice'")
            alice = c.fetchone()["id"]
            c.execute(
                "INSERT OR IGNORE INTO completions(user_id, course_id) VALUES (?, ?)",
                (alice, ids["COMP1001"]),
            )
        conn.commit()
