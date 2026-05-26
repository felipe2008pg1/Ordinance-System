"""
Módulo de Controle de Acesso Inteligente.
Valida horário, tipo de visitante e regras cadastradas ANTES de permitir entrada.
O operador NÃO pode sobrescrever uma negação — a regra é soberana.
"""

from datetime import datetime
from db.database import get_connection
from modules.auditoria import registrar

# Mapeamento de dia da semana para abreviação usada nas regras
_DIAS = {0: "seg", 1: "ter", 2: "qua", 3: "qui", 4: "sex", 5: "sab", 6: "dom"}

def _hora_atual() -> str:
    return datetime.now().strftime("%H:%M")

def _dia_atual() -> str:
    return _DIAS[datetime.now().weekday()]

def verificar_regras(tipo_visita: str) -> tuple[bool, str]:
    conn = get_connection()
    try:
        regras = conn.execute(
            """
            SELECT * FROM regras_acesso
            WHERE ativo = 1
              AND (tipo_visita = ? OR tipo_visita = 'todos')
            """,
            (tipo_visita,),
        ).fetchall()

        if not regras:
            return False, f"Nenhuma regra de acesso cadastrada para '{tipo_visita}'."

        hora_agora = _hora_atual()
        dia_agora = _dia_atual()

        for regra in regras:
            dias_permitidos = [d.strip() for d in regra["dias_semana"].split(",")]
            if dia_agora not in dias_permitidos:
                continue
            if regra["hora_inicio"] <= hora_agora <= regra["hora_fim"]:
                return True, f"Acesso permitido pela regra: '{regra['descricao']}'."

        return (
            False,
            f"Acesso BLOQUEADO. Tipo '{tipo_visita}' não permitido em {dia_agora} às {hora_agora}.",
        )
    finally:
        conn.close()

def registrar_visita(
    nome_visitante: str,
    tipo: str,
    unidade_destino: str,
    operador_id: int,
    documento: str = "",
) -> dict:
    permitido, motivo = verificar_regras(tipo)

    conn = get_connection()
    try:
        if permitido:
            status = "autorizado"
            entrada_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.execute(
                """
                INSERT INTO visitas
                    (nome_visitante, tipo, documento, unidade_destino,
                     operador_id, status, entrada_em)
                VALUES (?, ?, ?, ?, ?, 'autorizado', ?)
                """,
                (nome_visitante, tipo, documento, unidade_destino, operador_id, entrada_em),
            )
            visita_id = cursor.lastrowid
            conn.commit()

            registrar(
                acao="ACESSO_AUTORIZADO",
                modulo="acesso",
                payload={
                    "visita_id": visita_id,
                    "visitante": nome_visitante,
                    "tipo": tipo,
                    "unidade": unidade_destino,
                    "documento": documento,
                    "motivo": motivo,
                },
                operador_id=operador_id,
            )
            return {"ok": True, "visita_id": visita_id, "mensagem": motivo}

        else:
            cursor = conn.execute(
                """
                INSERT INTO visitas
                    (nome_visitante, tipo, documento, unidade_destino,
                     operador_id, status, motivo_negacao)
                VALUES (?, ?, ?, ?, ?, 'negado', ?)
                """,
                (nome_visitante, tipo, documento, unidade_destino, operador_id, motivo),
            )
            visita_id = cursor.lastrowid
            conn.commit()

            registrar(
                acao="ACESSO_NEGADO",
                modulo="acesso",
                payload={
                    "visita_id": visita_id,
                    "visitante": nome_visitante,
                    "tipo": tipo,
                    "unidade": unidade_destino,
                    "motivo": motivo,
                },
                operador_id=operador_id,
            )
            return {"ok": False, "visita_id": visita_id, "mensagem": motivo}
    finally:
        conn.close()

def registrar_saida(visita_id: int, operador_id: int) -> dict:
    conn = get_connection()
    try:
        visita = conn.execute(
            "SELECT * FROM visitas WHERE id = ?", (visita_id,)
        ).fetchone()

        if not visita:
            return {"ok": False, "mensagem": "Visita não encontrada."}
        if visita["status"] != "autorizado":
            return {"ok": False, "mensagem": f"Status atual '{visita['status']}' não permite registrar saída."}

        saida_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE visitas SET status = 'saida', saida_em = ? WHERE id = ?",
            (saida_em, visita_id),
        )
        conn.commit()

        registrar(
            acao="SAIDA_REGISTRADA",
            modulo="acesso",
            payload={
                "visita_id": visita_id,
                "visitante": visita["nome_visitante"],
                "unidade": visita["unidade_destino"],
                "entrada_em": visita["entrada_em"],
                "saida_em": saida_em,
            },
            operador_id=operador_id,
        )
        return {"ok": True, "mensagem": f"Saída de '{visita['nome_visitante']}' registrada com sucesso."}
    finally:
        conn.close()

def listar_visitas_ativas() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT v.*, o.nome AS operador_nome
            FROM visitas v
            JOIN operadores o ON o.id = v.operador_id
            WHERE v.status = 'autorizado'
            ORDER BY v.entrada_em DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def listar_visitas_recentes(limite: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT v.*, o.nome AS operador_nome
            FROM visitas v
            JOIN operadores o ON o.id = v.operador_id
            ORDER BY v.criado_em DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

# ── CRUD DE REGRAS ────────────────────────────────────────────────────────────

def criar_regra(
    descricao: str,
    tipo_visita: str,
    hora_inicio: str,
    hora_fim: str,
    dias_semana: str,
    operador_id: int,
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO regras_acesso
                (descricao, tipo_visita, hora_inicio, hora_fim, dias_semana)
            VALUES (?, ?, ?, ?, ?)
            """,
            (descricao, tipo_visita, hora_inicio, hora_fim, dias_semana),
        )
        regra_id = cursor.lastrowid
        conn.commit()

        registrar(
            acao="REGRA_CRIADA",
            modulo="acesso",
            payload={
                "regra_id": regra_id,
                "descricao": descricao,
                "tipo_visita": tipo_visita,
                "hora_inicio": hora_inicio,
                "hora_fim": hora_fim,
                "dias_semana": dias_semana,
            },
            operador_id=operador_id,
        )
        return regra_id
    finally:
        conn.close()

def listar_regras() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM regras_acesso ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def desativar_regra(regra_id: int, operador_id: int) -> bool:
    conn = get_connection()
    try:
        conn.execute("UPDATE regras_acesso SET ativo = 0 WHERE id = ?", (regra_id,))
        conn.commit()
        registrar(
            acao="REGRA_DESATIVADA",
            modulo="acesso",
            payload={"regra_id": regra_id},
            operador_id=operador_id,
        )
        return True
    finally:
        conn.close()