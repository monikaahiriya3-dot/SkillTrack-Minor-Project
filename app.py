
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "skilltrack-dev-key-change-later"

DB_PATH = Path(__file__).with_name("skilltrack.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
        """)

def add_career_tables():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS career_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS role_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                importance TEXT NOT NULL DEFAULT 'Important',
                FOREIGN KEY (role_id) REFERENCES career_roles(id),
                UNIQUE(role_id, skill_name)
            )
        """)

        roles = [
            ("Software Developer", "Build and maintain software applications."),
            ("Full-Stack Developer", "Build both frontend and backend applications."),
            ("Frontend Developer", "Create attractive and interactive websites."),
            ("Backend Developer", "Build server-side logic and APIs."),
            ("Data Analyst", "Analyze data and create useful insights."),
            ("AI/ML Developer", "Build applications using AI and machine learning."),
            ("Cloud Engineer", "Deploy and manage cloud infrastructure."),
            ("Cybersecurity Expert", "Protect systems, networks and data.")
        ]

        for title, description in roles:
            conn.execute(
                "INSERT OR IGNORE INTO career_roles (title, description) VALUES (?, ?)",
                (title, description)
            )

        skill_map = {
            "Software Developer": [
                ("Python", "Essential"), ("Programming Fundamentals", "Essential"),
                ("Data Structures & Algorithms", "Essential"),
                ("Git/GitHub", "Important"), ("SQL", "Important"),
                ("Testing", "Important")
            ],
            "Full-Stack Developer": [
                ("HTML", "Essential"), ("CSS", "Essential"),
                ("JavaScript", "Essential"), ("Git/GitHub", "Important"),
                ("React", "Important"), ("Python", "Important"),
                ("Flask", "Important"), ("SQL", "Important"),
                ("REST API", "Important"), ("Docker", "Advanced")
            ],
            "Frontend Developer": [
                ("HTML", "Essential"), ("CSS", "Essential"),
                ("JavaScript", "Essential"), ("Responsive Design", "Essential"),
                ("Git/GitHub", "Important"), ("React", "Important")
            ],
            "Backend Developer": [
                ("Python", "Essential"), ("Flask", "Important"),
                ("SQL", "Essential"), ("REST API", "Essential"),
                ("Git/GitHub", "Important"), ("Authentication", "Important"),
                ("Docker", "Advanced")
            ],
            "Data Analyst": [
                ("Excel", "Essential"), ("SQL", "Essential"),
                ("Python", "Important"), ("Pandas", "Important"),
                ("Data Visualization", "Important"), ("Statistics", "Essential")
            ],
            "AI/ML Developer": [
                ("Python", "Essential"), ("Statistics", "Essential"),
                ("NumPy", "Important"), ("Pandas", "Important"),
                ("Machine Learning", "Essential"), ("SQL", "Important"),
                ("Model Evaluation", "Important")
            ],
            "Cloud Engineer": [
                ("Linux", "Essential"), ("Networking", "Essential"),
                ("Git/GitHub", "Important"), ("Cloud Fundamentals", "Essential"),
                ("Docker", "Important"), ("CI/CD", "Important")
            ],
            "Cybersecurity Expert": [
                ("Networking", "Essential"), ("Linux", "Essential"),
                ("Security Fundamentals", "Essential"),
                ("Python", "Important"), ("Web Security", "Important"),
                ("Risk Assessment", "Important")
            ]
        }

        for title, skills in skill_map.items():
            role = conn.execute(
                "SELECT id FROM career_roles WHERE title = ?", (title,)
            ).fetchone()

            for skill_name, importance in skills:
                conn.execute("""
                    INSERT OR IGNORE INTO role_skills
                    (role_id, skill_name, importance)
                    VALUES (?, ?, ?)
                """, (role["id"], skill_name, importance))


add_career_tables()


def add_user_skill_table():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_skills (
                user_id INTEGER NOT NULL,
                role_skill_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('known', 'learning')
                ),
                PRIMARY KEY (user_id, role_skill_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (role_skill_id) REFERENCES role_skills(id)
            )
        """)


add_user_skill_table()



@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return render_template("register.html")

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password))
                )
            flash("Account created successfully! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.")

    return render_template("login.html")



@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        goal = conn.execute("""
            SELECT r.id, r.title
            FROM user_career_goals g
            JOIN career_roles r ON r.id = g.role_id
            WHERE g.user_id = ?
        """, (session["user_id"],)).fetchone()

        total = 0
        completed = 0
        progress_percentage = 0

        if goal:
            total = conn.execute("""
                SELECT COUNT(*)
                FROM role_skills
                WHERE role_id = ?
            """, (goal["id"],)).fetchone()[0]

            completed = conn.execute("""
                SELECT COUNT(*)
                FROM user_skills us
                JOIN role_skills rs
                    ON rs.id = us.role_skill_id
                WHERE us.user_id = ?
                  AND rs.role_id = ?
                  AND us.status = 'known'
            """, (session["user_id"], goal["id"])).fetchone()[0]

            progress_percentage = (
                round(completed / total * 100) if total else 0
            )

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        goal=goal,
        total=total,
        completed=completed,
        progress_percentage=progress_percentage
    )


@app.route("/career", methods=["GET", "POST"])
def career():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        roles = conn.execute(
            "SELECT * FROM career_roles ORDER BY title"
        ).fetchall()

        if request.method == "POST":
            role_id = request.form.get("role_id", type=int)

            role = conn.execute(
                "SELECT id FROM career_roles WHERE id = ?", (role_id,)
            ).fetchone()

            if not role:
                flash("Please select a valid career goal.")
                return render_template("career.html", roles=roles)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_career_goals (
                    user_id INTEGER PRIMARY KEY,
                    role_id INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(role_id) REFERENCES career_roles(id)
                )
            """)

            conn.execute("""
                INSERT INTO user_career_goals (user_id, role_id)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET role_id = excluded.role_id
            """, (session["user_id"], role_id))

            return redirect(url_for("required_skills"))

    return render_template("career.html", roles=roles)


@app.route("/required-skills")
def required_skills():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        selected_role = conn.execute("""
            SELECT r.id, r.title, r.description
            FROM user_career_goals g
            JOIN career_roles r ON r.id = g.role_id
            WHERE g.user_id = ?
        """, (session["user_id"],)).fetchone()

        if not selected_role:
            return redirect(url_for("career"))

        skills = conn.execute("""
            SELECT skill_name, importance
            FROM role_skills
            WHERE role_id = ?
            ORDER BY id
        """, (selected_role["id"],)).fetchall()

    return render_template(
        "required_skills.html",
        role=selected_role,
        skills=skills
    )

@app.route("/current-skills", methods=["GET", "POST"])
def current_skills():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        selected_role = conn.execute("""
            SELECT r.id, r.title
            FROM user_career_goals g
            JOIN career_roles r ON r.id = g.role_id
            WHERE g.user_id = ?
        """, (session["user_id"],)).fetchone()

        if not selected_role:
            return redirect(url_for("career"))

        if request.method == "POST":
            known_ids = request.form.getlist("known")
            learning_ids = request.form.getlist("learning")

            valid_rows = conn.execute("""
                SELECT id FROM role_skills WHERE role_id = ?
            """, (selected_role["id"],)).fetchall()

            valid_ids = {str(row["id"]) for row in valid_rows}

            if (set(known_ids) | set(learning_ids)) - valid_ids:
                flash("Invalid skill selection. Please try again.")
                return redirect(url_for("current_skills"))

            if set(known_ids) & set(learning_ids):
                flash("A skill cannot be both known and learning.")
                return redirect(url_for("current_skills"))

            conn.execute(
                "DELETE FROM user_skills WHERE user_id = ?",
                (session["user_id"],)
            )

            for skill_id in known_ids:
                conn.execute("""
                    INSERT INTO user_skills (user_id, role_skill_id, status)
                    VALUES (?, ?, 'known')
                """, (session["user_id"], int(skill_id)))

            for skill_id in learning_ids:
                conn.execute("""
                    INSERT INTO user_skills (user_id, role_skill_id, status)
                    VALUES (?, ?, 'learning')
                """, (session["user_id"], int(skill_id)))

            return redirect(url_for("skill_gap"))

        skills = conn.execute("""
            SELECT rs.id, rs.skill_name, rs.importance, us.status
            FROM role_skills rs
            LEFT JOIN user_skills us
                ON us.role_skill_id = rs.id AND us.user_id = ?
            WHERE rs.role_id = ?
            ORDER BY rs.id
        """, (session["user_id"], selected_role["id"])).fetchall()

    return render_template(
        "current_skills.html",
        role=selected_role,
        skills=skills
    )


@app.route("/skill-gap")
def skill_gap():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        selected_role = conn.execute("""
            SELECT r.id, r.title
            FROM user_career_goals g
            JOIN career_roles r ON r.id = g.role_id
            WHERE g.user_id = ?
        """, (session["user_id"],)).fetchone()

        if not selected_role:
            return redirect(url_for("career"))

        skills = conn.execute("""
            SELECT rs.skill_name, rs.importance, us.status
            FROM role_skills rs
            LEFT JOIN user_skills us
                ON us.role_skill_id = rs.id AND us.user_id = ?
            WHERE rs.role_id = ?
            ORDER BY rs.id
        """, (session["user_id"], selected_role["id"])).fetchall()

    known = [s for s in skills if s["status"] == "known"]
    learning = [s for s in skills if s["status"] == "learning"]
    missing = [s for s in skills if s["status"] is None]

    total = len(skills)
    readiness = round(
        (len(known) + 0.5 * len(learning)) / total * 100
    ) if total else 0

    return render_template(
        "skill_gap.html",
        role=selected_role,
        known=known,
        learning=learning,
        missing=missing,
        total=total,
        readiness=readiness
    )

@app.route("/roadmap")
def roadmap():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        goal = conn.execute("""
            SELECT role_id
            FROM user_career_goals
            WHERE user_id = ?
        """, (session["user_id"],)).fetchone()

        if not goal:
            return redirect(url_for("career"))

        role = conn.execute("""
            SELECT *
            FROM career_roles
            WHERE id = ?
        """, (goal["role_id"],)).fetchone()

        skills = conn.execute("""
            SELECT rs.*, us.status
            FROM role_skills rs
            LEFT JOIN user_skills us
                ON rs.id = us.role_skill_id
                AND us.user_id = ?
            WHERE rs.role_id = ?
        """, (session["user_id"], goal["role_id"])).fetchall()

    learning = [s for s in skills if s["status"] == "learning"]
    missing = [s for s in skills if s["status"] is None]

    return render_template(
        "roadmap.html",
        role=role,
        learning=learning,
        missing=missing
    )


@app.route("/progress", methods=["GET", "POST"])
def progress():
    if "user_id" not in session:
        return redirect(url_for("login"))

    with get_db() as conn:
        goal = conn.execute("""
            SELECT role_id
            FROM user_career_goals
            WHERE user_id = ?
        """, (session["user_id"],)).fetchone()

        if not goal:
            return redirect(url_for("career"))

        if request.method == "POST":
            completed_ids = request.form.getlist("completed")

            skills = conn.execute("""
                SELECT id
                FROM role_skills
                WHERE role_id = ?
            """, (goal["role_id"],)).fetchall()

            valid_ids = {str(skill["id"]) for skill in skills}

            if not set(completed_ids).issubset(valid_ids):
                return "Invalid skill selection", 400

            conn.execute("""
                UPDATE user_skills
                SET status = 'known'
                WHERE user_id = ?
                AND role_skill_id IN (
                    SELECT id FROM role_skills
                    WHERE role_id = ?
                )
            """, (session["user_id"], goal["role_id"]))

            for skill_id in completed_ids:
                conn.execute("""
                    INSERT INTO user_skills
                        (user_id, role_skill_id, status)
                    VALUES (?, ?, 'known')
                    ON CONFLICT(user_id, role_skill_id)
                    DO UPDATE SET status = 'known'
                """, (session["user_id"], int(skill_id)))

            conn.commit()

        skills = conn.execute("""
            SELECT rs.*, us.status
            FROM role_skills rs
            LEFT JOIN user_skills us
                ON rs.id = us.role_skill_id
                AND us.user_id = ?
            WHERE rs.role_id = ?
        """, (session["user_id"], goal["role_id"])).fetchall()

        role = conn.execute("""
            SELECT *
            FROM career_roles
            WHERE id = ?
        """, (goal["role_id"],)).fetchone()

    completed = [s for s in skills if s["status"] == "known"]
    total = len(skills)
    percentage = round(len(completed) / total * 100) if total else 0

    return render_template(
        "progress.html",
        role=role,
        skills=skills,
        completed=completed,
        total=total,
        percentage=percentage
    )



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
