# TreadEasy — a simple treadmill booking system
import sqlite3
from datetime import datetime, timedelta, time

DB_FILE = "treadeasy.db"
OPEN_HOUR = 7          # gym opens 07:00
CLOSE_HOUR = 22        # gym closes 22:00
TREADMILLS = 5         # number of identical machines
GRID_MIN = 5           # start times land on a 5-minute grid
MAX_LEN = 45           # longest session (minutes)
MAX_PER_DAY = 2        # bookings per user per calendar day
MIN_LEAD_H = 3         # can't book less than 3h ahead
MAX_LEAD_H = 24        # can't book more than 24h ahead
REPORTS_TO_SUSPEND = 3
SUSPEND_DAYS = 7

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor() # equivalent to "opening" a text file.
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
    """) # reported_id is to later ensure the same user can't be reported multiple times by the same reporter.
    conn.commit() # equivalent to "saving" a text file.
    conn.close()

def register():
    print('NOTE: Trailing whitespaces will be removed automatically.')
    user_id = input("Choose a user id: ").strip()
    password = input("Choose a password: ").strip()
    if user_id == "" or password == "":
        print("Sorry, the ID and password sections can't be empty.")
        return # to prompt the user to repeat the registration process.
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, password) VALUES (?, ?)", # <– this is SQL language inside python.
                  (user_id, password))
        conn.commit()
        print("Account created! You can log in now.")
    except sqlite3.IntegrityError: # raised when the user_id already exists in the database.
        print("That user id is already taken.")
    conn.close()

def login():
    print('NOTE: Trailing whitespaces will be removed automatically.')
    user_id = input("User id: ").strip()
    password = input("Password: ").strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password, suspended_until FROM users WHERE user_id = ?",
              (user_id,))
    row = c.fetchone()
    conn.close()

    if row is None or row[0] != password:
        print("Wrong user id or password.")
        return None

    suspended_until = row[1]
    if suspended_until is not None:
        if datetime.fromisoformat(suspended_until) > datetime.now():
            print("Your account is suspended until", suspended_until)
            print("You cannot log in until your suspension is over.")
            return None

    print("Welcome back, " + user_id + "!")
    return user_id # we return user_id for the logged_in menu to successfully execute.


def logged_in_menu(user_id):
    while True:
        print("\n--- Menu ---")
        print("1. Book a session")
        print("2. View my sessions")
        print("3. Report a user")
        print("4. Log out")
        choice = input("Choose: ")
        if choice == "1":
            book(user_id)
        elif choice == "2":
            view_sessions(user_id)
        elif choice == "3":
            report_user(user_id)
        elif choice == "4":
            print("Logged out.")
            break
        else:
            print("Invalid choice.")

def parse_clock(text):
    # turn our input time string (format hh:mm AM/PM) into a datetime.time object.
    text = text.strip().upper() #am/pM turns strictly into AM/PM.
    try:
        return datetime.strptime(text, "%I:%M %p").time()
    except ValueError:
        return None

def book(user_id):
    now = datetime.now() # current time.
    print("Enter times as  h:mm am/pm   (example: 8:30 am, or 12:35 pm.)")
    print("NOTE: If the time you have entered is in the past for today and falls in tomorrow's slot, it will be booked for tomorrow.")
    start_t = parse_clock(input("Start time: ")) #parse_clock changes them into program-understandable times.
    end_t   = parse_clock(input("End time: "))

    # CHECK 1 — format
    if start_t is None or end_t is None:
        print("Couldn't read that. Use the format – 8:30 am.")
        return

    # turn the bare clock times into real dates (next time they occur)
    start = datetime.combine(now.date(), start_t) # if time is in the past, we will book it for tomorrow.
    if start <= now:
        start += timedelta(days=1)
    end = datetime.combine(start.date(), end_t)

    # CHECK 2 — end after start
    if end <= start:
        print("End time must be after start time.")
        return

    # CHECK 3 — length at most 45 minutes
    length_min = (end - start).total_seconds() / 60 # calculates if the session duration is less or more than 45 minutes.
    if length_min > MAX_LEN:
        print("A session can be at most", MAX_LEN, "minutes.")
        return

    # CHECK 4 — minutes on the 5-minute grid
    if start.minute % GRID_MIN != 0 or end.minute % GRID_MIN != 0: # has to be a multiple of 5.
        print("Minutes must be multiples of", GRID_MIN, "(e.g. 7:25, not 7:23).")
        return

    # CHECK 5 — inside gym hours (07:00 - 22:00)
    closing = datetime.combine(start.date(), time(CLOSE_HOUR, 0))
    if start.hour < OPEN_HOUR or end > closing:
        print("The gym is only open from 7 am to 10 pm. Please book your slot within this time frame.")
        return

    # CHECK 6 — booking window (+3h to +24h)
    if start < now + timedelta(hours=MIN_LEAD_H):
        print("You must book at least", MIN_LEAD_H, "hours in advance.")
        return
    if start > now + timedelta(hours=MAX_LEAD_H):
        print("You can only book up to", MAX_LEAD_H, "hours in advance.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor() # opens the SQLite database file for the next checks.

    # CHECK 7 — at most 2 bookings that calendar day
    day = start.date().isoformat()                 # 'YYYY-MM-DD'
    c.execute("SELECT COUNT(*) FROM bookings WHERE user_id = ? AND start_time LIKE ?",
              (user_id, day + "%"))
    (count_today,) = c.fetchone()
    if count_today >= MAX_PER_DAY:
        print("You already have", MAX_PER_DAY, "bookings on", day + ".")
        conn.close()
        return

    # CHECK 8 — find a free treadmill
    start_iso = start.isoformat()
    end_iso   = end.isoformat()
    chosen = None
    for tid in range(1, TREADMILLS + 1):
        c.execute("""SELECT COUNT(*) FROM bookings
                     WHERE treadmill_id = ?
                       AND start_time < ?
                       AND end_time > ?""",
                  (tid, end_iso, start_iso))
        (overlap,) = c.fetchone()
        if overlap == 0:
            chosen = tid
            break
    if chosen is None:
        print("All treadmills are booked for that time. Try another slot.")
        conn.close()
        return

    # all 8 checks passed -> save it
    c.execute("""INSERT INTO bookings (user_id, treadmill_id, start_time, end_time)
                 VALUES (?, ?, ?, ?)""",
              (user_id, chosen, start_iso, end_iso))
    conn.commit()
    conn.close()
    print("Booked! Treadmill", chosen, "on", day,
          "from", start.strftime("%I:%M %p"), "to", end.strftime("%I:%M %p"))

def view_sessions(user_id):
    now_iso = datetime.now().replace(microsecond=0).isoformat()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # remove every session that has already finished (this is the "auto-disappear")
    c.execute("DELETE FROM bookings WHERE end_time <= ?", (now_iso,))
    conn.commit()

    # show this user's remaining (upcoming / current) sessions
    c.execute("""SELECT treadmill_id, start_time, end_time
                 FROM bookings
                 WHERE user_id = ?
                 ORDER BY start_time""", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("You have no upcoming sessions.")
        return

    print("\nYour sessions:")
    for treadmill_id, start_iso, end_iso in rows:
        start = datetime.fromisoformat(start_iso)
        end   = datetime.fromisoformat(end_iso)
        print("- Treadmill", treadmill_id, ":",
              start.strftime("%a %d %b, %I:%M %p"), "to", end.strftime("%I:%M %p"))

def report_user(reporter_id):
    target = input("User id to report: ").strip()

    # you can't report yourself
    if target == reporter_id:
        print("You can't report yourself.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # the person you're reporting must actually exist
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (target,))
    if c.fetchone() is None:
        print("No user with that id.")
        conn.close()
        return

    # record the report — UNIQUE(reporter_id, reported_id) blocks a repeat
    now_iso = datetime.now().replace(microsecond=0).isoformat()
    try:
        c.execute("""INSERT INTO reports (reporter_id, reported_id, created_at)
                     VALUES (?, ?, ?)""", (reporter_id, target, now_iso))
        conn.commit()
    except sqlite3.IntegrityError:
        print("You have already reported this user.")
        conn.close()
        return

    print("Report submitted against " + target + ".")

    # how many different people have now reported this user?
    c.execute("SELECT COUNT(*) FROM reports WHERE reported_id = ?", (target,))
    (num_reports,) = c.fetchone()

    # 3 or more -> suspend for 7 days
    if num_reports >= REPORTS_TO_SUSPEND:
        until = (datetime.now() + timedelta(days=SUSPEND_DAYS)).replace(microsecond=0).isoformat()
        c.execute("UPDATE users SET suspended_until = ? WHERE user_id = ?", (until, target))
        c.execute("DELETE FROM reports WHERE reported_id = ?", (target,))
        conn.commit()
        print(target, "has reached", REPORTS_TO_SUSPEND,
              "reports and is suspended for", SUSPEND_DAYS, "days.")

    conn.close()

def main():
    init_db()
    print("Welcome to TreadEasy!")
    while True:
        print("\n1. Register")
        print("2. Login")
        print("3. Quit")
        choice = input("Choose: ")
        if choice == "1":
            register()
        elif choice == "2":
            user_id = login()
            if user_id is not None: # if the user successfully logged in, show the logged-in menu.
                logged_in_menu(user_id)
        elif choice == "3":
            print("Bye!")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()