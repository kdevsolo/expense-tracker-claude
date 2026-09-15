import sqlite3

import pytest

from database.db import get_db, init_db, seed_db


def test_init_db_creates_tables(app):
    init_db()
    conn = get_db()
    tables = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "users" in tables
    assert "expenses" in tables


def test_init_db_is_idempotent(app):
    init_db()
    init_db()


def test_get_db_enables_foreign_keys(app):
    conn = get_db()
    fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.close()
    assert fk_status == 1


def test_seed_db_inserts_demo_user(app):
    init_db()
    seed_db()
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    assert user is not None
    assert user["name"] == "Demo User"
    assert user["password_hash"] != "demo123"


def test_seed_db_inserts_eight_expenses_covering_all_categories(app):
    init_db()
    seed_db()
    conn = get_db()
    expenses = conn.execute("SELECT * FROM expenses").fetchall()
    conn.close()
    assert len(expenses) == 8
    categories = {row["category"] for row in expenses}
    assert categories == {
        "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
    }


def test_seed_db_is_idempotent(app):
    init_db()
    seed_db()
    seed_db()
    conn = get_db()
    user_count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    expense_count = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
    conn.close()
    assert user_count == 1
    assert expense_count == 8


def test_duplicate_email_raises_integrity_error(app):
    init_db()
    seed_db()
    conn = get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Another User", "demo@spendly.com", "somehash"),
        )
        conn.commit()
    conn.close()


def test_expense_with_invalid_user_id_raises_integrity_error(app):
    init_db()
    conn = get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (99999, 10.0, "Food", "2026-09-01", "orphan expense"),
        )
        conn.commit()
    conn.close()
