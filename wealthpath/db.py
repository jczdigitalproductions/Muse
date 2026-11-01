"""SQLite storage for WealthPath AI."""
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

SEED_EMAIL = "judge@jczlabs.com"
SEED_PASSWORD = "What!JCZ"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  pw_hash TEXT NOT NULL,
  is_pro INTEGER NOT NULL DEFAULT 0,
  stripe_customer_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", (SEED_EMAIL,)
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users (email, pw_hash) VALUES (?, ?)",
            (SEED_EMAIL, generate_password_hash(SEED_PASSWORD)),
        )
    conn.commit()
    conn.close()


def get_user_by_email(db_path, email):
    conn = connect(db_path)
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(db_path, user_id):
    conn = connect(db_path)
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_password(user, password):
    return check_password_hash(user["pw_hash"], password)


def create_user(db_path, email, password):
    conn = connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO users (email, pw_hash) VALUES (?, ?)",
            (email.strip().lower(), generate_password_hash(password)),
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        user_id = None
    conn.close()
    return user_id


def set_pro(db_path, user_id, customer_id=None):
    conn = connect(db_path)
    conn.execute(
        "UPDATE users SET is_pro = 1, stripe_customer_id = "
        "COALESCE(?, stripe_customer_id) WHERE id = ?",
        (customer_id, user_id),
    )
    conn.commit()
    conn.close()
