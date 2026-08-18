"""
Package Management Module.
Flow: receiving → automatic notification → pickup with the resident's password.
The confirmation password is validated by the system — the operator cannot skip this step.
"""

from datetime import datetime
from db.database import get_connection
from modules.audit_log import record

def _find_resident(unit: str):
    conn = get_connection()

    try:
        return conn.execute(
            "SELECT * FROM residents WHERE unit = ? AND active = 1",
            (unit,),
        ).fetchone()

    finally:
        conn.close()

def _simulate_notification(
    resident_name: str,
    unit: str,
    description: str,
    package_id: int,
):
    current_time = datetime.now().strftime("%m/%d/%Y %H:%M")

    print(f"\n  {'─' * 55}")
    print("  📦 [AUTOMATIC NOTIFICATION]")
    print(f"  To:         {resident_name} — Unit {unit}")
    print(f"  Message:    New package received: '{description}'.")
    print(f"              Reference #{package_id} — {current_time}")
    print("              Pick it up at the gatehouse with your confirmation password.")
    print(f"  {'─' * 55}\n")

def receive_package(
    description: str,
    destination_unit: str,
    operator_id: int,
    tracking_code: str = "",
    sender: str = "",
) -> dict:
    resident = _find_resident(destination_unit)

    if not resident:
        return {
            "ok": False,
            "message": (
                f"Unit '{destination_unit}' not found or inactive."
            ),
        }

    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO packages
                (
                    tracking_code,
                    description,
                    sender,
                    destination_unit,
                    operator_id,
                    status
                )
            VALUES (?, ?, ?, ?, ?, 'received')
            """,
            (
                tracking_code,
                description,
                sender,
                destination_unit,
                operator_id,
            ),
        )

        package_id = cursor.lastrowid

        conn.execute(
            "UPDATE packages SET status = 'notified' WHERE id = ?",
            (package_id,),
        )

        conn.commit()

        record(
            action="PACKAGE_RECEIVED",
            module="package",
            payload={
                "package_id": package_id,
                "description": description,
                "unit": destination_unit,
                "tracking_code": tracking_code,
                "sender": sender,
                "resident": resident["name"],
            },
            operator_id=operator_id,
        )

        _simulate_notification(
            resident["name"],
            destination_unit,
            description,
            package_id,
        )

        return {
            "ok": True,
            "package_id": package_id,
            "message": (
                f"Package #{package_id} registered "
                "and resident notified."
            ),
        }

    finally:
        conn.close()

def pick_up_package(
    package_id: int,
    confirmation_password: str,
    picked_up_by: str,
    operator_id: int,
) -> dict:
    conn = get_connection()

    try:
        package = conn.execute(
            "SELECT * FROM packages WHERE id = ?",
            (package_id,),
        ).fetchone()

        if not package:
            return {
                "ok": False,
                "message": "Package not found.",
            }

        elif package["status"] == "picked_up":
            return {
                "ok": False,
                "message": "This package has already been picked up.",
            }

        elif package["status"] == "received":
            return {
                "ok": False,
                "message": "Package has not been notified to the resident yet.",
            }

        resident = _find_resident(package["destination_unit"])

        if not resident:
            return {
                "ok": False,
                "message": "Resident not found for password validation.",
            }

        # ── PASSWORD VALIDATION (immutable business rule) ─────────

        if resident["package_password"] != confirmation_password.strip():
            record(
                action="PACKAGE_PICKUP_INVALID_PASSWORD",
                module="package",
                payload={
                    "package_id": package_id,
                    "unit": package["destination_unit"],
                    "pickup_attempted_by": picked_up_by,
                },
                operator_id=operator_id,
            )

            return {
                "ok": False,
                "message": (
                    "❌ Invalid confirmation password. "
                    "Pickup NOT authorized."
                ),
            }

        # Correct password → complete pickup

        picked_up_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            """
            UPDATE packages
            SET status = 'picked_up',
                picked_up_at = ?,
                picked_up_by = ?
            WHERE id = ?
            """,
            (
                picked_up_at,
                picked_up_by,
                package_id,
            ),
        )

        conn.commit()

        record(
            action="PACKAGE_PICKED_UP",
            module="package",
            payload={
                "package_id": package_id,
                "unit": package["destination_unit"],
                "picked_up_by": picked_up_by,
                "picked_up_at": picked_up_at,
            },
            operator_id=operator_id,
        )

        return {
            "ok": True,
            "message": (
                f"✅ Package #{package_id} successfully picked up "
                f"by '{picked_up_by}'."
            ),
        }

    finally:
        conn.close()

def list_pending_packages() -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT p.*, o.name AS operator_name
            FROM packages p
            JOIN operators o ON o.id = p.operator_id
            WHERE p.status IN ('received', 'notified')
            ORDER BY p.received_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()

def list_recent_packages(limit: int = 20) -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT p.*, o.name AS operator_name
            FROM packages p
            JOIN operators o ON o.id = p.operator_id
            ORDER BY p.received_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()
