from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .database import init_db
from .engine import (
    AuthUser,
    auth_login,
    create_course,
    drop_course,
    enroll_course,
    format_course_line,
    get_student_schedule,
    list_courses,
    set_course_open,
)


class CourseApp:
    def __init__(self) -> None:
        init_db()
        self.root = tk.Tk()
        self.root.title("COMP2116 - Course Registration System")
        self.root.geometry("980x650")
        self.root.configure(bg="#0E1629")

        self.user: AuthUser | None = None
        self._build_login()

    def _clear(self) -> None:
        for w in self.root.winfo_children():
            w.destroy()

    def _build_login(self) -> None:
        self._clear()
        card = tk.Frame(self.root, bg="#16233F", bd=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=430, height=320)

        tk.Label(card, text="Course Registration Login", fg="#F1F5FF", bg="#16233F", font=("Helvetica", 18, "bold")).pack(pady=(24, 18))

        tk.Label(card, text="Username", fg="#C7D2FE", bg="#16233F", font=("Helvetica", 11)).pack(anchor="w", padx=44)
        self.ent_user = tk.Entry(card, width=32)
        self.ent_user.pack(padx=44, pady=(4, 10))

        tk.Label(card, text="Password", fg="#C7D2FE", bg="#16233F", font=("Helvetica", 11)).pack(anchor="w", padx=44)
        self.ent_pass = tk.Entry(card, width=32, show="*")
        self.ent_pass.pack(padx=44, pady=(4, 18))

        tk.Button(card, text="Login", width=16, command=self._login).pack()

        hint = (
            "Demo accounts:\n"
            "admin / admin123 (administrator)\n"
            "alice / alice123 (student)\n"
            "bob / bob123 (student)"
        )
        tk.Label(card, text=hint, fg="#BBD0FF", bg="#16233F", justify="left").pack(pady=(16, 0))

        self.root.bind("<Return>", lambda _e: self._login())

    def _login(self) -> None:
        u = self.ent_user.get().strip()
        p = self.ent_pass.get()
        user = auth_login(u, p)
        if not user:
            messagebox.showerror("Login failed", "Invalid username/password")
            return
        self.user = user
        self.root.unbind("<Return>")
        if user.role == "admin":
            self._build_admin_view()
        else:
            self._build_student_view()

    def _header(self, title: str) -> tk.Frame:
        top = tk.Frame(self.root, bg="#0E1629")
        top.pack(fill=tk.X, padx=16, pady=10)
        who = f"{self.user.username} ({self.user.role})" if self.user else "-"
        tk.Label(top, text=title, fg="#F8FAFF", bg="#0E1629", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT)
        tk.Label(top, text=f"Logged in: {who}", fg="#BFD2FF", bg="#0E1629").pack(side=tk.LEFT, padx=16)
        tk.Button(top, text="Logout", command=self._build_login).pack(side=tk.RIGHT)
        return top

    def _build_student_view(self) -> None:
        self._clear()
        self._header("Student Panel")

        body = tk.Frame(self.root, bg="#0E1629")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        left = tk.LabelFrame(body, text="All Courses", fg="#E7EEFF", bg="#142241")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.lst_courses = tk.Listbox(left, width=95, height=22)
        self.lst_courses.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        btns = tk.Frame(left, bg="#142241")
        btns.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(btns, text="Enroll Selected", command=self._student_enroll).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Refresh", command=self._refresh_student).pack(side=tk.LEFT, padx=4)

        right = tk.LabelFrame(body, text="My Schedule", fg="#E7EEFF", bg="#142241")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.lst_schedule = tk.Listbox(right, width=72, height=22)
        self.lst_schedule.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        b2 = tk.Frame(right, bg="#142241")
        b2.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(b2, text="Drop Selected", command=self._student_drop).pack(side=tk.LEFT, padx=4)

        self._refresh_student()

    def _refresh_student(self) -> None:
        self.lst_courses.delete(0, tk.END)
        for c in list_courses():
            self.lst_courses.insert(tk.END, format_course_line(c))

        self.lst_schedule.delete(0, tk.END)
        for c in get_student_schedule(self.user.user_id):
            line = f"[{c['id']}] {c['code']} | {c['title']} | {c['day_of_week']} {c['start_minute']//60:02d}:{c['start_minute']%60:02d}-{c['end_minute']//60:02d}:{c['end_minute']%60:02d}"
            self.lst_schedule.insert(tk.END, line)

    @staticmethod
    def _extract_id(line: str) -> int | None:
        if not line.startswith("["):
            return None
        try:
            return int(line.split("]", 1)[0][1:])
        except Exception:
            return None

    def _student_enroll(self) -> None:
        sel = self.lst_courses.curselection()
        if not sel:
            messagebox.showinfo("Enroll", "Select a course first.")
            return
        line = self.lst_courses.get(sel[0])
        cid = self._extract_id(line)
        if cid is None:
            messagebox.showerror("Enroll", "Invalid course selection.")
            return
        msg = enroll_course(self.user.user_id, cid)
        messagebox.showinfo("Enroll", msg)
        self._refresh_student()

    def _student_drop(self) -> None:
        sel = self.lst_schedule.curselection()
        if not sel:
            messagebox.showinfo("Drop", "Select a schedule entry first.")
            return
        line = self.lst_schedule.get(sel[0])
        cid = self._extract_id(line)
        if cid is None:
            messagebox.showerror("Drop", "Invalid schedule selection.")
            return
        msg = drop_course(self.user.user_id, cid)
        messagebox.showinfo("Drop", msg)
        self._refresh_student()

    def _build_admin_view(self) -> None:
        self._clear()
        self._header("Administrator Panel")

        body = tk.Frame(self.root, bg="#0E1629")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        top = tk.LabelFrame(body, text="Courses", fg="#E7EEFF", bg="#142241")
        top.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.lst_admin_courses = tk.Listbox(top, width=140, height=14)
        self.lst_admin_courses.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        b = tk.Frame(top, bg="#142241")
        b.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(b, text="Open Selected", command=lambda: self._admin_set_open(True)).pack(side=tk.LEFT, padx=4)
        tk.Button(b, text="Close Selected", command=lambda: self._admin_set_open(False)).pack(side=tk.LEFT, padx=4)
        tk.Button(b, text="Refresh", command=self._refresh_admin).pack(side=tk.LEFT, padx=4)

        bottom = tk.LabelFrame(body, text="Create Course", fg="#E7EEFF", bg="#142241")
        bottom.pack(fill=tk.X)

        form = tk.Frame(bottom, bg="#142241")
        form.pack(fill=tk.X, padx=8, pady=8)

        self.ent_code = tk.Entry(form, width=12)
        self.ent_title = tk.Entry(form, width=28)
        self.ent_day = tk.Entry(form, width=8)
        self.ent_start = tk.Entry(form, width=6)
        self.ent_end = tk.Entry(form, width=6)
        self.ent_cap = tk.Entry(form, width=6)

        labels = ["Code", "Title", "Day", "Start", "End", "Cap"]
        ents = [self.ent_code, self.ent_title, self.ent_day, self.ent_start, self.ent_end, self.ent_cap]
        for i, (lb, ent) in enumerate(zip(labels, ents)):
            tk.Label(form, text=lb, fg="#D5E4FF", bg="#142241").grid(row=0, column=i, padx=4, sticky="w")
            ent.grid(row=1, column=i, padx=4)

        tk.Button(form, text="Create", command=self._admin_create).grid(row=1, column=6, padx=10)
        tk.Label(bottom, text="Day use Mon/Tue/Wed/Thu/Fri | Start/End in hour (e.g. 9, 11)", fg="#A9C4FF", bg="#142241").pack(anchor="w", padx=8, pady=(0, 8))

        self._refresh_admin()

    def _refresh_admin(self) -> None:
        self.lst_admin_courses.delete(0, tk.END)
        for c in list_courses():
            self.lst_admin_courses.insert(tk.END, format_course_line(c))

    def _admin_set_open(self, is_open: bool) -> None:
        sel = self.lst_admin_courses.curselection()
        if not sel:
            messagebox.showinfo("Admin", "Select a course first.")
            return
        line = self.lst_admin_courses.get(sel[0])
        cid = self._extract_id(line)
        if cid is None:
            messagebox.showerror("Admin", "Invalid selection.")
            return
        msg = set_course_open(cid, is_open)
        messagebox.showinfo("Admin", msg)
        self._refresh_admin()

    def _admin_create(self) -> None:
        code = self.ent_code.get()
        title = self.ent_title.get()
        day = self.ent_day.get()
        try:
            s = int(self.ent_start.get())
            e = int(self.ent_end.get())
            cap = int(self.ent_cap.get())
        except Exception:
            messagebox.showerror("Create", "Start/End/Cap must be numbers.")
            return
        msg = create_course(code, title, day, s, e, cap)
        messagebox.showinfo("Create", msg)
        self._refresh_admin()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    CourseApp().run()


if __name__ == "__main__":
    main()
