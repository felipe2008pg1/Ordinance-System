"""
CLI interface utilities: ANSI colors, tables, and standardized prompts.
"""

import os
import json
from datetime import datetime

# ── ANSI COLORS ───────────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    @staticmethod
    def ok(message):
        return f"{C.GREEN}✓ {message}{C.RESET}"

    @staticmethod
    def error(message):
        return f"{C.RED}✗ {message}{C.RESET}"

    @staticmethod
    def warning(message):
        return f"{C.YELLOW}⚠ {message}{C.RESET}"

    @staticmethod
    def info(message):
        return f"{C.CYAN}ℹ {message}{C.RESET}"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def header(title: str, subtitle: str = ""):
    width = 60

    print(f"\n{C.BLUE}{'═' * width}{C.RESET}")
    print(
        f"{C.BOLD}{C.WHITE}  🏢 GATEHOUSE — "
        f"{title.upper()}{C.RESET}"
    )

    if subtitle:
        print(f"{C.GRAY}  {subtitle}{C.RESET}")

    print(f"{C.BLUE}{'═' * width}{C.RESET}\n")

def separator(label: str = ""):
    if label:
        print(
            f"\n{C.DIM}── {label} "
            f"{'─' * (50 - len(label))}{C.RESET}"
        )

    else:
        print(f"{C.DIM}{'─' * 55}{C.RESET}")

def pause():
    input(
        f"\n{C.GRAY}  Press ENTER to continue...{C.RESET}"
    )

def confirm(question: str) -> bool:
    response = input(
        f"\n{C.YELLOW}  {question} [y/N]: {C.RESET}"
    ).strip().lower()

    return response == "y"

def prompt(
    label: str,
    required: bool = True,
    hidden: bool = False,
) -> str:
    import getpass

    while True:
        if hidden:
            value = getpass.getpass(f"  {label}: ")

        else:
            value = input(f"  {label}: ").strip()

        if value or not required:
            return value

        print(C.error("  Required field."))

def menu(title: str, options: list[str]) -> int:
    print(f"\n{C.BOLD}  {title}{C.RESET}")
    separator()

    for index, option in enumerate(options, 1):
        print(
            f"  {C.CYAN}[{index}]{C.RESET} {option}"
        )

    print(
        f"  {C.GRAY}[0]{C.RESET} Back / Exit"
    )

    separator()

    while True:
        try:
            choice = int(
                input("  Option: ").strip()
            )

            if choice == 0:
                return -1

            elif 1 <= choice <= len(options):
                return choice - 1

            print(
                C.warning(
                    f"  Choose between 0 and {len(options)}."
                )
            )

        except ValueError:
            print(
                C.error("  Enter a valid number.")
            )

def table(
    columns: list[str],
    rows: list[list],
    column_widths: list[int] | None = None,
):
    """Renders a simple table in the terminal."""

    if not column_widths:
        column_widths = [
            max(
                len(str(column)),
                max(
                    (
                        len(str(row[index]))
                        for row in rows
                    ),
                    default=0,
                ),
            )
            for index, column in enumerate(columns)
        ]

        column_widths = [
            min(width, 30)
            for width in column_widths
        ]

    separator_line = (
        "  +"
        + "+".join(
            "-" * (width + 2)
            for width in column_widths
        )
        + "+"
    )

    header_row = (
        "  |"
        + "|".join(
            f" {C.BOLD}{str(column).upper()[:width].ljust(width)}{C.RESET} "
            for column, width in zip(
                columns,
                column_widths,
            )
        )
        + "|"
    )

    print(separator_line)
    print(header_row)
    print(separator_line)

    for row in rows:
        formatted_row = (
            "  |"
            + "|".join(
                f" {str(value)[:width].ljust(width)} "
                for value, width in zip(
                    row,
                    column_widths,
                )
            )
            + "|"
        )

        print(formatted_row)

    print(separator_line)

def display_formatted_json(
    data: dict | str,
    title: str = "",
):
    """Displays a JSON payload in a readable format in the terminal."""

    if title:
        print(
            f"\n  {C.BOLD}{title}{C.RESET}"
        )

    if isinstance(data, str):
        try:
            data = json.loads(data)

        except Exception:
            print(f"  {data}")
            return

    formatted = json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
        default=str,
    )

    for line in formatted.split("\n"):
        print(
            f"  {C.GRAY}{line}{C.RESET}"
        )

def status_badge(status: str) -> str:
    status_map = {
        "authorized":
            f"{C.GREEN}● authorized{C.RESET}",

        "denied":
            f"{C.RED}✗ denied{C.RESET}",

        "pending":
            f"{C.YELLOW}◌ pending{C.RESET}",

        "checked_out":
            f"{C.GRAY}↩ checked out{C.RESET}",

        "received":
            f"{C.CYAN}📦 received{C.RESET}",

        "notified":
            f"{C.YELLOW}🔔 notified{C.RESET}",

        "picked_up":
            f"{C.GREEN}✓ picked up{C.RESET}",
    }

    return status_map.get(status, status)
