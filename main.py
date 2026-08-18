"""
Main CLI interface for the Gatehouse Control, Logistics, and Audit System.
Entry point: python main.py
"""

import sys
import os

# Ensures that the project root directory is included in the path
sys.path.insert(0, os.path.dirname(__file__))

from db.database import init_db
from modules import auth, access, packages, audit_log
from utils.cli import (
    C,
    clear_screen,
    header,
    separator,
    pause,
    confirm,
    prompt,
    menu,
    table,
    display_formatted_json,
    status_badge,
)

# Authenticated operator in the current session
session: dict | None = None

# ═══════════════════════════════════════════════════════════════════
# LOGIN / LOGOUT
# ═══════════════════════════════════════════════════════════════════

def login_screen():
    global session

    clear_screen()
    header(
        "Gatehouse System",
        "Control · Logistics · Audit",
    )

    print(C.info("  Log in to continue.\n"))
    username = prompt("Username")
    password = prompt("Password", hidden=True)
    operator = auth.authenticate(username, password)

    if operator:
        session = operator
        operator_name = operator["name"]
        operator_role = operator["role"]

        print(
            f"\n  {C.ok(f"Welcome, {operator_name}! Role: {operator_role}")}"
        )

        pause()

    else:
        print(
            f"\n  {C.error("Invalid credentials. Please try again.")}"
        )

        pause()

# ═══════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════

def main_menu():
    doorman_options = [
        "🚪  Access Control",
        "📦  Package Management",
        "📋  Audit Trail",
        "🚪  Exit System",
    ]

    admin_options = [
        "🚪  Access Control",
        "📦  Package Management",
        "📋  Audit Trail",
        "👥  Manage Operators",
        "🏠  Manage Residents",
        "🚪  Exit System",
    ]

    is_admin = session["role"] == "admin"
    options = admin_options if is_admin else doorman_options

    while True:
        clear_screen()

        header(
            "Main Menu",
            f"Operator: {session['name']} "
            f"({session['role']})  |  {_current_time()}",
        )

        choice = menu("Select a module", options)

        if choice == -1 or options[
            choice if choice >= 0 else 0
        ].endswith("System"):

            if confirm("Do you really want to exit?"):
                audit_log.record(
                    action="LOGOUT",
                    module="system",
                    payload={
                        "username": session["username"],
                    },
                    operator_id=session["id"],
                )

                print(
                    f"\n  {C.info('Session ended. Goodbye!')}\n"
                )

                sys.exit(0)

            continue

        label = options[choice]

        if "Access" in label:
            access_menu()

        elif "Package" in label:
            packages_menu()

        elif "Audit" in label:
            audit_menu()

        elif "Operators" in label and is_admin:
            operators_menu()

        elif "Residents" in label and is_admin:
            residents_menu()

        elif "Exit" in label:
            if confirm("Do you really want to exit?"):
                print(
                    f"\n  {C.info('Session ended. Goodbye!')}\n"
                )

                sys.exit(0)

def _current_time():
    from datetime import datetime

    return datetime.now().strftime("%m/%d/%Y %H:%M")

# ═══════════════════════════════════════════════════════════════════
# ACCESS CONTROL MODULE
# ═══════════════════════════════════════════════════════════════════

def access_menu():
    while True:
        clear_screen()

        header(
            "Access Control",
            "Registration and validation of entries/exits",
        )

        choice = menu(
            "Access",
            [
                "Register new entry",
                "Register checkout",
                "View active entries",
                "Visit history",
                "─── Access Rules ───",
                "Create new rule",
                "List rules",
            ],
        )

        if choice == -1:
            break

        elif choice == 0:
            _register_entry()

        elif choice == 1:
            _register_checkout()

        elif choice == 2:
            _list_active_entries()

        elif choice == 3:
            _visit_history()

        elif choice == 5:
            if session["role"] != "admin":
                print(
                    C.error(
                        "  Only administrators can create access rules."
                    )
                )

                pause()

            else:
                _create_rule()

        elif choice == 6:
            _list_rules()

def _register_entry():
    clear_screen()
    header("New Entry")

    visitor_type = _choose_visit_type()

    if not visitor_type:
        return

    visitor_name = prompt("Visitor/service provider name")
    document = prompt(
        "Document (CPF/ID)",
        required=False,
    )
    unit = prompt("Destination unit (e.g. 101, 202)")

    print()

    allowed, preview_message = access.check_rules(
        visitor_type
    )

    if not allowed:
        print(
            f"  {C.warning('WARNING: The rules indicate that this access will be DENIED.')}"
        )

        print(
            f"  {C.GRAY}{preview_message}{C.RESET}"
        )

        if not confirm(
            "Do you want to register it anyway "
            "(the denial will be audited)?"
        ):
            return

    result = access.register_visit(
        visitor_name=visitor_name,
        type=visitor_type,
        destination_unit=unit,
        operator_id=session["id"],
        document=document,
    )

    if result["ok"]:
        print(
            f"\n  {C.ok(result['message'])}"
        )

        print(
            f"  Entry reference: #{result['visit_id']}"
        )

    else:
        print(
            f"\n  {C.error(result['message'])}"
        )

        print(
            f"  Denial record: #{result['visit_id']}"
        )

    pause()

def _choose_visit_type() -> str | None:
    visitor_types = [
        "visitor",
        "service_provider",
        "delivery",
    ]

    choice = menu(
        "Visitor Type",
        [
            visitor_type.replace("_", " ").title()
            for visitor_type in visitor_types
        ],
    )

    if choice == -1:
        return None

    return visitor_types[choice]

def _register_checkout():
    clear_screen()
    header("Register Checkout")

    active_visits = access.list_active_visits()

    if not active_visits:
        print(
            C.info("  No active visits at the moment.")
        )

        pause()
        return

    _display_visit_table(
        active_visits,
        show_checkout=False,
    )

    try:
        visit_id = int(
            prompt("Visit ID to register checkout")
        )

    except ValueError:
        print(
            C.error("Invalid ID.")
        )

        pause()
        return

    result = access.register_checkout(
        visit_id,
        session["id"],
    )

    if result["ok"]:
        print(
            f"\n  {C.ok(result['message'])}"
        )

    else:
        print(
            f"\n  {C.error(result['message'])}"
        )

    pause()

def _list_active_entries():
    clear_screen()
    header("Active Entries")
    active_visits = access.list_active_visits()

    if not active_visits:
        print(
            C.info("  No active visits at the moment.")
        )

    else:
        _display_visit_table(active_visits)

    pause()

def _visit_history():
    clear_screen()

    header(
        "Visit History",
        "Last 20 entries",
    )

    visits = access.list_recent_visits(20)

    if not visits:
        print(
            C.info("  No visits registered.")
        )

    else:
        _display_visit_table(visits)

    pause()

def _display_visit_table(
    visits: list,
    show_checkout: bool = True,
):
    columns = [
        "ID",
        "Visitor",
        "Type",
        "Unit",
        "Status",
        "Entry",
    ]

    rows = []

    for visit in visits:
        rows.append(
            [
                visit["id"],
                visit["visitor_name"][:20],
                visit["type"],
                visit["destination_unit"],
                status_badge(visit["status"]),
                (visit["checked_in_at"] or "-")[:16],
            ]
        )

    table(
        columns,
        rows,
        [4, 22, 17, 8, 18, 16],
    )

def _create_rule():
    clear_screen()
    header("Create Access Rule")

    print(
        C.info(
            "  Days: mon, tue, wed, thu, fri, sat, sun "
            "(comma-separated)\n"
        )
    )

    description = prompt("Rule description")
    visitor_type = _choose_visit_type() or "all"
    start_time = prompt("Start time (HH:MM)")
    end_time = prompt("End time   (HH:MM)")
    weekdays = prompt(
        "Allowed days (e.g. mon,tue,wed,thu,fri)"
    )

    rule_id = access.create_rule(
        description,
        visitor_type,
        start_time,
        end_time,
        weekdays,
        session["id"],
    )

    print(
        f"\n  {C.ok(f'Rule #{rule_id} created successfully.')}"
    )

    pause()

def _list_rules():
    clear_screen()
    header("Registered Access Rules")

    rules = access.list_rules()

    if not rules:
        print(
            C.info("  No rules registered.")
        )

    else:
        columns = [
            "ID",
            "Description",
            "Type",
            "Start",
            "End",
            "Days",
            "Active",
        ]

        rows = [
            [
                rule["id"],
                rule["description"][:25],
                rule["visitor_type"],
                rule["start_time"],
                rule["end_time"],
                rule["weekdays"],
                "✓" if rule["active"] else "✗",
            ]
            for rule in rules
        ]

        table(
            columns,
            rows,
            [4, 27, 17, 7, 7, 20, 6],
        )

        if session["role"] == "admin":
            separator()

            if confirm("Do you want to deactivate a rule?"):
                try:
                    rule_id = int(
                        prompt("Rule ID")
                    )

                    access.deactivate_rule(
                        rule_id,
                        session["id"],
                    )

                    print(
                        C.ok("Rule deactivated.")
                    )

                except ValueError:
                    print(
                        C.error("Invalid ID.")
                    )

    pause()

# ═══════════════════════════════════════════════════════════════════
# PACKAGE MANAGEMENT MODULE
# ═══════════════════════════════════════════════════════════════════

def packages_menu():
    while True:
        clear_screen()

        header(
            "Package Management",
            "Receiving · Notification · Pickup",
        )

        choice = menu(
            "Packages",
            [
                "Register package receipt",
                "Process pickup (with password)",
                "Pending packages",
                "Package history",
            ],
        )

        if choice == -1:
            break

        elif choice == 0:
            _receive_package()

        elif choice == 1:
            _pick_up_package()

        elif choice == 2:
            _pending_packages()

        elif choice == 3:
            _package_history()

def _receive_package():
    clear_screen()
    header("Register Package Receipt")

    unit = prompt(
        "Destination unit (e.g. 101)"
    )

    description = prompt(
        "Package description"
    )

    tracking_code = prompt(
        "Tracking code",
        required=False,
    )

    sender = prompt(
        "Sender",
        required=False,
    )

    result = packages.receive_package(
        description=description,
        destination_unit=unit,
        operator_id=session["id"],
        tracking_code=tracking_code,
        sender=sender,
    )

    if result["ok"]:
        print(
            f"  {C.ok(result['message'])}"
        )

    else:
        print(
            f"  {C.error(result['message'])}"
        )

    pause()

def _pick_up_package():
    clear_screen()
    header("Process Package Pickup")

    pending_packages = packages.list_pending_packages()

    if not pending_packages:
        print(
            C.info("  No pending packages.")
        )

        pause()
        return

    _display_package_table(pending_packages)
    separator()

    print(
        C.warning(
            "  The resident's confirmation password is required "
            "to release the package.\n"
        )
    )

    try:
        package_id = int(
            prompt("Package ID")
        )

    except ValueError:
        print(
            C.error("Invalid ID.")
        )

        pause()
        return

    picked_up_by = prompt(
        "Name of person picking up"
    )

    confirmation_password = prompt(
        "Resident confirmation password",
        hidden=True,
    )

    result = packages.pick_up_package(
        package_id=package_id,
        confirmation_password=confirmation_password,
        picked_up_by=picked_up_by,
        operator_id=session["id"],
    )

    if result["ok"]:
        print(
            f"\n  {C.ok(result['message'])}"
        )

    else:
        print(
            f"\n  {C.error(result['message'])}"
        )

    pause()


def _pending_packages():
    clear_screen()
    header("Pending Packages")

    pending_packages = packages.list_pending_packages()

    if not pending_packages:
        print(
            C.info(
                "  No pending packages at the moment."
            )
        )

    else:
        _display_package_table(
            pending_packages
        )

    pause()

def _package_history():
    clear_screen()

    header(
        "Package History",
        "Last 20",
    )

    history = packages.list_recent_packages(20)

    if not history:
        print(
            C.info("  No packages registered.")
        )

    else:
        _display_package_table(history)

    pause()

def _display_package_table(
    package_list: list,
):
    columns = [
        "ID",
        "Unit",
        "Description",
        "Status",
        "Received",
        "Tracking",
    ]

    rows = [
        [
            package["id"],
            package["destination_unit"],
            package["description"][:25],
            status_badge(package["status"]),
            package["received_at"][:16],
            (package["tracking_code"] or "-")[:15],
        ]
        for package in package_list
    ]

    table(
        columns,
        rows,
        [4, 8, 27, 18, 16, 17],
    )

# ═══════════════════════════════════════════════════════════════════
# AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════

def audit_menu():
    while True:
        clear_screen()

        total = audit_log.get_total_events()

        header(
            "Audit Trail",
            f"Total registered events: {total}",
        )

        choice = menu(
            "Audit",
            [
                "View recent events (all)",
                "Filter by module",
                "Inspect event JSON payload",
            ],
        )

        if choice == -1:
            break

        elif choice == 0:
            _recent_audit_events()

        elif choice == 1:
            _audit_by_module()

        elif choice == 2:
            _inspect_event()

def _recent_audit_events(
    module=None,
    limit=30,
):
    clear_screen()

    header(
        "Audit Trail",
        f"Module: {module or 'all'} · "
        f"Last {limit} events",
    )

    events = audit_log.search_audit_trail(
        module=module,
        limit=limit,
    )

    if not events:
        print(
            C.info("  No events found.")
        )

        pause()
        return

    columns = [
        "ID",
        "Action",
        "Module",
        "Operator",
        "Date/Time",
    ]

    rows = [
        [
            event["id"],
            event["action"][:25],
            event["module"],
            (event["operator_username"] or "system")[:15],
            event["recorded_at"][:16],
        ]
        for event in events
    ]

    table(
        columns,
        rows,
        [5, 27, 10, 17, 16],
    )

    pause()

def _audit_by_module():
    modules = [
        "access",
        "package",
        "system",
        "operator",
        "resident",
    ]

    choice = menu(
        "Filter by module",
        [
            module.capitalize()
            for module in modules
        ],
    )

    if choice == -1:
        return

    _recent_audit_events(
        module=modules[choice]
    )

def _inspect_event():
    clear_screen()
    header("Inspect Audit Event")

    try:
        event_id = int(
            prompt("Event ID")
        )

    except ValueError:
        print(
            C.error("Invalid ID.")
        )

        pause()
        return

    from db.database import get_connection

    conn = get_connection()

    event = conn.execute(
        """
        SELECT a.*,
               o.name AS operator_name,
               o.username AS operator_username
        FROM audit_log a
        LEFT JOIN operators o
            ON o.id = a.operator_id
        WHERE a.id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    if not event:
        print(
            C.error("Event not found.")
        )

        pause()
        return

    separator("Metadata")

    print(
        f"  ID:          {event['id']}"
    )

    print(
        f"  Action:      "
        f"{C.BOLD}{event['action']}{C.RESET}"
    )

    print(
        f"  Module:      {event['module']}"
    )

    print(
        f"  Operator:    "
        f"{event['operator_name'] or 'System'} "
        f"({event['operator_username'] or '-'})"
    )

    print(
        f"  Recorded:    {event['recorded_at']}"
    )

    print(
        f"  IP:          {event['source_ip'] or '-'}"
    )

    display_formatted_json(
        event["payload_json"],
        title="JSON Payload:",
    )

    pause()

# ═══════════════════════════════════════════════════════════════════
# OPERATOR MANAGEMENT (ADMIN ONLY)
# ═══════════════════════════════════════════════════════════════════

def operators_menu():
    while True:
        clear_screen()

        header(
            "Manage Operators",
            "Administrators only",
        )

        choice = menu(
            "Operators",
            [
                "List operators",
                "Create new operator",
                "Deactivate operator",
            ],
        )

        if choice == -1:
            break

        elif choice == 0:
            _list_operators()

        elif choice == 1:
            _create_operator()

        elif choice == 2:
            _deactivate_operator()

def _list_operators():
    clear_screen()
    header("Registered Operators")

    operators = auth.list_operators()

    columns = [
        "ID",
        "Name",
        "Username",
        "Role",
        "Active",
    ]

    rows = [
        [
            operator["id"],
            operator["name"][:25],
            operator["username"],
            operator["role"],
            "✓" if operator["active"] else "✗",
        ]
        for operator in operators
    ]

    table(
        columns,
        rows,
        [4, 27, 15, 10, 6],
    )

    pause()

def _create_operator():
    clear_screen()
    header("Create New Operator")

    name = prompt("Full name")
    username = prompt("Username (unique)")
    password = prompt(
        "Password",
        hidden=True,
    )

    roles = [
        "doorman",
        "admin",
    ]

    index = menu(
        "Role",
        [
            "Doorman",
            "Admin",
        ],
    )

    if index == -1:
        return

    role = roles[index]

    result = auth.create_operator(
        name,
        username,
        password,
        role,
        session["id"],
    )

    if result["ok"]:
        print(
            f"\n  {C.ok(result['message'])}"
        )

    else:
        print(
            f"\n  {C.error(result['message'])}"
        )

    pause()

def _deactivate_operator():
    _list_operators()

    try:
        operator_id = int(
            prompt(
                "Operator ID to deactivate"
            )
        )

    except ValueError:
        print(
            C.error("Invalid ID.")
        )

        pause()
        return

    if confirm(
        f"Confirm deactivation of operator #{operator_id}?"
    ):
        result = auth.deactivate_operator(
            operator_id,
            session["id"],
        )

        if result["ok"]:
            print(
                C.ok(result["message"])
            )

        else:
            print(
                C.error(result["message"])
            )

    pause()

# ═══════════════════════════════════════════════════════════════════
# RESIDENT MANAGEMENT (ADMIN ONLY)
# ═══════════════════════════════════════════════════════════════════

def residents_menu():
    while True:
        clear_screen()
        header("Manage Residents")

        choice = menu(
            "Residents",
            [
                "List residents",
                "Create resident",
                "Deactivate resident",
            ],
        )

        if choice == -1:
            break

        elif choice == 0:
            _list_residents()

        elif choice == 1:
            _create_resident()

        elif choice == 2:
            _deactivate_resident()

def _list_residents():
    clear_screen()
    header("Registered Residents")

    residents = auth.list_residents()

    columns = [
        "ID",
        "Name",
        "Unit",
        "Phone",
        "Active",
    ]

    rows = [
        [
            resident["id"],
            resident["name"][:25],
            resident["unit"],
            resident["phone"] or "-",
            "✓" if resident["active"] else "✗",
        ]
        for resident in residents
    ]

    table(
        columns,
        rows,
        [4, 27, 8, 15, 6],
    )

    pause()

def _create_resident():
    clear_screen()
    header("Create Resident")

    name = prompt("Resident name")
    unit = prompt(
        "Unit (e.g. 101, B204)"
    )

    phone = prompt(
        "Phone",
        required=False,
    )

    print(
        C.info(
            "\n  The package password will be required "
            "when picking up packages."
        )
    )

    password = prompt(
        "Package confirmation password",
        hidden=True,
    )

    result = auth.create_resident(
        name,
        unit,
        password,
        session["id"],
        phone,
    )

    if result["ok"]:
        print(
            f"\n  {C.ok(result['message'])}"
        )

    else:
        print(
            f"\n  {C.error(result['message'])}"
        )

    pause()

def _deactivate_resident():
    _list_residents()

    try:
        resident_id = int(
            prompt(
                "Resident ID to deactivate"
            )
        )

    except ValueError:
        print(
            C.error("Invalid ID.")
        )

        pause()
        return

    if confirm(
        f"Confirm deactivation of resident #{resident_id}?"
    ):
        result = auth.deactivate_resident(
            resident_id,
            session["id"],
        )

        if result["ok"]:
            print(
                C.ok(result["message"])
            )

        else:
            print(
                C.error(result["message"])
            )

    pause()

# ═══════════════════════════════════════════════════════════════════
# SEED — INITIAL DEMONSTRATION DATA
# ═══════════════════════════════════════════════════════════════════

def _seed_initial_data():
    """Populates the database with sample data if it does not exist yet."""

    from db.database import get_connection

    conn = get_connection()

    existing = conn.execute(
        "SELECT id FROM operators WHERE username = 'admin'"
    ).fetchone()

    conn.close()

    if existing:
        return

    import hashlib

    def hash_password(value):
        return hashlib.sha256(
            value.encode()
        ).hexdigest()

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO operators
            (name, username, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Administrator",
            "admin",
            hash_password("admin123"),
            "admin",
        ),
    )

    conn.execute(
        """
        INSERT INTO operators
            (name, username, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        (
            "John Doorman",
            "john",
            hash_password("doorman123"),
            "doorman",
        ),
    )

    conn.execute(
        """
        INSERT INTO residents
            (name, unit, phone, package_password)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Maria Silva",
            "101",
            "11999990001",
            "1234",
        ),
    )

    conn.execute(
        """
        INSERT INTO residents
            (name, unit, phone, package_password)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Carlos Souza",
            "202",
            "11999990002",
            "5678",
        ),
    )

    conn.execute(
        """
        INSERT INTO residents
            (name, unit, phone, package_password)
        VALUES (?, ?, ?, ?)
        """,
        (
            "Ana Lima",
            "303",
            "11999990003",
            "9999",
        ),
    )

    conn.execute(
        """
        INSERT INTO access_rules
            (
                description,
                visitor_type,
                start_time,
                end_time,
                weekdays
            )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Business hours visitors",
            "visitor",
            "08:00",
            "22:00",
            "mon,tue,wed,thu,fri,sat,sun",
        ),
    )

    conn.execute(
        """
        INSERT INTO access_rules
            (
                description,
                visitor_type,
                start_time,
                end_time,
                weekdays
            )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Weekday service providers",
            "service_provider",
            "08:00",
            "18:00",
            "mon,tue,wed,thu,fri",
        ),
    )

    conn.execute(
        """
        INSERT INTO access_rules
            (
                description,
                visitor_type,
                start_time,
                end_time,
                weekdays
            )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Extended delivery hours",
            "delivery",
            "07:00",
            "21:00",
            "mon,tue,wed,thu,fri,sat",
        ),
    )

    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    init_db()
    _seed_initial_data()

    clear_screen()

    header(
        "Gatehouse System",
        "v1.0  ·  Control · Logistics · Audit",
    )

    print(
        f"""
  {C.BOLD}Demo Credentials:{C.RESET}

  {C.CYAN}Admin{C.RESET}     →  username: {C.BOLD}admin{C.RESET}   password: {C.BOLD}admin123{C.RESET}
  {C.CYAN}Doorman{C.RESET}   →  username: {C.BOLD}john{C.RESET}    password: {C.BOLD}doorman123{C.RESET}

  {C.GRAY}Sample residents: units 101, 202, 303{C.RESET}
  {C.GRAY}Package passwords: 1234 / 5678 / 9999{C.RESET}
    """
    )

    pause()

    while True:
        if not session:
            login_screen()

        else:
            main_menu()

if __name__ == "__main__":
    main()
