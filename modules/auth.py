"""
Módulo de Autenticação e Gestão de Operadores/Moradores.
Usa SHA-256 para hash de senhas (sem dependências externas).
"""

import hashlib
from db.database import get_connection
from modules.auditoria import registrar

def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

# ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────────

def autenticar(login: str, senha: str) -> dict | None:
    """Retorna dict do operador se credenciais válidas, None caso contrário."""
    conn = get_connection()
    try:
        op = conn.execute(
            "SELECT * FROM operadores WHERE login = ? AND ativo = 1", (login,)
        ).fetchone()
        if op and op["senha_hash"] == _hash_senha(senha):
            registrar(
                acao="LOGIN_OK",
                modulo="sistema",
                payload={"login": login, "perfil": op["perfil"]},
                operador_id=op["id"],
            )
            return dict(op)

        registrar(
            acao="LOGIN_FALHOU",
            modulo="sistema",
            payload={"login": login, "motivo": "credenciais inválidas"},
        )
        return None
    finally:
        conn.close()

# ── OPERADORES ────────────────────────────────────────────────────────────────

def criar_operador(
    nome: str,
    login: str,
    senha: str,
    perfil: str,
    criado_por_id: int,
) -> dict:
    conn = get_connection()
    try:
        existente = conn.execute(
            "SELECT id FROM operadores WHERE login = ?", (login,)
        ).fetchone()
        if existente:
            return {"ok": False, "mensagem": f"Login '{login}' já está em uso."}

        cursor = conn.execute(
            "INSERT INTO operadores (nome, login, senha_hash, perfil) VALUES (?, ?, ?, ?)",
            (nome, login, _hash_senha(senha), perfil),
        )
        op_id = cursor.lastrowid
        conn.commit()

        registrar(
            acao="OPERADOR_CRIADO",
            modulo="operador",
            payload={"novo_operador_id": op_id, "login": login, "perfil": perfil},
            operador_id=criado_por_id,
        )
        return {"ok": True, "operador_id": op_id, "mensagem": f"Operador '{nome}' criado com sucesso."}
    finally:
        conn.close()

def listar_operadores() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nome, login, perfil, ativo, criado_em FROM operadores ORDER BY nome"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def desativar_operador(op_id: int, admin_id: int) -> dict:
    conn = get_connection()
    try:
        op = conn.execute("SELECT * FROM operadores WHERE id = ?", (op_id,)).fetchone()
        if not op:
            return {"ok": False, "mensagem": "Operador não encontrado."}
        if op["id"] == admin_id:
            return {"ok": False, "mensagem": "Você não pode desativar sua própria conta."}

        conn.execute("UPDATE operadores SET ativo = 0 WHERE id = ?", (op_id,))
        conn.commit()

        registrar(
            acao="OPERADOR_DESATIVADO",
            modulo="operador",
            payload={"operador_id": op_id, "login": op["login"]},
            operador_id=admin_id,
        )
        return {"ok": True, "mensagem": f"Operador '{op['nome']}' desativado."}
    finally:
        conn.close()

# ── MORADORES ─────────────────────────────────────────────────────────────────

def criar_morador(
    nome: str,
    unidade: str,
    senha_encomenda: str,
    operador_id: int,
    telefone: str = "",
) -> dict:
    conn = get_connection()
    try:
        existente = conn.execute(
            "SELECT id FROM moradores WHERE unidade = ?", (unidade,)
        ).fetchone()
        if existente:
            return {"ok": False, "mensagem": f"Unidade '{unidade}' já cadastrada."}

        cursor = conn.execute(
            "INSERT INTO moradores (nome, unidade, telefone, senha_encomenda) VALUES (?, ?, ?, ?)",
            (nome, unidade, telefone, senha_encomenda),
        )
        mor_id = cursor.lastrowid
        conn.commit()

        registrar(
            acao="MORADOR_CRIADO",
            modulo="morador",
            payload={"morador_id": mor_id, "nome": nome, "unidade": unidade},
            operador_id=operador_id,
        )
        return {"ok": True, "morador_id": mor_id, "mensagem": f"Morador '{nome}' — Unidade {unidade} cadastrado."}
    finally:
        conn.close()

def listar_moradores() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nome, unidade, telefone, ativo, criado_em FROM moradores ORDER BY unidade"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def desativar_morador(mor_id: int, operador_id: int) -> dict:
    conn = get_connection()
    try:
        mor = conn.execute("SELECT * FROM moradores WHERE id = ?", (mor_id,)).fetchone()
        if not mor:
            return {"ok": False, "mensagem": "Morador não encontrado."}
        conn.execute("UPDATE moradores SET ativo = 0 WHERE id = ?", (mor_id,))
        conn.commit()
        registrar(
            acao="MORADOR_DESATIVADO",
            modulo="morador",
            payload={"morador_id": mor_id, "unidade": mor["unidade"]},
            operador_id=operador_id,
        )
        return {"ok": True, "mensagem": f"Morador '{mor['nome']}' desativado."}
    finally:
        conn.close()