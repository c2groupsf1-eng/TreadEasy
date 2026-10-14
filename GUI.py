import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta, time

DB_FILE = "treadeasy.db"
OPEN_HOUR = 7
CLOSE_HOUR = 22
TREADMILLS = 5
GRID_MIN = 5
MAX_LEN = 45
MAX_PER_DAY = 2
MIN_LEAD_H = 3
MAX_LEAD_H = 24
REPORTS_TO_SUSPEND = 3
SUSPEND_DAYS = 7

# --- COLOR PALETTE (Modern Slate Theme) ---
COLOR_BG = "#f8fafc"          # Light Slate background
COLOR_SIDEBAR = "#0f172a"     # Dark Navy sidebar
COLOR_CARD = "#ffffff"        # Pure white card container
COLOR_PRIMARY = "#2563eb"     # Royal Blue accent
COLOR_TEXT_MAIN = "#1e293b"   # Dark slate text
COLOR_TEXT_MUTED = "#64748b"  # Muted gray text
COLOR_SIDEBAR_TEXT = "#f1f5f9"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            suspended_until TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            treadmill_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id TEXT NOT NULL,
            reported_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(reporter_id, reported_id)
        )
    """)
    conn.commit()
    conn.close()


class TreadEasyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TreadEasy — Gym Management System")
        self.geometry("850x550")
        self.configure(bg=COLOR_BG)

        init_db()
        self.current_user = None

        self.apply_custom_styles()
        self.show_auth_frame()

    def apply_custom_styles(self):
        """Configures the Tkinter ttk Style Engine to simulate web styling."""
        style = ttk.Style()
        style.theme_use("clam")

        # Global Font Settings
        FONT_FAMILY = "Segoe UI" if tk.TkVersion >= 8.6 else "Helvetica"

        # Frame styles
        style.configure("Main.TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_CARD, relief="flat", borderwidth=1)
        style.configure("Sidebar.TFrame", background=COLOR_SIDEBAR)

        # Label styles
        style.configure("Title.TLabel", font=(FONT_FAMILY, 16, "bold"), foreground=COLOR_TEXT_MAIN, background=COLOR_CARD)
        style.configure("Header.TLabel", font=(FONT_FAMILY, 12, "bold"), foreground=COLOR_TEXT_MAIN, background=COLOR_CARD)
        style.configure("Body.TLabel", font=(FONT_FAMILY, 9), foreground=COLOR_TEXT_MAIN, background=COLOR_CARD)
        style.configure("Muted.TLabel", font=(FONT_FAMILY, 8), foreground=COLOR_TEXT_MUTED, background=COLOR_CARD)
        style.configure("SidebarTitle.TLabel", font=(FONT_FAMILY, 14, "bold"), foreground=COLOR_SIDEBAR_TEXT, background=COLOR_SIDEBAR)

        # Button styles
        style.configure("Primary.TButton", font=(FONT_FAMILY, 9, "bold"), background=COLOR_PRIMARY, foreground="#ffffff", borderwidth=0, focuscolor="none")
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

        style.configure("Nav.TButton", font=(FONT_FAMILY, 9), background=COLOR_SIDEBAR, foreground=COLOR_SIDEBAR_TEXT, borderwidth=0, anchor="w", padding=8)
        style.map("Nav.TButton", background=[("active", "#1e293b")])

        # Entry fields
        style.configure("TEntry", fieldbackground="#f1f5f9", borderwidth=1, padding=5)

        # Treeview (Tables)
        style.configure("Treeview", font=(FONT_FAMILY, 9), rowheight=28, background="#ffffff", fieldbackground="#ffffff", borderwidth=0)
        style.configure("Treeview.Heading", font=(FONT_FAMILY, 9, "bold"), background="#f1f5f9", foreground=COLOR_TEXT_MAIN, borderwidth=0)
        style.map("Treeview", background=[("selected", COLOR_PRIMARY)], foreground=[("selected", "#ffffff")])

    # --- AUTHENTICATION VIEW ---
    def show_auth_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

        main_frame = ttk.Frame(self, style="Main.TFrame")
        main_frame.pack(fill="both", expand=True)

        # Center Card
        card = ttk.Frame(main_frame, style="Card.TFrame", padding=30)
        card.place(relx=0.5, rely=0.5, anchor="center", width=380)

        ttk.Label(card, text="TreadEasy", style="Title.TLabel").pack(pady=(0, 5))
        ttk.Label(card, text="Sign in to manage treadmill bookings", style="Muted.TLabel").pack(pady=(0, 20))

        ttk.Label(card, text="User ID", style="Body.TLabel").pack(anchor="w", pady=(5, 2))
        user_entry = ttk.Entry(card)
        user_entry.pack(fill="x", pady=(0, 10))

        ttk.Label(card, text="Password", style="Body.TLabel").pack(anchor="w", pady=(5, 2))
        pass_entry = ttk.Entry(card, show="*")
        pass_entry.pack(fill="x", pady=(0, 15))

        def handle_login():
            user_id = user_entry.get().strip()
            password = pass_entry.get().strip()
            if not user_id or not password:
                messagebox.showwarning("Validation Error", "Please provide both User ID and Password.")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT password, suspended_until FROM users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            conn.close()

            if row is None or row[0] != password:
                messagebox.showerror("Auth Error", "Invalid user ID or password.")
                return

            if row[1] is not None and datetime.fromisoformat(row[1]) > datetime.now():
                messagebox.showerror("Suspended", f"Account suspended until {row[1]}")
                return

            self.current_user = user_id
            self.show_dashboard_layout()

        def handle_register():
            user_id = user_entry.get().strip()
            password = pass_entry.get().strip()
            if not user_id or not password:
                messagebox.showwarning("Validation Error", "User ID and Password cannot be empty.")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (user_id, password) VALUES (?, ?)", (user_id, password))
                conn.commit()
                messagebox.showinfo("Success", "Account created successfully!")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "That User ID is already taken.")
            finally:
                conn.close()

        ttk.Button(card, text="Log In", style="Primary.TButton", command=handle_login).pack(fill="x", pady=(5, 5))
        ttk.Button(card, text="Register New Account", command=handle_register).pack(fill="x")

    # --- DASHBOARD LAYOUT (Sidebar + Content Area) ---
    def show_dashboard_layout(self):
        for widget in self.winfo_children():
            widget.destroy()

        # Navigation Sidebar
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=200, padding=15)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="🏃 TreadEasy", style="SidebarTitle.TLabel").pack(anchor="w", pady=(10, 25))

        ttk.Button(sidebar, text="📌  Book Session", style="Nav.TButton", command=self.render_booking_view).pack(fill="x", pady=2)
        ttk.Button(sidebar, text="📋  My Bookings", style="Nav.TButton", command=self.render_sessions_view).pack(fill="x", pady=2)
        ttk.Button(sidebar, text="⚠️  Report User", style="Nav.TButton", command=self.render_report_view).pack(fill="x", pady=2)

        ttk.Button(sidebar, text="🚪  Log Out", style="Nav.TButton", command=self.show_auth_frame).pack(side="bottom", fill="x")

        # Main Workspace Container
        self.workspace = ttk.Frame(self, style="Main.TFrame", padding=25)
        self.workspace.pack(side="right", fill="both", expand=True)

        # Render Default View
        self.render_booking_view()

    def clear_workspace(self):
        for widget in self.workspace.winfo_children():
            widget.destroy()

    # --- VIEWS ---
    def render_booking_view(self):
        self.clear_workspace()

        card = ttk.Frame(self.workspace, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Book a Treadmill", style="Title.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(card, text="Hours: 07:00 – 22:00 | Max Duration: 45 Mins | 5-Minute Grid Steps", style="Muted.TLabel").pack(anchor="w", pady=(0, 20))

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(anchor="w", fill="x")

        ttk.Label(form, text="Start Time (e.g., 8:30 am):", style="Body.TLabel").grid(row=0, column=0, sticky="w", pady=8, padx=(0, 10))
        start_entry = ttk.Entry(form, width=25)
        start_entry.grid(row=0, column=1, pady=8)

        ttk.Label(form, text="End Time (e.g., 9:15 am):", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=8, padx=(0, 10))
        end_entry = ttk.Entry(form, width=25)
        end_entry.grid(row=1, column=1, pady=8)

        def submit_booking():
            now = datetime.now()
            try:
                start_t = datetime.strptime(start_entry.get().strip().upper(), "%I:%M %p").time()
                end_t = datetime.strptime(end_entry.get().strip().upper(), "%I:%M %p").time()
            except ValueError:
                messagebox.showerror("Error", "Invalid time format. Use format like '8:30 am'.")
                return

            start = datetime.combine(now.date(), start_t)
            if start <= now:
                start += timedelta(days=1)
            end = datetime.combine(start.date(), end_t)

            if end <= start or (end - start).total_seconds() / 60 > MAX_LEN:
                messagebox.showerror("Error", f"Sessions must end after start and be max {MAX_LEN} minutes.")
                return

            if start.minute % GRID_MIN != 0 or end.minute % GRID_MIN != 0:
                messagebox.showerror("Error", f"Times must align with {GRID_MIN}-minute intervals.")
                return

            if start.hour < OPEN_HOUR or end > datetime.combine(start.date(), time(CLOSE_HOUR, 0)):
                messagebox.showerror("Error", "Gym hours are 07:00 AM to 10:00 PM.")
                return

            if not (now + timedelta(hours=MIN_LEAD_H) <= start <= now + timedelta(hours=MAX_LEAD_H)):
                messagebox.showerror("Error", f"Bookings must be made between {MIN_LEAD_H}h and {MAX_LEAD_H}h in advance.")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()

            day = start.date().isoformat()
            c.execute("SELECT COUNT(*) FROM bookings WHERE user_id = ? AND start_time LIKE ?", (self.current_user, day + "%"))
            if c.fetchone()[0] >= MAX_PER_DAY:
                messagebox.showerror("Limit Reached", f"You have reached the maximum {MAX_PER_DAY} bookings for {day}.")
                conn.close()
                return

            start_iso, end_iso = start.isoformat(), end.isoformat()
            chosen = None
            for tid in range(1, TREADMILLS + 1):
                c.execute("SELECT COUNT(*) FROM bookings WHERE treadmill_id = ? AND start_time < ? AND end_time > ?", (tid, end_iso, start_iso))
                if c.fetchone()[0] == 0:
                    chosen = tid
                    break

            if chosen is None:
                messagebox.showerror("Unavailable", "All machines are reserved during this window.")
                conn.close()
                return

            c.execute("INSERT INTO bookings (user_id, treadmill_id, start_time, end_time) VALUES (?, ?, ?, ?)",
                      (self.current_user, chosen, start_iso, end_iso))
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"Reserved Treadmill {chosen} for {day}\n"
                                          f"Slot: {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}")
            self.render_sessions_view()

        ttk.Button(card, text="Confirm Reservation", style="Primary.TButton", command=submit_booking).pack(anchor="w", pady=20)

    def render_sessions_view(self):
        self.clear_workspace()

        card = ttk.Frame(self.workspace, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Your Scheduled Sessions", style="Title.TLabel").pack(anchor="w", pady=(0, 15))

        now_iso = datetime.now().replace(microsecond=0).isoformat()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM bookings WHERE end_time <= ?", (now_iso,))
        conn.commit()

        c.execute("SELECT treadmill_id, start_time, end_time FROM bookings WHERE user_id = ? ORDER BY start_time", (self.current_user,))
        rows = c.fetchall()
        conn.close()

        tree = ttk.Treeview(card, columns=("Machine", "Date", "Start", "End"), show="headings", selectmode="browse")
        tree.heading("Machine", text="MACHINE")
        tree.heading("Date", text="DATE")
        tree.heading("Start", text="START TIME")
        tree.heading("End", text="END TIME")

        tree.column("Machine", width=100, anchor="center")
        tree.column("Date", width=140, anchor="center")
        tree.column("Start", width=120, anchor="center")
        tree.column("End", width=120, anchor="center")

        tree.pack(fill="both", expand=True)

        for tid, s_iso, e_iso in rows:
            s = datetime.fromisoformat(s_iso)
            e = datetime.fromisoformat(e_iso)
            tree.insert("", "end", values=(f"Treadmill #{tid}", s.strftime("%a, %b %d"), s.strftime("%I:%M %p"), e.strftime("%I:%M %p")))

    def render_report_view(self):
        self.clear_workspace()

        card = ttk.Frame(self.workspace, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Report User Behavior", style="Title.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(card, text="Users receiving 3 reports are automatically suspended for 7 days.", style="Muted.TLabel").pack(anchor="w", pady=(0, 20))

        ttk.Label(card, text="Target User ID:", style="Body.TLabel").pack(anchor="w", pady=(5, 2))
        target_entry = ttk.Entry(card, width=30)
        target_entry.pack(anchor="w", pady=(0, 15))

        def submit_report():
            target = target_entry.get().strip()
            if target == self.current_user:
                messagebox.showerror("Error", "You cannot submit a report against yourself.")
                return

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE user_id = ?", (target,))
            if c.fetchone() is None:
                messagebox.showerror("Error", "Target user ID does not exist.")
                conn.close()
                return

            now_iso = datetime.now().replace(microsecond=0).isoformat()
            try:
                c.execute("INSERT INTO reports (reporter_id, reported_id, created_at) VALUES (?, ?, ?)",
                          (self.current_user, target, now_iso))
                conn.commit()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "You have already reported this user.")
                conn.close()
                return

            c.execute("SELECT COUNT(*) FROM reports WHERE reported_id = ?", (target,))
            num_reports = c.fetchone()[0]

            if num_reports >= REPORTS_TO_SUSPEND:
                until = (datetime.now() + timedelta(days=SUSPEND_DAYS)).replace(microsecond=0).isoformat()
                c.execute("UPDATE users SET suspended_until = ? WHERE user_id = ?", (until, target))
                c.execute("DELETE FROM reports WHERE reported_id = ?", (target,))
                conn.commit()
                messagebox.showwarning("Notice", f"User {target} reached threshold and was suspended.")
            else:
                messagebox.showinfo("Submitted", f"Report recorded against {target}.")

            conn.close()
            self.render_booking_view()

        ttk.Button(card, text="Submit Incident Report", style="Primary.TButton", command=submit_report).pack(anchor="w")


if __name__ == "__main__":
    app = TreadEasyApp()
    app.mainloop()
