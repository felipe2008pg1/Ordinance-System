"""
Módulo de conexão e inicialização do banco de dados SQLite.
Todas as tabelas são criadas aqui, incluindo a tabela de auditoria imutável.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "portaria.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ── OPERADORES ────────────────────────────────────────────────
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operadores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT    NOT NULL,
            login       TEXT    NOT NULL UNIQUE,
            senha_hash  TEXT    NOT NULL,
            perfil      TEXT    NOT NULL CHECK(perfil IN ('admin', 'porteiro')),
            ativo       INTEGER NOT NULL DEFAULT 1,
            criado_em   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── MORADORES ─────────────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moradores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            unidade         TEXT    NOT NULL UNIQUE,
            telefone        TEXT,
            senha_encomenda TEXT    NOT NULL,
            ativo           INTEGER NOT NULL DEFAULT 1,
            criado_em       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── REGRAS DE ACESSO ──────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regras_acesso (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao    TEXT    NOT NULL,
            tipo_visita  TEXT    NOT NULL CHECK(tipo_visita IN ('visitante','prestador','entregador','todos')),
            hora_inicio  TEXT    NOT NULL,
            hora_fim     TEXT    NOT NULL,
            dias_semana  TEXT    NOT NULL,
            ativo        INTEGER NOT NULL DEFAULT 1
        )
    """)

    # ── VISITANTES / PRESTADORES ──────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_visitante  TEXT    NOT NULL,
            tipo            TEXT    NOT NULL CHECK(tipo IN ('visitante','prestador','entregador')),
            documento       TEXT,
            unidade_destino TEXT    NOT NULL,
            operador_id     INTEGER NOT NULL REFERENCES operadores(id),
            status          TEXT    NOT NULL DEFAULT 'aguardando'
                                    CHECK(status IN ('aguardando','autorizado','negado','saida')),
            motivo_negacao  TEXT,
            entrada_em      TEXT,
            saida_em        TEXT,
            criado_em       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ── ENCOMENDAS ────────────────────────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_rastreio TEXT,
            descricao       TEXT    NOT NULL,
            remetente       TEXT,
            unidade_destino TEXT    NOT NULL REFERENCES moradores(unidade),
            operador_id     INTEGER NOT NULL REFERENCES operadores(id),
            status          TEXT    NOT NULL DEFAULT 'recebida'
                                    CHECK(status IN ('recebida','notificado','retirada')),
            recebida_em     TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            retirada_em     TEXT,
            retirada_por    TEXT
        )
    """)

    # ── TRILHA DE AUDITORIA (IMUTÁVEL) ────────────────────────────

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            operador_id  INTEGER REFERENCES operadores(id),
            acao         TEXT    NOT NULL,
            modulo       TEXT    NOT NULL CHECK(modulo IN ('acesso','encomenda','sistema','operador','morador')),
            payload_json TEXT    NOT NULL,
            ip_origem    TEXT,
            registrado_em TEXT   NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # Trigger: impede UPDATE na auditoria

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS bloqueia_update_auditoria
        BEFORE UPDATE ON auditoria
        BEGIN
            SELECT RAISE(ABORT, 'VIOLAÇÃO: registros de auditoria são imutáveis.');
        END
    """)

    # Trigger: impede DELETE na auditoria

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS bloqueia_delete_auditoria
        BEFORE DELETE ON auditoria
        BEGIN
            SELECT RAISE(ABORT, 'VIOLAÇÃO: registros de auditoria não podem ser excluídos.');
        END
    """)

    conn.commit()
    conn.close()