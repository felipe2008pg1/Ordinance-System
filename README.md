<h1 align="center">🏢 Gatehouse Management System — Terminal CLI</h1>

<p align="center">
  <span style="display:inline-block; background:#0D1117; padding:12px; border-radius:16px; border:2px solid #00D4FF;">
    <img src="https://capsule-render.vercel.app/api?type=rect&color=0D1117&height=180&section=header&text=Gatehouse%20Management%20System&fontSize=32&fontColor=00D4FF&animation=fadeIn&fontAlignY=55" alt="Gatehouse Management System">
  </span>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&labelColor=0D1117&logo=python&logoColor=3776AB" alt="Python">
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&labelColor=0D1117&logo=sqlite&logoColor=003B57" alt="SQLite">
  <img src="https://img.shields.io/badge/Architecture-Layered-7B61FF?style=for-the-badge&labelColor=0D1117" alt="Layered Architecture">
  <img src="https://img.shields.io/badge/Security-SHA--256-E34F26?style=for-the-badge&labelColor=0D1117" alt="SHA-256">
  <img src="https://img.shields.io/badge/Audit-Append--Only-00C853?style=for-the-badge&labelColor=0D1117" alt="Append Only Audit">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" alt="Rainbow divider">
</p>

> **📌 NOTICE:**
> A security-oriented terminal management system designed around **strict business rules, database-level immutability, and complete operational traceability**. Business constraints are enforced by the backend and SQLite triggers, ensuring that critical rules remain **sovereign and non-bypassable**, regardless of the user interface.

---

## 📋 About the Project

**Gatehouse Management System** is a Python-based **Terminal CLI** designed for gatehouse operations in **condominiums, residential complexes, and companies**.

The system is built around three core principles:

* **Business rules must be enforced by the backend.**
* **Critical records must be immutable.**
* **Every relevant operation must be traceable.**

Instead of relying exclusively on the CLI to prevent invalid operations, the system pushes critical guarantees down into the **database layer**.

This architecture prevents operators from bypassing restrictions through the interface and uses **SQL Triggers** to enforce audit immutability directly at the DBMS level.

---

## 🏗️ Architecture

The application follows a **layered architecture**:

```text
┌─────────────────────────────┐
│          CLI / UI            │
│       main.py + cli.py       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│          Modules             │
│                             │
│  auth │ access │ packages   │
│             │ audit          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│         SQLite DB            │
│                             │
│  Relations │ Constraints     │
│  Triggers  │ Audit Trail     │
└─────────────────────────────┘
```

The fundamental principle is simple:

**The UI requests operations. The backend validates them. The database enforces critical invariants.**

---

## 📁 Project Structure

```text
system/
├── main.py                  # Entry point — CLI interface
├── db/
│   └── database.py          # SQLite schema + connection + immutability triggers
├── modules/
│   ├── auth.py              # Authentication, operators and residents
│   ├── acess.py             # Pillar 1: Intelligent Access Control
│   ├── packages.py          # Pillar 2: Package Management Module
│   └── audit.py             # Pillar 3: Audit Trail (append-only)
└── utils/
    └── cli.py               # Terminal helpers: colors, menus, tables
```

---

## 🛡️ The 3 Pillars

### 1. 🚪 Intelligent Access Control

The access control system evaluates registered rules **before any database write**.

Key characteristics:

* **Visitor type** determines applicable access rules.
* **Time ranges** restrict when access is permitted.
* **Days of the week** can be configured as part of the access policy.
* Rules are validated **before persistence**.
* Operators **cannot manually override a denial**.
* The configured rule remains **sovereign over operator decisions**.

Access lifecycle:

```text
WAITING
   │
   ├── Authorized ──► EXITED
   │
   └── Denied
```

Possible statuses:

| Status       | Meaning                                     |
| ------------ | ------------------------------------------- |
| `WAITING`    | Access request is awaiting validation       |
| `AUTHORIZED` | Access was approved according to the rules  |
| `EXITED`     | Authorized visitor has left                 |
| `DENIED`     | Access was rejected by the configured rules |

---

### 2. 📦 Package Management Module

The package system provides a complete operational lifecycle:

```text
RECEIVED
    │
    ▼
NOTIFIED
    │
    ▼
PICKED UP
```

Core guarantees:

* Package registration automatically triggers **resident notification**.
* Pickup requires the resident's **confirmation PIN**.
* The PIN requirement is **mandatory and non-bypassable**.
* Invalid PIN attempts generate an audit event.
* Failed authentication attempts are recorded as:

```text
WITHDRAWAL_INVALID_PASSWORD
```

The system therefore does not merely track whether a package exists. It records the operational chain surrounding its delivery and pickup.

---

### 3. 🧾 Audit Trail

The audit system is designed as an **append-only event log**.

Audit records cannot be modified or deleted after creation.

This guarantee is enforced at the **database level** through SQLite triggers:

```text
INSERT  ────────────────► ✅ ALLOWED

UPDATE  ────────────────► ❌ BLOCKED

DELETE  ────────────────► ❌ BLOCKED
```

Each audit event stores:

| Field          | Purpose                           |
| -------------- | --------------------------------- |
| `action`       | Operation that occurred           |
| `module`       | System module responsible         |
| `operator`     | User who performed the operation  |
| `timestamp`    | Exact time of the event           |
| `JSON payload` | Structured contextual information |

This creates a persistent forensic trail for operational activity.

---

## 🔐 Security & Engineering Principles

The project applies several backend and database security concepts.

### Backend Validation

Business rules are validated independently of the CLI.

The interface is therefore **not trusted as the security boundary**.

```text
CLI Input
    │
    ▼
Backend Validation
    │
    ├── Invalid ──► Operation rejected
    │
    ▼
Database
    │
    ├── Constraints
    └── Triggers
```

### Database-Level Immutability

Audit integrity is protected through **SQL Triggers**, preventing unauthorized modification or deletion of historical events.

### Password Hashing

Passwords are stored using **SHA-256 hashing**, without requiring external dependencies.

> For a production authentication system, a password-specific adaptive hash such as **Argon2id, bcrypt, or scrypt** would be preferable to SHA-256. SHA-256 is included here as an applied cryptographic concept, not as the ideal choice for modern password storage.

### Structured JSON

Audit events contain structured JSON payloads to provide richer contextual information for later analysis and forensic inspection.

### Referential Integrity

Foreign keys connect core entities such as:

```text
Operators
    │
    ├────────► Visits
    │
    └────────► Audit Events

Residents
    │
    ├────────► Visits
    │
    └────────► Packages
```

---

## 👥 Roles and Permissions

| Permission                 | Doorman | Admin |
| -------------------------- | :-----: | :---: |
| Register entries / exits   |    ✅    |   ✅   |
| Receive / process packages |    ✅    |   ✅   |
| View audit trail           |    ✅    |   ✅   |
| Manage access rules        |    ❌    |   ✅   |
| Manage operators           |    ❌    |   ✅   |
| Manage residents           |    ❌    |   ✅   |

The authorization model separates **operational responsibilities** from **administrative configuration**.

A doorman can execute day-to-day gatehouse operations, while administrative configuration remains restricted to administrators.

---

## 🔑 Demo Credentials

| Role        | Login   | Password      |
| ----------- | ------- | ------------- |
| **Admin**   | `admin` | `admin123`    |
| **Doorman** | `joao`  | `porteiro123` |

> ⚠️ **Demo environment only:** these credentials are intentionally simple for demonstration purposes and must not be used in production.

---

## 🏠 Sample Residents

| Unit  | Resident     | PIN    |
| ----- | ------------ | ------ |
| `101` | Maria Silva  | `1234` |
| `202` | Carlos Souza | `5678` |
| `303` | Ana Lima     | `9999` |

> ⚠️ These credentials are sample data intended for testing the CLI workflow.

---

## 🚀 How to Run

Clone the repository and enter the project directory.

Then execute:

```bash
python main.py
```

The application starts through the terminal-based CLI.

---

## 🧠 Concepts Applied

| Concept                  | Application                                                    |
| ------------------------ | -------------------------------------------------------------- |
| **SQL Relationships**    | Foreign keys between visits, packages, operators and residents |
| **Database Triggers**    | Audit immutability enforced at DBMS level                      |
| **Password Hashing**     | SHA-256 without external dependencies                          |
| **Backend Validation**   | Business rules cannot be bypassed through the UI               |
| **Structured JSON**      | Rich audit payloads for traceability                           |
| **Layered Architecture** | UI → Modules → Database                                        |
| **Audit Trail**          | Persistent operational event history                           |
| **State Management**     | Controlled lifecycle for visits and packages                   |

---

## 🎯 Design Philosophy

The project is intentionally designed around a principle that matters in real systems:

> **Critical business rules should not depend solely on user behavior.**

If an operation must never happen, the system should make it **technically impossible**, rather than simply displaying a warning and trusting the operator to behave.

This philosophy is reflected throughout the architecture:

```text
Business Rule
     │
     ▼
Backend Validation
     │
     ▼
Database Constraint / Trigger
     │
     ▼
Immutable System Invariant
```

The result is a system where **business logic, data integrity, and auditability reinforce each other**.

---

## 🔭 Future Improvements

Potential production-oriented extensions include:

* **Argon2id** password hashing.
* Environment-based configuration using `.env`.
* More granular **role-based access control**.
* Automated testing with `pytest`.
* Database migration management.
* More comprehensive audit event taxonomy.
* Exportable audit reports.
* Automated backup and recovery.
* Stronger credential policies.
* Unit and integration test coverage.
* CI/CD validation through GitHub Actions.

---

## 🔗 Connect

<p align="center">
  <a href="https://www.linkedin.com/in/felipe-de-la-vega-dev/">
    <img src="https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&labelColor=0D1117&logo=linkedin&logoColor=0A66C2" alt="LinkedIn">
  </a>
</p>

<p align="center">
  <i>"Good architecture does not merely make software easier to change. It makes incorrect states harder to create."</i>
</p>
