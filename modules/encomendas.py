"""
Módulo de Encomendas.
Fluxo: recebimento → notificação automática → retirada com senha do morador.
A senha de confirmação é validada pelo sistema — o operador não pode "pular" essa etapa.
"""

from datetime import datetime
from db.database import get_connection
from modules.auditoria import registrar

def _buscar_morador(unidade: str):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM moradores WHERE unidade = ? AND ativo = 1", (unidade,)
        ).fetchone()
    finally:
        conn.close()

def _simular_notificacao(morador_nome: str, unidade: str, descricao: str, encomenda_id: int):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"\n  {'─'*55}")
    print(f"  📦 [NOTIFICAÇÃO AUTOMÁTICA]")
    print(f"  Para:      {morador_nome} — Unidade {unidade}")
    print(f"  Mensagem:  Nova encomenda recebida: '{descricao}'.")
    print(f"             Protocolo #{encomenda_id} — {agora}")
    print(f"             Retire na portaria com sua senha de confirmação.")
    print(f"  {'─'*55}\n")

def receber_encomenda(
    descricao: str,
    unidade_destino: str,
    operador_id: int,
    codigo_rastreio: str = "",
    remetente: str = "",
) -> dict:
    morador = _buscar_morador(unidade_destino)
    if not morador:
        return {"ok": False, "mensagem": f"Unidade '{unidade_destino}' não encontrada ou inativa."}

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO encomendas
                (codigo_rastreio, descricao, remetente, unidade_destino, operador_id, status)
            VALUES (?, ?, ?, ?, ?, 'recebida')
            """,
            (codigo_rastreio, descricao, remetente, unidade_destino, operador_id),
        )
        enc_id = cursor.lastrowid

        conn.execute(
            "UPDATE encomendas SET status = 'notificado' WHERE id = ?", (enc_id,)
        )
        conn.commit()

        registrar(
            acao="ENCOMENDA_RECEBIDA",
            modulo="encomenda",
            payload={
                "encomenda_id": enc_id,
                "descricao": descricao,
                "unidade": unidade_destino,
                "rastreio": codigo_rastreio,
                "remetente": remetente,
                "morador": morador["nome"],
            },
            operador_id=operador_id,
        )

        _simular_notificacao(morador["nome"], unidade_destino, descricao, enc_id)

        return {
            "ok": True,
            "encomenda_id": enc_id,
            "mensagem": f"Encomenda #{enc_id} registrada e morador notificado.",
        }
    finally:
        conn.close()

def retirar_encomenda(
    encomenda_id: int,
    senha_confirmacao: str,
    retirada_por: str,
    operador_id: int,
) -> dict:
    conn = get_connection()
    try:
        enc = conn.execute(
            "SELECT * FROM encomendas WHERE id = ?", (encomenda_id,)
        ).fetchone()

        if not enc:
            return {"ok": False, "mensagem": "Encomenda não encontrada."}

        if enc["status"] == "retirada":
            return {"ok": False, "mensagem": "Esta encomenda já foi retirada."}

        if enc["status"] == "recebida":
            return {"ok": False, "mensagem": "Encomenda ainda não notificada ao morador."}

        morador = _buscar_morador(enc["unidade_destino"])
        if not morador:
            return {"ok": False, "mensagem": "Morador não encontrado para validação de senha."}

        # ── VALIDAÇÃO DA SENHA (regra de negócio inviolável) ──────

        if morador["senha_encomenda"] != senha_confirmacao.strip():
            registrar(
                acao="RETIRADA_SENHA_INVALIDA",
                modulo="encomenda",
                payload={
                    "encomenda_id": encomenda_id,
                    "unidade": enc["unidade_destino"],
                    "tentativa_retirada_por": retirada_por,
                },
                operador_id=operador_id,
            )
            return {"ok": False, "mensagem": "❌ Senha de confirmação inválida. Retirada NÃO autorizada."}

        # Senha correta → efetua retirada
        
        retirada_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            UPDATE encomendas
            SET status = 'retirada', retirada_em = ?, retirada_por = ?
            WHERE id = ?
            """,
            (retirada_em, retirada_por, encomenda_id),
        )
        conn.commit()

        registrar(
            acao="ENCOMENDA_RETIRADA",
            modulo="encomenda",
            payload={
                "encomenda_id": encomenda_id,
                "unidade": enc["unidade_destino"],
                "retirada_por": retirada_por,
                "retirada_em": retirada_em,
            },
            operador_id=operador_id,
        )
        return {
            "ok": True,
            "mensagem": f"✅ Encomenda #{encomenda_id} retirada com sucesso por '{retirada_por}'.",
        }
    finally:
        conn.close()

def listar_encomendas_pendentes() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT e.*, o.nome AS operador_nome
            FROM encomendas e
            JOIN operadores o ON o.id = e.operador_id
            WHERE e.status IN ('recebida', 'notificado')
            ORDER BY e.recebida_em DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def listar_encomendas_recentes(limite: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT e.*, o.nome AS operador_nome
            FROM encomendas e
            JOIN operadores o ON o.id = e.operador_id
            ORDER BY e.recebida_em DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()