from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .database import get_conn


@dataclass
class AuthUser:
    user_id: int
    username: str
    role: str


def _time_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _fmt_minute(m: int) -> str:
    h = m // 60
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


def auth_login(username: str, password: str) -> AuthUser | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role FROM users WHERE username=? AND password=?",
            (username.strip(), password),
        ).fetchone()
        if not row:
            return None
        return AuthUser(user_id=row["id"], username=row["username"], role=row["role"])


def list_courses() -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.*,
                   (SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.id) AS enrolled,
                   (SELECT COUNT(*) FROM waitlists w WHERE w.course_id=c.id) AS waitlisted
            FROM courses c
            ORDER BY c.code
            """
        ).fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "code": r["code"],
                    "title": r["title"],
                    "day": r["day_of_week"],
                    "start": r["start_minute"],
                    "end": r["end_minute"],
                    "time_str": f"{_fmt_minute(r['start_minute'])}-{_fmt_minute(r['end_minute'])}",
                    "capacity": r["capacity"],
                    "enrolled": r["enrolled"],
                    "waitlisted": r["waitlisted"],
                    "is_open": bool(r["is_open"]),
                }
            )
        return out


def get_student_schedule(user_id: int) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.*
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.user_id=?
            ORDER BY c.day_of_week, c.start_minute, c.code
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _check_prerequisites(user_id: int, course_id: int) -> Tuple[bool, str]:
    with get_conn() as conn:
        prereq_rows = conn.execute(
            """
            SELECT p.prereq_course_id, c.code
            FROM prerequisites p
            JOIN courses c ON c.id = p.prereq_course_id
            WHERE p.course_id=?
            """,
            (course_id,),
        ).fetchall()
        if not prereq_rows:
            return True, ""

        for r in prereq_rows:
            ok = conn.execute(
                "SELECT 1 FROM completions WHERE user_id=? AND course_id=?",
                (user_id, r["prereq_course_id"]),
            ).fetchone()
            if not ok:
                return False, f"Missing prerequisite: {r['code']}"
        return True, ""


def _check_time_conflict(user_id: int, course: dict) -> Tuple[bool, str]:
    schedule = get_student_schedule(user_id)
    for c in schedule:
        if c["day_of_week"] != course["day_of_week"]:
            continue
        if _time_overlap(c["start_minute"], c["end_minute"], course["start_minute"], course["end_minute"]):
            return False, f"Time conflict with {c['code']} ({_fmt_minute(c['start_minute'])}-{_fmt_minute(c['end_minute'])})"
    return True, ""


def _can_enroll_now(user_id: int, course_id: int) -> Tuple[bool, str]:
    with get_conn() as conn:
        course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not course:
            return False, "Course not found."
        if not bool(course["is_open"]):
            return False, "Course is closed by admin."
        ok_pr, msg_pr = _check_prerequisites(user_id, course_id)
        if not ok_pr:
            return False, msg_pr
        ok_tc, msg_tc = _check_time_conflict(user_id, dict(course))
        if not ok_tc:
            return False, msg_tc
        return True, ""


def enroll_course(user_id: int, course_id: int) -> str:
    with get_conn() as conn:
        course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not course:
            return "Course not found."

        exists = conn.execute(
            "SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        ).fetchone()
        if exists:
            return "Already enrolled."

        if not bool(course["is_open"]):
            return "Course is closed by admin."

        enrolled = conn.execute(
            "SELECT COUNT(*) AS n FROM enrollments WHERE course_id=?",
            (course_id,),
        ).fetchone()["n"]
        if enrolled >= course["capacity"]:
            return "Course is full. You can join waitlist."

        ok, msg = _can_enroll_now(user_id, course_id)
        if not ok:
            return msg

        conn.execute(
            "INSERT INTO enrollments(user_id, course_id) VALUES (?, ?)",
            (user_id, course_id),
        )
        # Remove existing waitlist entry if user was queued before.
        conn.execute(
            "DELETE FROM waitlists WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        )
        conn.commit()
        return "Enrolled successfully."


def drop_course(user_id: int, course_id: int) -> str:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM enrollments WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        )
        if cur.rowcount == 0:
            conn.commit()
            return "Not enrolled in this course."
        promoted = _promote_waitlist_locked(conn, course_id)
        conn.commit()
        if promoted:
            return f"Dropped successfully. Waitlist promoted: {promoted}"
        return "Dropped successfully."


def join_waitlist(user_id: int, course_id: int) -> str:
    with get_conn() as conn:
        course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not course:
            return "Course not found."
        if not bool(course["is_open"]):
            return "Course is closed by admin."

        exists_enroll = conn.execute(
            "SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        ).fetchone()
        if exists_enroll:
            return "Already enrolled. No need to waitlist."

        exists_wait = conn.execute(
            "SELECT 1 FROM waitlists WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        ).fetchone()
        if exists_wait:
            return "Already in waitlist."

        ok, msg = _can_enroll_now(user_id, course_id)
        if not ok:
            return msg

        # If seat is available now, enroll directly.
        enrolled = conn.execute(
            "SELECT COUNT(*) AS n FROM enrollments WHERE course_id=?",
            (course_id,),
        ).fetchone()["n"]
        if enrolled < course["capacity"]:
            conn.execute(
                "INSERT INTO enrollments(user_id, course_id) VALUES (?, ?)",
                (user_id, course_id),
            )
            conn.commit()
            return "Seat available now. Enrolled directly."

        conn.execute(
            "INSERT INTO waitlists(user_id, course_id, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (user_id, course_id),
        )
        conn.commit()
        return "Joined waitlist."


def leave_waitlist(user_id: int, course_id: int) -> str:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM waitlists WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return "You are not in waitlist for this course."
        return "Removed from waitlist."


def list_waitlist_for_student(user_id: int) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT w.course_id, c.code, c.title, c.day_of_week, c.start_minute, c.end_minute, w.created_at,
                   (
                    SELECT COUNT(*) + 1
                    FROM waitlists w2
                    WHERE w2.course_id = w.course_id
                      AND (w2.created_at < w.created_at OR (w2.created_at = w.created_at AND w2.id <= w.id))
                   ) AS position
            FROM waitlists w
            JOIN courses c ON c.id = w.course_id
            WHERE w.user_id=?
            ORDER BY w.created_at
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_waitlist_for_course(course_id: int) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT w.id, u.username, w.created_at
            FROM waitlists w
            JOIN users u ON u.id = w.user_id
            WHERE w.course_id=?
            ORDER BY w.created_at, w.id
            """,
            (course_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _promote_waitlist_locked(conn, course_id: int) -> str:
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if not course or not bool(course["is_open"]):
        return ""

    enrolled = conn.execute(
        "SELECT COUNT(*) AS n FROM enrollments WHERE course_id=?",
        (course_id,),
    ).fetchone()["n"]
    if enrolled >= course["capacity"]:
        return ""

    rows = conn.execute(
        """
        SELECT w.id, w.user_id, u.username
        FROM waitlists w
        JOIN users u ON u.id = w.user_id
        WHERE w.course_id=?
        ORDER BY w.created_at, w.id
        """,
        (course_id,),
    ).fetchall()

    for r in rows:
        user_id = r["user_id"]
        ok, _msg = _can_enroll_now(user_id, course_id)
        if not ok:
            continue
        already = conn.execute(
            "SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        ).fetchone()
        conn.execute("DELETE FROM waitlists WHERE id=?", (r["id"],))
        if not already:
            conn.execute(
                "INSERT INTO enrollments(user_id, course_id) VALUES (?, ?)",
                (user_id, course_id),
            )
            return r["username"]
    return ""


def set_course_open(course_id: int, is_open: bool) -> str:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE courses SET is_open=? WHERE id=?",
            (1 if is_open else 0, course_id),
        )
        promoted = ""
        if is_open and cur.rowcount > 0:
            promoted = _promote_waitlist_locked(conn, course_id)
        conn.commit()
        if cur.rowcount == 0:
            return "Course not found."
        if promoted:
            return f"Course status updated. Waitlist promoted: {promoted}"
        return "Course status updated."


def create_course(code: str, title: str, day: str, start_hour: int, end_hour: int, capacity: int) -> str:
    day = day.strip().title()
    if day not in {"Mon", "Tue", "Wed", "Thu", "Fri"}:
        return "Day must be Mon/Tue/Wed/Thu/Fri."
    if start_hour < 8 or end_hour > 21 or start_hour >= end_hour:
        return "Time range must be valid (8..21, start < end)."
    if capacity < 1 or capacity > 200:
        return "Capacity must be in 1..200."

    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO courses(code, title, day_of_week, start_minute, end_minute, capacity, is_open)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (code.strip().upper(), title.strip(), day, start_hour * 60, end_hour * 60, capacity),
            )
            conn.commit()
            return "Course created."
        except Exception:
            return "Create failed (check duplicate code)."


def admin_stats() -> Dict[str, int]:
    with get_conn() as conn:
        total_courses = conn.execute("SELECT COUNT(*) AS n FROM courses").fetchone()["n"]
        open_courses = conn.execute("SELECT COUNT(*) AS n FROM courses WHERE is_open=1").fetchone()["n"]
        total_enrollments = conn.execute("SELECT COUNT(*) AS n FROM enrollments").fetchone()["n"]
        total_waitlists = conn.execute("SELECT COUNT(*) AS n FROM waitlists").fetchone()["n"]
        return {
            "total_courses": int(total_courses),
            "open_courses": int(open_courses),
            "total_enrollments": int(total_enrollments),
            "total_waitlists": int(total_waitlists),
        }


def format_course_line(c: dict) -> str:
    st = c["time_str"] if "time_str" in c else f"{_fmt_minute(c['start_minute'])}-{_fmt_minute(c['end_minute'])}"
    status = "OPEN" if c.get("is_open", 1) else "CLOSED"
    enrolled = c.get("enrolled", 0)
    waitlisted = c.get("waitlisted", 0)
    cap = c.get("capacity", 0)
    return f"[{c['id']}] {c['code']} | {c['title']} | {c['day']} {st} | {enrolled}/{cap} | wait {waitlisted} | {status}"
