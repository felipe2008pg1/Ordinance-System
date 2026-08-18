"""
Audit Trail — the heart of the system.
Every action performed in the system passes through here.
Records are append-only: no UPDATE or DELETE is allowed (enforced via SQL trigger).
"""
import json
from datetime import datetime
from db.database import get_connection

def record(
    action: str,
    module: str,
    payload: dict,
    operator_id: int | None = None,
    source_ip: str | None = None,
):
    """
    Records an immutable event in the audit trail.

    Args:
        action:       Description of the action (e.g. 'ACCESS_DENIED', 'PACKAGE_RECEIVED').
        module:       System pillar: 'access' | 'package' | 'system' | 'operator' | 'resident'.
        payload:      Dict containing relevant event data (serialized as JSON).
        operator_id:  ID of the operator who performed the action
                      (None for automatic system actions).
        source_ip:    Session IP address, when available.
    """
    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO audit_log
                (operator_id, action, module, payload_json, source_ip)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                operator_id,
                action.upper(),
                module,
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    default=str,
                ),
                source_ip,
            ),
        )

        conn.commit()

    finally:
        conn.close()

def search_audit_trail(
    module: str | None = None,
    operator_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Queries the audit trail with optional filters."""

    conn = get_connection()

    try:
        query = """
            SELECT a.id,
                   a.action,
                   a.module,
                   a.payload_json,
                   a.source_ip,
                   a.recorded_at,
                   o.name AS operator_name,
                   o.username AS operator_username
            FROM audit_log a
            LEFT JOIN operators o ON o.id = a.operator_id
            WHERE 1=1
        """

        params = []

        if module:
            query += " AND a.module = ?"
            params.append(module)

        elif operator_id:
            query += " AND a.operator_id = ?"
            params.append(operator_id)

        elif start_date:
            query += " AND a.recorded_at >= ?"
            params.append(start_date)

        elif end_date:
            query += " AND a.recorded_at <= ?"
            params.append(end_date + " 23:59:59")

        query += " ORDER BY a.id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()

def get_total_events() -> int:
    conn = get_connection()

    try:
        return conn.execute(
            "SELECT COUNT(*) FROM audit_log"
        ).fetchone()[0]

    finally:
        conn.close()
