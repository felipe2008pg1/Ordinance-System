"""
Authentication and Operator/Resident Management Module.
Uses SHA-256 for password hashing (no external dependencies).
"""

import hashlib
from db.database import get_connection
from modules.audit_log import record

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ── AUTHENTICATION ────────────────────────────────────────────────────────────

def authenticate(username: str, password: str) -> dict | None:
    """Returns the operator dict if credentials are valid, None otherwise."""
    conn = get_connection()

    try:
        operator = conn.execute(
            "SELECT * FROM operators WHERE username = ? AND active = 1",
            (username,),
        ).fetchone()

        if operator and operator["password_hash"] == _hash_password(password):
            record(
                action="LOGIN_SUCCESS",
                module="system",
                payload={
                    "username": username,
                    "role": operator["role"],
                },
                operator_id=operator["id"],
            )

            return dict(operator)

        record(
            action="LOGIN_FAILED",
            module="system",
            payload={
                "username": username,
                "reason": "invalid credentials",
            },
        )

        return None

    finally:
        conn.close()

# ── OPERATORS ────────────────────────────────────────────────────────────────

def create_operator(
    name: str,
    username: str,
    password: str,
    role: str,
    created_by_id: int,
) -> dict:
    conn = get_connection()

    try:
        existing = conn.execute(
            "SELECT id FROM operators WHERE username = ?",
            (username,),
        ).fetchone()

        if existing:
            return {
                "ok": False,
                "message": f"Username '{username}' is already in use.",
            }

        cursor = conn.execute(
            """
            INSERT INTO operators
                (name, username, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                username,
                _hash_password(password),
                role,
            ),
        )

        operator_id = cursor.lastrowid
        conn.commit()

        record(
            action="OPERATOR_CREATED",
            module="operator",
            payload={
                "new_operator_id": operator_id,
                "username": username,
                "role": role,
            },
            operator_id=created_by_id,
        )

        return {
            "ok": True,
            "operator_id": operator_id,
            "message": f"Operator '{name}' created successfully.",
        }

    finally:
        conn.close()

def list_operators() -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT id,
                   name,
                   username,
                   role,
                   active,
                   created_at
            FROM operators
            ORDER BY name
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()

def deactivate_operator(operator_id: int, admin_id: int) -> dict:
    conn = get_connection()

    try:
        operator = conn.execute(
            "SELECT * FROM operators WHERE id = ?",
            (operator_id,),
        ).fetchone()

        if not operator:
            return {
                "ok": False,
                "message": "Operator not found.",
            }

        elif operator["id"] == admin_id:
            return {
                "ok": False,
                "message": "You cannot deactivate your own account.",
            }

        conn.execute(
            "UPDATE operators SET active = 0 WHERE id = ?",
            (operator_id,),
        )

        conn.commit()

        record(
            action="OPERATOR_DEACTIVATED",
            module="operator",
            payload={
                "operator_id": operator_id,
                "username": operator["username"],
            },
            operator_id=admin_id,
        )

        return {
            "ok": True,
            "message": f"Operator '{operator['name']}' deactivated.",
        }

    finally:
        conn.close()

# ── RESIDENTS ────────────────────────────────────────────────────────────────

def create_resident(
    name: str,
    unit: str,
    package_password: str,
    operator_id: int,
    phone: str = "",
) -> dict:
    conn = get_connection()

    try:
        existing = conn.execute(
            "SELECT id FROM residents WHERE unit = ?",
            (unit,),
        ).fetchone()

        if existing:
            return {
                "ok": False,
                "message": f"Unit '{unit}' is already registered.",
            }

        cursor = conn.execute(
            """
            INSERT INTO residents
                (name, unit, phone, package_password)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                unit,
                phone,
                package_password,
            ),
        )

        resident_id = cursor.lastrowid
        conn.commit()

        record(
            action="RESIDENT_CREATED",
            module="resident",
            payload={
                "resident_id": resident_id,
                "name": name,
                "unit": unit,
            },
            operator_id=operator_id,
        )

        return {
            "ok": True,
            "resident_id": resident_id,
            "message": (
                f"Resident '{name}' — Unit {unit} registered successfully."
            ),
        }

    finally:
        conn.close()

def list_residents() -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT id,
                   name,
                   unit,
                   phone,
                   active,
                   created_at
            FROM residents
            ORDER BY unit
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()

def deactivate_resident(resident_id: int, operator_id: int) -> dict:
    conn = get_connection()

    try:
        resident = conn.execute(
            "SELECT * FROM residents WHERE id = ?",
            (resident_id,),
        ).fetchone()

        if not resident:
            return {
                "ok": False,
                "message": "Resident not found.",
            }

        conn.execute(
            "UPDATE residents SET active = 0 WHERE id = ?",
            (resident_id,),
        )

        conn.commit()

        record(
            action="RESIDENT_DEACTIVATED",
            module="resident",
            payload={
                "resident_id": resident_id,
                "unit": resident["unit"],
            },
            operator_id=operator_id,
        )

        return {
            "ok": True,
            "message": f"Resident '{resident['name']}' deactivated.",
        }

    finally:
        conn.close()
