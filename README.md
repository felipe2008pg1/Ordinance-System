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
- Immutability enforced by **SQL triggers at the database level**
- Each event stores: action, module, operator, timestamp, and a **JSON payload**

### How to Run

    python main.py

### Demo Credentials

| Role    | Login   | Password      |
|---------|---------|---------------|
| Admin   | `admin` | `admin123`    |
| Doorman | `joao`  | `porteiro123` |

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
