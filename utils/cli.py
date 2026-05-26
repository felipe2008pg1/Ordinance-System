"""
Utilitários de interface CLI: cores ANSI, tabelas, prompts padronizados.
"""

import os
import json
from datetime import datetime


# ── CORES ANSI ────────────────────────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"

    @staticmethod
    def ok(msg):    return f"{C.GREEN}✓ {msg}{C.RESET}"
    @staticmethod
    def erro(msg):  return f"{C.RED}✗ {msg}{C.RESET}"
    @staticmethod
    def aviso(msg): return f"{C.YELLOW}⚠ {msg}{C.RESET}"
    @staticmethod
    def info(msg):  return f"{C.CYAN}ℹ {msg}{C.RESET}"


def limpar_tela():
    os.system("cls" if os.name == "nt" else "clear")


def cabecalho(titulo: str, subtitulo: str = ""):
    largura = 60
    print(f"\n{C.BLUE}{'═'*largura}{C.RESET}")
    print(f"{C.BOLD}{C.WHITE}  🏢 PORTARIA — {titulo.upper()}{C.RESET}")
    if subtitulo:
        print(f"{C.GRAY}  {subtitulo}{C.RESET}")
    print(f"{C.BLUE}{'═'*largura}{C.RESET}\n")


def separador(label: str = ""):
    if label:
        print(f"\n{C.DIM}── {label} {'─'*(50-len(label))}{C.RESET}")
    else:
        print(f"{C.DIM}{'─'*55}{C.RESET}")


def pausar():
    input(f"\n{C.GRAY}  Pressione ENTER para continuar...{C.RESET}")


def confirmar(pergunta: str) -> bool:
    resp = input(f"\n{C.YELLOW}  {pergunta} [s/N]: {C.RESET}").strip().lower()
    return resp == "s"


def pedir(label: str, obrigatorio: bool = True, oculto: bool = False) -> str:
    import getpass
    while True:
        if oculto:
            valor = getpass.getpass(f"  {label}: ")
        else:
            valor = input(f"  {label}: ").strip()
        if valor or not obrigatorio:
            return valor
        print(C.erro("  Campo obrigatório."))


def menu(titulo: str, opcoes: list[str]) -> int:
    print(f"\n{C.BOLD}  {titulo}{C.RESET}")
    separador()
    for i, op in enumerate(opcoes, 1):
        print(f"  {C.CYAN}[{i}]{C.RESET} {op}")
    print(f"  {C.GRAY}[0]{C.RESET} Voltar / Sair")
    separador()

    while True:
        try:
            escolha = int(input(f"  Opção: ").strip())
            if escolha == 0:
                return -1
            if 1 <= escolha <= len(opcoes):
                return escolha - 1
            print(C.aviso(f"  Escolha entre 0 e {len(opcoes)}."))
        except ValueError:
            print(C.erro("  Digite um número válido."))


def tabela(colunas: list[str], linhas: list[list], col_widths: list[int] | None = None):
    """Renderiza uma tabela simples no terminal."""
    if not col_widths:
        col_widths = [max(len(str(c)), max((len(str(l[i])) for l in linhas), default=0))
                      for i, c in enumerate(colunas)]
        col_widths = [min(w, 30) for w in col_widths]

    sep = "  +" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header = "  |" + "|".join(
        f" {C.BOLD}{str(c).upper()[:w].ljust(w)}{C.RESET} "
        for c, w in zip(colunas, col_widths)
    ) + "|"

    print(sep)
    print(header)
    print(sep)
    for linha in linhas:
        row = "  |" + "|".join(
            f" {str(v)[:w].ljust(w)} " for v, w in zip(linha, col_widths)
        ) + "|"
        print(row)
    print(sep)


def exibir_json_formatado(dados: dict | str, titulo: str = ""):
    """Exibe um payload JSON de forma legível no terminal."""
    if titulo:
        print(f"\n  {C.BOLD}{titulo}{C.RESET}")
    if isinstance(dados, str):
        try:
            dados = json.loads(dados)
        except Exception:
            print(f"  {dados}")
            return
    formatted = json.dumps(dados, indent=4, ensure_ascii=False, default=str)
    for line in formatted.split("\n"):
        print(f"  {C.GRAY}{line}{C.RESET}")


def status_badge(status: str) -> str:
    mapa = {
        "autorizado": f"{C.GREEN}● autorizado{C.RESET}",
        "negado":     f"{C.RED}✗ negado{C.RESET}",
        "aguardando": f"{C.YELLOW}◌ aguardando{C.RESET}",
        "saida":      f"{C.GRAY}↩ saída{C.RESET}",
        "recebida":   f"{C.CYAN}📦 recebida{C.RESET}",
        "notificado": f"{C.YELLOW}🔔 notificado{C.RESET}",
        "retirada":   f"{C.GREEN}✓ retirada{C.RESET}",
    }
    return mapa.get(status, status)