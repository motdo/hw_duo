import os
from functools import wraps

import mysql.connector
from dotenv import load_dotenv

from flask import (
    Flask,
    Blueprint,
    g,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    render_template,
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

# =====================
# ENV
# =====================
load_dotenv()

# =====================
# BLUEPRINT
# =====================
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
search_bp = Blueprint("search", __name__, url_prefix="/search")


# =====================
# APP
# =====================
def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "dev"
    )

    app.teardown_appcontext(close_db)
    app.before_request(load_user)

    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)

    # 테이블 자동 생성
    with app.app_context():
        init_db()

    @app.route("/")
    def index():

        if g.user:
            return redirect(url_for("search.index"))

        return redirect(url_for("auth.login"))

    return app


# =====================
# DB
# =====================
def get_db():

    if "db" not in g:

        g.db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )

    return g.db


def close_db(error=None):

    db = g.pop("db", None)

    if db:
        db.close()


# =====================
# INIT DB
# =====================
def init_db():

    db = get_db()
    cursor = db.cursor()

    # users 테이블
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )

    # contacts 테이블
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(100),
            email VARCHAR(255),

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
        """
    )

    db.commit()

    cursor.close()


# =====================
# USER
# =====================
def load_user():

    g.user = None

    user_id = session.get("user_id")

    if user_id:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE id=%s",
            (user_id,)
        )

        g.user = cursor.fetchone()

        cursor.close()


def login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped_view


# =====================
# LOGIN
# =====================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        user = cursor.fetchone()

        cursor.close()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session.clear()
            session["user_id"] = user["id"]

            return redirect(url_for("search.index"))

        return "로그인 실패"

    return render_template("auth/login.html")


# =====================
# REGISTER
# =====================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (username, password_hash)
                VALUES (%s, %s)
                """,
                (
                    username,
                    generate_password_hash(password)
                )
            )

            db.commit()

        except mysql.connector.Error as e:

            return f"회원가입 오류: {e}"

        finally:

            cursor.close()

        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# =====================
# LOGOUT
# =====================
@auth_bp.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("auth.login"))


# =====================
# PAGE
# =====================
@search_bp.route("/")
@login_required
def index():

    return render_template("search/index.html")


# =====================
# CONTACT LIST
# =====================
@search_bp.route("/api")
@login_required
def list_contacts():

    q = request.args.get("q", "").strip()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if q:

        cursor.execute(
            """
            SELECT *
            FROM contacts
            WHERE user_id=%s
            AND (
                name LIKE %s
                OR phone LIKE %s
                OR email LIKE %s
            )
            ORDER BY id DESC
            """,
            (
                session["user_id"],
                f"%{q}%",
                f"%{q}%",
                f"%{q}%"
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM contacts
            WHERE user_id=%s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

    rows = cursor.fetchall()

    cursor.close()

    return jsonify({
        "contacts": rows
    })


# =====================
# CREATE
# =====================
@search_bp.route("/contacts", methods=["POST"])
@login_required
def create_contact():

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    if not name:

        return jsonify({
            "success": False,
            "error": "이름 입력"
        })

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO contacts
        (user_id, name, phone, email)
        VALUES (%s, %s, %s, %s)
        """,
        (
            session["user_id"],
            name,
            phone,
            email
        )
    )

    db.commit()

    cursor.close()

    return jsonify({
        "success": True
    })


# =====================
# UPDATE
# =====================
@search_bp.route("/contacts/<int:id>", methods=["POST"])
@login_required
def update_contact(id):

    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE contacts
        SET
            name=%s,
            phone=%s,
            email=%s
        WHERE
            id=%s
            AND user_id=%s
        """,
        (
            name,
            phone,
            email,
            id,
            session["user_id"]
        )
    )

    db.commit()

    cursor.close()

    return jsonify({
        "success": True
    })


# =====================
# DELETE
# =====================
@search_bp.route("/contacts/<int:id>/delete", methods=["POST"])
@login_required
def delete_contact(id):

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        DELETE FROM contacts
        WHERE id=%s
        AND user_id=%s
        """,
        (
            id,
            session["user_id"]
        )
    )

    db.commit()

    cursor.close()

    return jsonify({
        "success": True
    })


# =====================
# RUN
# =====================
app = create_app()

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )