"""
SQLite database connection and initialization module.
All tables are created here, including the immutable audit table.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "gatehouse.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ── OPERATORS ────────────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            username        TEXT    NOT NULL UNIQUE,
            password_hash   TEXT    NOT NULL,
            role            TEXT    NOT NULL CHECK(role IN ('admin', 'doorman')),
            active          INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── RESIDENTS ────────────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS residents (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            unit                TEXT    NOT NULL UNIQUE,
            phone               TEXT,
            package_password    TEXT    NOT NULL,
            active              INTEGER NOT NULL DEFAULT 1,
            created_at          TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── ACCESS RULES ─────────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_rules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            description     TEXT    NOT NULL,
            visitor_type    TEXT    NOT NULL CHECK(visitor_type IN ('visitor','service_provider','delivery','all')),
            start_time      TEXT    NOT NULL,
            end_time        TEXT    NOT NULL,
            weekdays        TEXT    NOT NULL,
            active          INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ── VISITS ──────────────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_name        TEXT    NOT NULL,
            type                TEXT    NOT NULL CHECK(type IN ('visitor','service_provider','delivery')),
            document            TEXT,
            destination_unit    TEXT    NOT NULL,
            operator_id         INTEGER NOT NULL REFERENCES operators(id),
            status              TEXT    NOT NULL DEFAULT 'pending'
                                        CHECK(status IN ('pending','authorized','denied','checked_out')),
            denial_reason       TEXT,
            checked_in_at       TEXT,
            checked_out_at      TEXT,
            created_at          TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── PACKAGES ────────────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code       TEXT,
            description         TEXT    NOT NULL,
            sender              TEXT,
            destination_unit    TEXT    NOT NULL REFERENCES residents(unit),
            operator_id         INTEGER NOT NULL REFERENCES operators(id),
            status              TEXT    NOT NULL DEFAULT 'received'
                                        CHECK(status IN ('received','notified','picked_up')),
            received_at         TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            picked_up_at        TEXT,
            picked_up_by        TEXT
        )
    """)

    # ── AUDIT LOG (IMMUTABLE) ───────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id     INTEGER REFERENCES operators(id),
            action          TEXT    NOT NULL,
            module          TEXT    NOT NULL CHECK(module IN ('access','package','system','operator','resident')),
            payload_json    TEXT    NOT NULL,
            source_ip       TEXT,
            recorded_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # Trigger: Prevent UPDATE on audit_log

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS block_audit_update
        BEFORE UPDATE ON audit_log
        BEGIN
            SELECT RAISE(ABORT, 'VIOLATION: audit records are immutable.');
        END
    """)

    # Trigger: Prevent DELETE on audit_log

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS block_audit_delete
        BEFORE DELETE ON audit_log
        BEGIN
            SELECT RAISE(ABORT, 'VIOLATION: audit records cannot be deleted.');
        END
    """)

    conn.commit()
    conn.close()
