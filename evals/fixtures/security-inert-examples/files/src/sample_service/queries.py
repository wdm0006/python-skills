"""INERT EVALUATION EXAMPLE: SQL built by string formatting."""
import sqlite3


def find_user(conn: sqlite3.Connection, name: str):
    # Unsafe on purpose: caller-supplied text is interpolated into SQL.
    return conn.execute(f"SELECT * FROM users WHERE name = '{name}'").fetchall()


def find_user_safely(conn: sqlite3.Connection, name: str):
    return conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchall()
