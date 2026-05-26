import os
import sqlite3
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

import click
from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
search_bp = Blueprint("search", __name__, url_prefix="/search")
api_bp = Blueprint("api", __name__, url_prefix="/api")


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-change-me"),
        DATABASE=os.path.join(app.instance_path, "addressbook.sqlite"),
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    app.teardown_appcontext(close_db)
    app.before_request(load_logged_in_user)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)

    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        if g.user:
            return redirect(url_for("search.index"))
        return redirect(url_for("auth.login"))

    return app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with SCHEMA_PATH.open("r", encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())
    db.commit()


@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized the database.")


@click.command("seed-db")
def seed_db_command():
    db = get_db()
    username = "demo"
    password = "demo1234"

    user = db.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        user_id = cursor.lastrowid
    else:
        user_id = user["id"]

    existing_contacts = db.execute(
        "SELECT COUNT(*) AS count FROM contacts WHERE user_id = ?",
        (user_id,),
    ).fetchone()["count"]

    if existing_contacts == 0:
        db.executemany(
            """
            INSERT INTO contacts (user_id, name, phone, email, address, memo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    user_id,
                    "Kim Minjun",
                    "010-1234-5678",
                    "minjun@example.com",
                    "Seoul",
                    "Project teammate",
                ),
                (
                    user_id,
                    "Lee Seoyeon",
                    "010-9876-5432",
                    "seoyeon@example.com",
                    "Busan",
                    "Search test contact",
                ),
            ],
        )

    db.commit()
    click.echo("Seeded demo user: demo / demo1234")


def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None

    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, username, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.full_path))
        return view(**kwargs)

    return wrapped_view


def api_login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return jsonify({"success": False, "error": "Login required."}), 401
        return view(**kwargs)

    return wrapped_view


@auth_bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user:
        return redirect(url_for("search.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = (
            request.form.get("password_confirm")
            or request.form.get("confirm_password")
            or ""
        )
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif password_confirm and password != password_confirm:
            error = "Password confirmation does not match."

        db = get_db()
        if error is None:
            duplicate = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if duplicate is not None:
                error = "Username is already registered."

        if error is None:
            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()
            flash("Registration complete. Please log in.")
            return redirect(url_for("auth.login"))

        flash(error)

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user:
        return redirect(url_for("search.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None

        user = get_db().execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None:
            error = "Incorrect username."
        elif not check_password_hash(user["password_hash"], password):
            error = "Incorrect password."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(get_safe_next_url())

        flash(error)

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=("POST", "GET"))
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@api_bp.route("/login", methods=("POST",))
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or request.form.get("username") or "").strip()
    password = data.get("password") or request.form.get("password") or ""

    user = get_db().execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid login."}), 401

    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"success": True, "username": user["username"]})


@api_bp.route("/contacts", methods=("GET", "POST"))
@api_login_required
def api_contacts():
    if request.method == "POST":
        contact, error = read_contact_payload()
        if error:
            return jsonify({"success": False, "error": error}), 400

        cursor = get_db().execute(
            """
            INSERT INTO contacts (user_id, name, phone, email, address, memo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                contact["name"],
                contact["phone"],
                contact["email"],
                contact["address"],
                contact["memo"],
            ),
        )
        get_db().commit()
        return jsonify({"success": True, "id": cursor.lastrowid}), 201

    query = (request.args.get("keyword") or request.args.get("q") or "").strip()
    return jsonify([dict(contact) for contact in find_contacts(query=query)])


@search_bp.route("/")
@login_required
def index():
    query = get_search_query()
    contacts = find_contacts(query=query)
    return render_template(
        "search/index.html",
        query=query,
        contacts=contacts,
        total=len(contacts),
    )


@search_bp.route("/api")
@login_required
def api():
    query = get_search_query()
    contacts = find_contacts(query=query)
    return jsonify(
        {
            "query": query,
            "total": len(contacts),
            "contacts": [dict(contact) for contact in contacts],
        }
    )


@search_bp.route("/contacts", methods=("POST",))
@login_required
def create_contact():
    contact, error = read_contact_form()

    if error:
        flash(error)
        return redirect(url_for("search.index", q=get_search_query()))

    get_db().execute(
        """
        INSERT INTO contacts (user_id, name, phone, email, address, memo)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            g.user["id"],
            contact["name"],
            contact["phone"],
            contact["email"],
            contact["address"],
            contact["memo"],
        ),
    )
    get_db().commit()
    flash("Contact added.")
    return redirect(url_for("search.index"))


@search_bp.route("/contacts/<int:contact_id>", methods=("POST",))
@login_required
def update_contact(contact_id):
    get_contact_or_404(contact_id)
    contact, error = read_contact_form()

    if error:
        flash(error)
        return redirect(url_for("search.index", q=get_search_query()))

    get_db().execute(
        """
        UPDATE contacts
        SET name = ?, phone = ?, email = ?, address = ?, memo = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (
            contact["name"],
            contact["phone"],
            contact["email"],
            contact["address"],
            contact["memo"],
            contact_id,
            g.user["id"],
        ),
    )
    get_db().commit()
    flash("Contact updated.")
    return redirect(url_for("search.index", q=get_search_query()))


@search_bp.route("/contacts/<int:contact_id>/delete", methods=("POST",))
@login_required
def delete_contact(contact_id):
    get_contact_or_404(contact_id)
    get_db().execute(
        "DELETE FROM contacts WHERE id = ? AND user_id = ?",
        (contact_id, g.user["id"]),
    )
    get_db().commit()
    flash("Contact deleted.")
    return redirect(url_for("search.index", q=get_search_query()))


def get_search_query():
    return (request.values.get("q") or request.values.get("query") or "").strip()


def get_safe_next_url():
    target = request.args.get("next", "")
    parsed = urlsplit(target)

    if target.startswith("/") and not parsed.scheme and not parsed.netloc:
        return target

    return url_for("search.index")


def find_contacts(query):
    if query:
        pattern = f"%{query}%"
        return get_db().execute(
            """
            SELECT id, name, phone, email, address, memo, created_at, updated_at
            FROM contacts
            WHERE user_id = ?
              AND (
                name LIKE ?
                OR phone LIKE ?
                OR email LIKE ?
                OR address LIKE ?
                OR memo LIKE ?
              )
            ORDER BY name COLLATE NOCASE ASC
            """,
            (g.user["id"], pattern, pattern, pattern, pattern, pattern),
        ).fetchall()

    return get_db().execute(
        """
        SELECT id, name, phone, email, address, memo, created_at, updated_at
        FROM contacts
        WHERE user_id = ?
        ORDER BY name COLLATE NOCASE ASC
        LIMIT 50
        """,
        (g.user["id"],),
    ).fetchall()


def read_contact_form():
    contact = {
        "name": request.form.get("name", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "email": request.form.get("email", "").strip(),
        "address": request.form.get("address", "").strip(),
        "memo": request.form.get("memo", "").strip(),
    }

    if not contact["name"]:
        return contact, "Contact name is required."

    return contact, None


def read_contact_payload():
    data = request.get_json(silent=True) or {}
    contact = {
        "name": (data.get("name") or request.form.get("name") or "").strip(),
        "phone": (data.get("phone") or request.form.get("phone") or "").strip(),
        "email": (data.get("email") or request.form.get("email") or "").strip(),
        "address": (data.get("address") or request.form.get("address") or "").strip(),
        "memo": (data.get("memo") or request.form.get("memo") or "").strip(),
    }

    if not contact["name"]:
        return contact, "Contact name is required."

    return contact, None


def get_contact_or_404(contact_id):
    contact = get_db().execute(
        """
        SELECT id, user_id, name, phone, email, address, memo, created_at, updated_at
        FROM contacts
        WHERE id = ? AND user_id = ?
        """,
        (contact_id, g.user["id"]),
    ).fetchone()

    if contact is None:
        abort(404)

    return contact


app = create_app()
