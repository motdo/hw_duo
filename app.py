import os
import sqlite3
from functools import wraps
from pathlib import Path

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
# PATH
# =====================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "addressbook.sqlite"

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

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "dev"
    )

    os.makedirs(BASE_DIR / "instance", exist_ok=True)

    app.teardown_appcontext(close_db)
    app.before_request(load_user)

    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)

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

        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(error=None):

    db = g.pop("db", None)

    if db:
        db.close()


# =====================
# USER
# =====================
def load_user():

    g.user = None

    user_id = session.get("user_id")

    if user_id:

        g.user = get_db().execute(
            "SELECT * FROM users WHERE id=?",
            (user_id,)
        ).fetchone()


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

        user = get_db().execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

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

        db.execute(
            """
            INSERT INTO users
            (username, password_hash)
            VALUES (?, ?)
            """,
            (
                username,
                generate_password_hash(password)
            )
        )

        db.commit()

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

    if q:

        rows = get_db().execute(
            """
            SELECT *
            FROM contacts
            WHERE user_id=?
            AND (
                name LIKE ?
                OR phone LIKE ?
                OR email LIKE ?
            )
            ORDER BY id DESC
            """,
            (
                session["user_id"],
                f"%{q}%",
                f"%{q}%",
                f"%{q}%"
            )
        ).fetchall()

    else:

        rows = get_db().execute(
            """
            SELECT *
            FROM contacts
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (session["user_id"],)
        ).fetchall()

    return jsonify({
        "contacts": [dict(row) for row in rows]
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

    get_db().execute(
        """
        INSERT INTO contacts
        (user_id, name, phone, email)
        VALUES (?, ?, ?, ?)
        """,
        (
            session["user_id"],
            name,
            phone,
            email
        )
    )

    get_db().commit()

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

    get_db().execute(
        """
        UPDATE contacts
        SET
            name=?,
            phone=?,
            email=?
        WHERE
            id=?
            AND user_id=?
        """,
        (
            name,
            phone,
            email,
            id,
            session["user_id"]
        )
    )

    get_db().commit()

    return jsonify({
        "success": True
    })


# =====================
# DELETE
# =====================
@search_bp.route("/contacts/<int:id>/delete", methods=["POST"])
@login_required
def delete_contact(id):

    get_db().execute(
        """
        DELETE FROM contacts
        WHERE id=?
        AND user_id=?
        """,
        (
            id,
            session["user_id"]
        )
    )

    get_db().commit()

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