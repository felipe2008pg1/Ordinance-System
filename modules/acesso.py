"""
Smart Access Control Module.
Validates time, visitor type, and registered rules BEFORE allowing entry.
The operator CANNOT override a denial — the rule is sovereign.
"""

from datetime import datetime
from db.database import get_connection
from modules.audit_log import record

# Mapping of weekdays to abbreviations used in the rules
_WEEKDAYS = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}


def _current_time() -> str:
    return datetime.now().strftime("%H:%M")


def _current_weekday() -> str:
    return _WEEKDAYS[datetime.now().weekday()]


def check_rules(visitor_type: str) -> tuple[bool, str]:
    conn = get_connection()

    try:
        rules = conn.execute(
            """
            SELECT * FROM access_rules
            WHERE active = 1
              AND (visitor_type = ? OR visitor_type = 'all')
            """,
            (visitor_type,),
        ).fetchall()

        if not rules:
            return False, f"No access rule registered for '{visitor_type}'."

        current_time = _current_time()
        current_weekday = _current_weekday()

        for rule in rules:
            allowed_days = [
                day.strip()
                for day in rule["weekdays"].split(",")
            ]

            if current_weekday not in allowed_days:
                continue

            if rule["start_time"] <= current_time <= rule["end_time"]:
                return (
                    True,
                    f"Access granted by rule: '{rule['description']}'.",
                )

        return (
            False,
            f"Access BLOCKED. Type '{visitor_type}' is not allowed "
            f"on {current_weekday} at {current_time}.",
        )

    finally:
        conn.close()


def register_visit(
    visitor_name: str,
    type: str,
    destination_unit: str,
    operator_id: int,
    document: str = "",
) -> dict:
    allowed, reason = check_rules(type)

    conn = get_connection()

    try:
        if allowed:
            status = "authorized"
            checked_in_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor = conn.execute(
                """
                INSERT INTO visits
                    (visitor_name, type, document, destination_unit,
                     operator_id, status, checked_in_at)
                VALUES (?, ?, ?, ?, ?, 'authorized', ?)
                """,
                (
                    visitor_name,
                    type,
                    document,
                    destination_unit,
                    operator_id,
                    checked_in_at,
                ),
            )

            visit_id = cursor.lastrowid
            conn.commit()

            record(
                action="ACCESS_GRANTED",
                module="access",
                payload={
                    "visit_id": visit_id,
                    "visitor": visitor_name,
                    "type": type,
                    "unit": destination_unit,
                    "document": document,
                    "reason": reason,
                },
                operator_id=operator_id,
            )

            return {
                "ok": True,
                "visit_id": visit_id,
                "message": reason,
            }

        else:
            cursor = conn.execute(
                """
                INSERT INTO visits
                    (visitor_name, type, document, destination_unit,
                     operator_id, status, denial_reason)
                VALUES (?, ?, ?, ?, ?, 'denied', ?)
                """,
                (
                    visitor_name,
                    type,
                    document,
                    destination_unit,
                    operator_id,
                    reason,
                ),
            )

            visit_id = cursor.lastrowid
            conn.commit()

            record(
                action="ACCESS_DENIED",
                module="access",
                payload={
                    "visit_id": visit_id,
                    "visitor": visitor_name,
                    "type": type,
                    "unit": destination_unit,
                    "reason": reason,
                },
                operator_id=operator_id,
            )

            return {
                "ok": False,
                "visit_id": visit_id,
                "message": reason,
            }

    finally:
        conn.close()


def register_checkout(visit_id: int, operator_id: int) -> dict:
    conn = get_connection()

    try:
        visit = conn.execute(
            "SELECT * FROM visits WHERE id = ?",
            (visit_id,),
        ).fetchone()

        if not visit:
            return {
                "ok": False,
                "message": "Visit not found.",
            }

        if visit["status"] != "authorized":
            return {
                "ok": False,
                "message": (
                    f"Current status '{visit['status']}' "
                    "does not allow checkout registration."
                ),
            }

        checked_out_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            """
            UPDATE visits
            SET status = 'checked_out',
                checked_out_at = ?
            WHERE id = ?
            """,
            (checked_out_at, visit_id),
        )

        conn.commit()

        record(
            action="CHECKOUT_REGISTERED",
            module="access",
            payload={
                "visit_id": visit_id,
                "visitor": visit["visitor_name"],
                "unit": visit["destination_unit"],
                "checked_in_at": visit["checked_in_at"],
                "checked_out_at": checked_out_at,
            },
            operator_id=operator_id,
        )

        return {
            "ok": True,
            "message": (
                f"Checkout for '{visit['visitor_name']}' "
                "registered successfully."
            ),
        }

    finally:
        conn.close()


def list_active_visits() -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT v.*, o.name AS operator_name
            FROM visits v
            JOIN operators o ON o.id = v.operator_id
            WHERE v.status = 'authorized'
            ORDER BY v.checked_in_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def list_recent_visits(limit: int = 20) -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT v.*, o.name AS operator_name
            FROM visits v
            JOIN operators o ON o.id = v.operator_id
            ORDER BY v.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


# ── ACCESS RULE CRUD ─────────────────────────────────────────────────────────


def create_rule(
    description: str,
    visitor_type: str,
    start_time: str,
    end_time: str,
    weekdays: str,
    operator_id: int,
) -> int:
    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO access_rules
                (description, visitor_type, start_time, end_time, weekdays)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                description,
                visitor_type,
                start_time,
                end_time,
                weekdays,
            ),
        )

        rule_id = cursor.lastrowid
        conn.commit()

        record(
            action="RULE_CREATED",
            module="access",
            payload={
                "rule_id": rule_id,
                "description": description,
                "visitor_type": visitor_type,
                "start_time": start_time,
                "end_time": end_time,
                "weekdays": weekdays,
            },
            operator_id=operator_id,
        )

        return rule_id

    finally:
        conn.close()


def list_rules() -> list[dict]:
    conn = get_connection()

    try:
        rows = conn.execute(
            "SELECT * FROM access_rules ORDER BY id"
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def deactivate_rule(rule_id: int, operator_id: int) -> bool:
    conn = get_connection()

    try:
        conn.execute(
            "UPDATE access_rules SET active = 0 WHERE id = ?",
            (rule_id,),
        )

        conn.commit()

        record(
            action="RULE_DEACTIVATED",
            module="access",
            payload={
                "rule_id": rule_id,
            },
            operator_id=operator_id,
        )

        return True

    finally:
        conn.close()
