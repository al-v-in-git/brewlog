import os
import uuid
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for
import mysql.connector
from mysql.connector import Error, IntegrityError
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "brewlog_secret")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3307")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "brewlog"),
}

app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
DEFAULT_BEANS = [
    ("Ethiopian Yirgacheffe", "Ethiopia", "Light"),
    ("Colombian Supremo", "Colombia", "Medium"),
    ("Kenyan AA", "Kenya", "Medium"),
    ("Brazil Santos", "Brazil", "Medium-Dark"),
]

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def get_server_connection():
    return mysql.connector.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (DB_CONFIG["database"], table_name, column_name),
    )
    return cursor.fetchone()[0] > 0


def ensure_column(cursor, table_name, column_name, definition):
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def initialize_database():
    server_db = get_server_connection()
    server_cursor = server_db.cursor()
    server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    server_cursor.close()
    server_db.close()

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS coffee_beans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            origin VARCHAR(100) NOT NULL,
            roast_level VARCHAR(50) NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS brewlogs (
            log_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            bean_name VARCHAR(100) NOT NULL,
            method VARCHAR(50) NOT NULL,
            grind_size VARCHAR(50) NOT NULL,
            water_temp INT NOT NULL,
            brew_time VARCHAR(20) NOT NULL,
            rating INT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            favorite BOOLEAN NOT NULL DEFAULT FALSE,
            image_path VARCHAR(255),
            bean_id INT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """
    )

    ensure_column(cursor, "brewlogs", "favorite", "BOOLEAN NOT NULL DEFAULT FALSE")
    ensure_column(cursor, "brewlogs", "image_path", "VARCHAR(255) NULL")
    ensure_column(cursor, "brewlogs", "bean_id", "INT NULL")

    for bean_name, origin, roast_level in DEFAULT_BEANS:
        cursor.execute(
            """
            INSERT IGNORE INTO coffee_beans (name, origin, roast_level)
            VALUES (%s, %s, %s)
            """,
            (bean_name, origin, roast_level),
        )

    db.commit()
    cursor.close()
    db.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def fetch_coffee_beans():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, origin, roast_level FROM coffee_beans ORDER BY name ASC")
    beans = cursor.fetchall()
    cursor.close()
    db.close()
    return beans


def fetch_bean(bean_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, name, origin, roast_level FROM coffee_beans WHERE id = %s",
        (bean_id,),
    )
    bean = cursor.fetchone()
    cursor.close()
    db.close()
    return bean


def fetch_filter_options(user_id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "SELECT DISTINCT method FROM brewlogs WHERE user_id = %s ORDER BY method ASC",
        (user_id,),
    )
    methods = [row[0] for row in cursor.fetchall()]
    cursor.close()
    db.close()
    return {
        "methods": methods,
        "ratings": [5, 4, 3, 2, 1],
    }


def fetch_brew_logs(user_id, filters=None, favorites_only=False):
    filters = filters or {}
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT
            b.log_id,
            b.bean_name,
            b.method,
            b.grind_size,
            b.water_temp,
            b.brew_time,
            b.rating,
            b.notes,
            b.created_at,
            b.favorite,
            b.image_path,
            cb.origin,
            cb.roast_level
        FROM brewlogs b
        LEFT JOIN coffee_beans cb ON b.bean_id = cb.id
        WHERE b.user_id = %s
    """
    params = [user_id]

    if favorites_only:
        query += " AND b.favorite = TRUE"

    search = (filters.get("search") or "").strip()
    method_name = (filters.get("method") or "").strip()
    rating_value = (filters.get("rating") or "").strip()

    if search:
        query += " AND (b.bean_name LIKE %s OR b.notes LIKE %s)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    if method_name:
        query += " AND b.method = %s"
        params.append(method_name)

    if rating_value:
        query += " AND b.rating = %s"
        params.append(int(rating_value))

    sort_value = filters.get("sort", "created_desc")
    sort_map = {
        "created_desc": "b.created_at DESC, b.log_id DESC",
        "created_asc": "b.created_at ASC, b.log_id ASC",
        "bean_asc": "b.bean_name ASC",
        "method_asc": "b.method ASC",
        "rating_desc": "b.rating DESC, b.created_at DESC",
        "rating_asc": "b.rating ASC, b.created_at DESC",
    }
    query += f" ORDER BY {sort_map.get(sort_value, sort_map['created_desc'])}"

    cursor.execute(query, tuple(params))
    brew_logs = cursor.fetchall()
    cursor.close()
    db.close()
    return brew_logs


def fetch_dashboard_summary(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_brews,
            COALESCE(ROUND(AVG(rating), 1), 0) AS average_rating,
            SUM(CASE WHEN favorite = TRUE THEN 1 ELSE 0 END) AS favorite_brews
        FROM brewlogs
        WHERE user_id = %s
        """,
        (user_id,),
    )
    summary = cursor.fetchone()

    cursor.execute(
        """
        SELECT method, COUNT(*) AS uses
        FROM brewlogs
        WHERE user_id = %s
        GROUP BY method
        ORDER BY uses DESC, method ASC
        LIMIT 1
        """,
        (user_id,),
    )
    top_method = cursor.fetchone()

    cursor.execute(
        """
        SELECT bean_name, COUNT(*) AS uses
        FROM brewlogs
        WHERE user_id = %s
        GROUP BY bean_name
        ORDER BY uses DESC, bean_name ASC
        LIMIT 1
        """,
        (user_id,),
    )
    top_bean = cursor.fetchone()

    cursor.close()
    db.close()

    return {
        "total_brews": summary["total_brews"] or 0,
        "average_rating": summary["average_rating"] or 0,
        "favorite_brews": summary["favorite_brews"] or 0,
        "top_method": top_method["method"] if top_method else "N/A",
        "top_bean": top_bean["bean_name"] if top_bean else "N/A",
    }


def fetch_analytics(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_brews,
            COALESCE(ROUND(AVG(rating), 1), 0) AS average_rating
        FROM brewlogs
        WHERE user_id = %s
        """,
        (user_id,),
    )
    summary = cursor.fetchone()

    cursor.execute(
        """
        SELECT method, COUNT(*) AS uses
        FROM brewlogs
        WHERE user_id = %s
        GROUP BY method
        ORDER BY uses DESC, method ASC
        LIMIT 1
        """,
        (user_id,),
    )
    most_used_method = cursor.fetchone()

    cursor.execute(
        """
        SELECT bean_name, COUNT(*) AS uses
        FROM brewlogs
        WHERE user_id = %s
        GROUP BY bean_name
        ORDER BY uses DESC, bean_name ASC
        LIMIT 1
        """,
        (user_id,),
    )
    most_used_bean = cursor.fetchone()

    cursor.execute(
        """
        SELECT method AS label, COUNT(*) AS value
        FROM brewlogs
        WHERE user_id = %s
        GROUP BY method
        ORDER BY value DESC, label ASC
        """,
        (user_id,),
    )
    method_breakdown = cursor.fetchall()

    cursor.execute(
        """
        SELECT CONCAT(rating, ' Stars') AS label, COUNT(*) AS value
        FROM brewlogs
        WHERE user_id = %s
        GROUP BY rating
        ORDER BY rating ASC
        """,
        (user_id,),
    )
    rating_breakdown = cursor.fetchall()

    cursor.close()
    db.close()

    return {
        "total_brews": summary["total_brews"] or 0,
        "average_rating": summary["average_rating"] or 0,
        "most_used_method": most_used_method["method"] if most_used_method else "N/A",
        "most_used_bean": most_used_bean["bean_name"] if most_used_bean else "N/A",
        "method_chart_labels": [row["label"] for row in method_breakdown],
        "method_chart_values": [row["value"] for row in method_breakdown],
        "rating_chart_labels": [row["label"] for row in rating_breakdown],
        "rating_chart_values": [row["value"] for row in rating_breakdown],
    }


def save_uploaded_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_image(file_storage.filename):
        raise ValueError("Please upload a PNG, JPG, JPEG, GIF, or WEBP image.")

    original_name = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex}_{original_name}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file_storage.save(file_path)
    return os.path.join("uploads", unique_name).replace("\\", "/")


DB_INIT_ERROR = None

try:
    initialize_database()
except Error as exc:
    DB_INIT_ERROR = f"Database initialization warning: {exc}"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password),
            )
            db.commit()
            cursor.close()
            db.close()
            return redirect(url_for("login"))
        except IntegrityError:
            error = "An account with that email already exists."
        except Error as exc:
            error = f"Database error: {exc}"

    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                "SELECT user_id, name FROM users WHERE email = %s AND password = %s",
                (email, password),
            )
            user = cursor.fetchone()
            cursor.close()
            db.close()

            if user:
                session["user_id"] = user[0]
                session["user_name"] = user[1]
                return redirect(url_for("dashboard"))

            error = "Invalid email or password."
        except Error as exc:
            error = f"Database error: {exc}"

    return render_template("login.html", error=error)


@app.route("/dashboard")
@login_required
def dashboard():
    error = None
    brew_logs = []
    summary = {
        "total_brews": 0,
        "average_rating": 0,
        "favorite_brews": 0,
        "top_method": "N/A",
        "top_bean": "N/A",
    }

    try:
        brew_logs = fetch_brew_logs(session["user_id"], {"sort": "created_desc"})[:5]
        summary = fetch_dashboard_summary(session["user_id"])
    except Error as exc:
        error = f"Database error: {exc}"

    return render_template(
        "dashboard.html",
        brew_logs=brew_logs,
        summary=summary,
        error=error,
        user_name=session.get("user_name", "Brewer"),
    )


@app.route("/history")
@login_required
def history():
    filters = {
        "search": request.args.get("search", ""),
        "method": request.args.get("method", ""),
        "rating": request.args.get("rating", ""),
        "sort": request.args.get("sort", "created_desc"),
    }
    brew_logs = []
    filter_options = {"methods": [], "ratings": [5, 4, 3, 2, 1]}
    error = None

    try:
        brew_logs = fetch_brew_logs(session["user_id"], filters)
        filter_options = fetch_filter_options(session["user_id"])
    except Error as exc:
        error = f"Database error: {exc}"

    return render_template(
        "history.html",
        brew_logs=brew_logs,
        filters=filters,
        filter_options=filter_options,
        error=error,
    )


@app.route("/favorites")
@login_required
def favorites():
    error = None
    brew_logs = []

    try:
        brew_logs = fetch_brew_logs(
            session["user_id"],
            {"sort": request.args.get("sort", "created_desc")},
            favorites_only=True,
        )
    except Error as exc:
        error = f"Database error: {exc}"

    return render_template("favorites.html", brew_logs=brew_logs, error=error)


@app.route("/analytics")
@login_required
def analytics():
    analytics_data = {
        "total_brews": 0,
        "average_rating": 0,
        "most_used_method": "N/A",
        "most_used_bean": "N/A",
        "method_chart_labels": [],
        "method_chart_values": [],
        "rating_chart_labels": [],
        "rating_chart_values": [],
    }
    error = None

    try:
        analytics_data = fetch_analytics(session["user_id"])
    except Error as exc:
        error = f"Database error: {exc}"

    return render_template("analytics.html", analytics=analytics_data, error=error)


@app.route("/calculator")
@login_required
def calculator():
    return render_template("calculator.html")


@app.route("/addbrew", methods=["GET", "POST"])
@login_required
def add_brew():
    error = None
    beans = []

    try:
        beans = fetch_coffee_beans()
    except Error as exc:
        error = f"Database error: {exc}"

    if request.method == "POST":
        bean_id = request.form["bean_id"].strip()
        brew_method = request.form["method"].strip()
        grind_size = request.form["grind_size"].strip()
        water_temp = request.form["water_temp"].strip()
        brew_time = request.form["brew_time"].strip()
        rating = request.form["rating"].strip()
        notes = request.form["notes"].strip()
        favorite = 1 if request.form.get("favorite") == "on" else 0
        image_file = request.files.get("brew_image")

        try:
            bean = fetch_bean(int(bean_id))
            if not bean:
                raise ValueError("Please select a coffee bean from the list.")

            image_path = save_uploaded_image(image_file)

            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                """
                INSERT INTO brewlogs
                (user_id, bean_id, bean_name, method, grind_size, water_temp, brew_time, rating, notes, favorite, image_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    bean["id"],
                    bean["name"],
                    brew_method,
                    grind_size,
                    int(water_temp),
                    brew_time,
                    int(rating),
                    notes,
                    favorite,
                    image_path,
                ),
            )
            db.commit()
            cursor.close()
            db.close()
            return redirect(url_for("history"))
        except ValueError as exc:
            error = str(exc)
        except Error as exc:
            error = f"Database error: {exc}"

    return render_template("add_brew.html", error=error, beans=beans)


@app.route("/brew/<int:log_id>/delete", methods=["POST"])
@login_required
def delete_brew(log_id):
    next_url = request.form.get("next") or url_for("history")

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT image_path FROM brewlogs WHERE log_id = %s AND user_id = %s",
            (log_id, session["user_id"]),
        )
        brew = cursor.fetchone()

        if brew:
            cursor.execute(
                "DELETE FROM brewlogs WHERE log_id = %s AND user_id = %s",
                (log_id, session["user_id"]),
            )
            db.commit()

            if brew["image_path"]:
                image_path = os.path.join(app.static_folder, brew["image_path"])
                if os.path.exists(image_path):
                    os.remove(image_path)

        cursor.close()
        db.close()
    except Error:
        pass

    return redirect(next_url)


@app.route("/brew/<int:log_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(log_id):
    next_url = request.form.get("next") or url_for("history")

    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            """
            UPDATE brewlogs
            SET favorite = CASE WHEN favorite = TRUE THEN FALSE ELSE TRUE END
            WHERE log_id = %s AND user_id = %s
            """,
            (log_id, session["user_id"]),
        )
        db.commit()
        cursor.close()
        db.close()
    except Error:
        pass

    return redirect(next_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    if DB_INIT_ERROR:
        print(DB_INIT_ERROR)
    app.run(debug=True)
