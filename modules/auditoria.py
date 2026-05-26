"""
Trilha de Auditoria — coração do sistema.
Toda ação realizada no sistema passa por aqui.
Registros são append-only: nenhum UPDATE ou DELETE é permitido (garantido via trigger SQL).
"""

import json
from datetime import datetime
from db.database import get_connection

def registrar(
    acao: str,
    modulo: str,
    payload: dict,
    operador_id: int | None = None,
    ip_origem: str | None = None,
):
    """
    Grava um evento imutável na trilha de auditoria.

    Args:
        acao:        Descrição da ação (ex: 'ACESSO_NEGADO', 'ENCOMENDA_RECEBIDA').
        modulo:      Pilar do sistema: 'acesso' | 'encomenda' | 'sistema' | 'operador' | 'morador'.
        payload:     Dict com os dados relevantes do evento (serializado em JSON).
        operador_id: ID do operador que executou a ação (None para ações automáticas do sistema).
        ip_origem:   IP da sessão, quando disponível.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO auditoria (operador_id, acao, modulo, payload_json, ip_origem)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                operador_id,
                acao.upper(),
                modulo,
                json.dumps(payload, ensure_ascii=False, default=str),
                ip_origem,
            ),
        )
        conn.commit()
    finally:
        conn.close()

def buscar_trilha(
    modulo: str | None = None,
    operador_id: int | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    limite: int = 50,
) -> list[dict]:
    """Consulta a trilha de auditoria com filtros opcionais."""
    conn = get_connection()
    try:
        query = """
            SELECT a.id, a.acao, a.modulo, a.payload_json,
                   a.ip_origem, a.registrado_em,
                   o.nome AS operador_nome, o.login AS operador_login
            FROM auditoria a
            LEFT JOIN operadores o ON o.id = a.operador_id
            WHERE 1=1
        """
        params = []

        if modulo:
            query += " AND a.modulo = ?"
            params.append(modulo)
        if operador_id:
            query += " AND a.operador_id = ?"
            params.append(operador_id)
        if data_inicio:
            query += " AND a.registrado_em >= ?"
            params.append(data_inicio)
        if data_fim:
            query += " AND a.registrado_em <= ?"
            params.append(data_fim + " 23:59:59")

        query += " ORDER BY a.id DESC LIMIT ?"
        params.append(limite)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def total_eventos() -> int:
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
    finally:
        conn.close()