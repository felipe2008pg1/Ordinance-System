# 🏢 Sistema de Controle, Logística e Auditoria para Portarias

> 🇧🇷 Português | 🇺🇸 [English below](#-gatehouse-control-logistics-and-audit-system)

---

## 🇧🇷 Português

### Sobre o Projeto

Sistema CLI em Python com SQLite, focado em **rigidez de regras**, **imutabilidade de dados** e **rastreabilidade total** de todas as ações realizadas na portaria de condomínios ou empresas.

### Estrutura do Projeto

portaria/
├── main.py                  # Ponto de entrada — interface CLI
├── db/
│   └── database.py          # Schema SQLite + conexão + triggers de imutabilidade
├── modules/
│   ├── auth.py              # Autenticação, operadores e moradores
│   ├── acesso.py            # Pilar 1: Controle de Acesso Inteligente
│   ├── encomendas.py        # Pilar 2: Módulo de Encomendas
│   └── auditoria.py         # Pilar 3: Trilha de Auditoria (append-only)
└── utils/
└── cli.py               # Helpers de terminal: cores, menus, tabelas

### Os 3 Pilares

#### 1 — Controle de Acesso Inteligente
- Regras cadastradas definem **tipo de visitante**, **horário** e **dias da semana**
- O sistema valida as regras **antes** de qualquer persistência no banco
- O operador **não pode sobrescrever** uma negação — a regra é soberana
- Status possíveis: `aguardando → autorizado → saida` ou `negado`

#### 2 — Módulo de Encomendas
- Fluxo completo: `recebida → notificado → retirada`
- Notificação automática disparada ao registrar o recebimento
- Retirada exige a **senha de confirmação do morador** — etapa obrigatória e inviolável
- Tentativas com senha errada geram evento `RETIRADA_SENHA_INVALIDA` na auditoria

#### 3 — Trilha de Auditoria
- Tabela `auditoria` com registros **append-only** — nunca sofre UPDATE ou DELETE
- Imutabilidade garantida por **triggers SQL diretamente no banco**:
```sql
-- Tentativa de UPDATE resulta em:
VIOLAÇÃO: registros de auditoria são imutáveis.

-- Tentativa de DELETE resulta em:
VIOLAÇÃO: registros de auditoria não podem ser excluídos.
```
- Cada evento armazena: ação, módulo, operador, data/hora e **payload em JSON**

### Como Executar

```bash
# Requer apenas Python 3.10+ — sem dependências externas
python main.py
```

### Credenciais de Demonstração

| Perfil   | Login   | Senha          |
|----------|---------|----------------|
| Admin    | `admin` | `admin123`     |
| Porteiro | `joao`  | `porteiro123`  |

### Moradores de Exemplo

| Unidade | Morador      | Senha Encomenda |
|---------|--------------|-----------------|
| 101     | Maria Silva  | `1234`          |
| 202     | Carlos Souza | `5678`          |
| 303     | Ana Lima     | `9999`          |

### Perfis e Permissões

| Ação                         | Porteiro | Admin |
|------------------------------|----------|-------|
| Registrar entradas/saídas    | ✓        | ✓     |
| Receber/processar encomendas | ✓        | ✓     |
| Ver trilha de auditoria      | ✓        | ✓     |
| Cadastrar regras de acesso   | ✗        | ✓     |
| Gerenciar operadores         | ✗        | ✓     |
| Gerenciar moradores          | ✗        | ✓     |

### Conceitos Aplicados

- **Relacionamentos SQL** — FK entre visitas, encomendas, operadores e moradores
- **Triggers de banco** — imutabilidade da auditoria garantida a nível de SGBD
- **Hashing de senhas** — SHA-256 sem dependências externas
- **Validação no back-end** — regras de negócio não contornáveis pela interface
- **JSON estruturado** — payloads ricos para rastreabilidade forense
- **Arquitetura em camadas** — UI → módulos → banco de dados

---

## 🇺🇸 English

### About the Project

A Python CLI system using SQLite, focused on **strict business rules**, **data immutability**, and **full traceability** of every action performed at the gatehouse of condominiums or companies.

### Project Structure

portaria/
├── main.py                  # Entry point — CLI interface
├── db/
│   └── database.py          # SQLite schema + connection + immutability triggers
├── modules/
│   ├── auth.py              # Authentication, operators and residents
│   ├── acesso.py            # Pillar 1: Intelligent Access Control
│   ├── encomendas.py        # Pillar 2: Package Management Module
│   └── auditoria.py         # Pillar 3: Audit Trail (append-only)
└── utils/
└── cli.py               # Terminal helpers: colors, menus, tables

### The 3 Pillars

#### 1 — Intelligent Access Control
- Registered rules define **visitor type**, **time range**, and **days of the week**
- The system validates rules **before** any database write
- Operators **cannot override** a denial — the rule is sovereign
- Possible statuses: `waiting → authorized → exited` or `denied`

#### 2 — Package Management Module
- Full flow: `received → notified → picked up`
- Automatic notification triggered upon registering a package
- Pickup requires the **resident's confirmation PIN** — mandatory and non-bypassable
- Failed PIN attempts generate a `RETIRADA_SENHA_INVALIDA` audit event

#### 3 — Audit Trail
- The `auditoria` table is **append-only** — no UPDATE or DELETE ever allowed
- Immutability enforced by **SQL triggers at the database level**:
```sql
-- Any UPDATE attempt results in:
VIOLATION: audit records are immutable.

-- Any DELETE attempt results in:
VIOLATION: audit records cannot be deleted.
```
- Each event stores: action, module, operator, timestamp, and a **JSON payload**

### How to Run

```bash
# Requires only Python 3.10+ — no external dependencies
python main.py
```

### Demo Credentials

| Role     | Login   | Password       |
|----------|---------|----------------|
| Admin    | `admin` | `admin123`     |
| Doorman  | `joao`  | `porteiro123`  |

### Sample Residents

| Unit | Resident     | Package PIN |
|------|--------------|-------------|
| 101  | Maria Silva  | `1234`      |
| 202  | Carlos Souza | `5678`      |
| 303  | Ana Lima     | `9999`      |

### Roles and Permissions

| Action                      | Doorman | Admin |
|-----------------------------|---------|-------|
| Register entries/exits      | ✓       | ✓     |
| Receive/process packages    | ✓       | ✓     |
| View audit trail            | ✓       | ✓     |
| Manage access rules         | ✗       | ✓     |
| Manage operators            | ✗       | ✓     |
| Manage residents            | ✗       | ✓     |

### Concepts Applied

- **SQL Relationships** — FK between visits, packages, operators and residents
- **Database Triggers** — audit immutability enforced at the DBMS level
- **Password Hashing** — SHA-256 with no external dependencies
- **Back-end Validation** — business rules that cannot be bypassed through the UI
- **Structured JSON** — rich payloads for forensic traceability
- **Layered Architecture** — UI → modules → database