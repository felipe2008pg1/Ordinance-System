"""
Interface CLI principal do Sistema de Controle, Logística e Auditoria para Portarias.
Ponto de entrada: python main.py
"""

import sys
import os

# Garante que o diretório raiz do projeto esteja no path
sys.path.insert(0, os.path.dirname(__file__))

from db.database import init_db
from modules import auth, acesso, encomendas, auditoria
from utils.cli import (
    C, limpar_tela, cabecalho, separador, pausar,
    confirmar, pedir, menu, tabela, exibir_json_formatado, status_badge
)

# Operador autenticado na sessão atual
sessao: dict | None = None

# ═══════════════════════════════════════════════════════════════════
# LOGIN / LOGOUT
# ═══════════════════════════════════════════════════════════════════

def tela_login():
    global sessao
    limpar_tela()
    cabecalho("Sistema de Portaria", "Controle · Logística · Auditoria")

    print(C.info("  Faça login para continuar.\n"))
    login = pedir("Login")
    senha = pedir("Senha", oculto=True)

    operador = auth.autenticar(login, senha)
    if operador:
        sessao = operador
        nome_op = operador["nome"]
        perfil_op = operador["perfil"]
        print(f"\n  {C.ok(f'Bem-vindo(a), {nome_op}! Perfil: {perfil_op}')}")
        pausar()
    else:
        print(f"\n  {C.erro('Credenciais inválidas. Tente novamente.')}")
        pausar()

# ═══════════════════════════════════════════════════════════════════
# MENU PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

def menu_principal():
    opcoes_porteiro = [
        "🚪  Controle de Acesso",
        "📦  Módulo de Encomendas",
        "📋  Trilha de Auditoria",
        "🚪  Sair do Sistema",
    ]
    opcoes_admin = [
        "🚪  Controle de Acesso",
        "📦  Módulo de Encomendas",
        "📋  Trilha de Auditoria",
        "👥  Gerenciar Operadores",
        "🏠  Gerenciar Moradores",
        "🚪  Sair do Sistema",
    ]

    is_admin = sessao["perfil"] == "admin"
    opcoes = opcoes_admin if is_admin else opcoes_porteiro

    while True:
        limpar_tela()
        cabecalho(
            "Menu Principal",
            f"Operador: {sessao['nome']} ({sessao['perfil']})  |  {_hora_agora()}"
        )

        escolha = menu("Selecione o módulo", opcoes)

        if escolha == -1 or opcoes[escolha if escolha >= 0 else 0].endswith("Sistema"):
            if confirmar("Deseja realmente sair?"):
                auditoria.registrar(
                    acao="LOGOUT",
                    modulo="sistema",
                    payload={"login": sessao["login"]},
                    operador_id=sessao["id"],
                )
                print(f"\n  {C.info('Sessão encerrada. Até logo!')}\n")
                sys.exit(0)
            continue

        label = opcoes[escolha]
        if "Acesso" in label:
            menu_acesso()
        elif "Encomenda" in label:
            menu_encomendas()
        elif "Auditoria" in label:
            menu_auditoria()
        elif "Operadores" in label and is_admin:
            menu_operadores()
        elif "Moradores" in label and is_admin:
            menu_moradores()
        elif "Sair" in label:
            if confirmar("Deseja realmente sair?"):
                print(f"\n  {C.info('Sessão encerrada. Até logo!')}\n")
                sys.exit(0)

def _hora_agora():
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y %H:%M")

# ═══════════════════════════════════════════════════════════════════
# MÓDULO DE ACESSO
# ═══════════════════════════════════════════════════════════════════

def menu_acesso():
    while True:
        limpar_tela()
        cabecalho("Controle de Acesso", "Registro e validação de entradas/saídas")

        escolha = menu("Acesso", [
            "Registrar nova entrada",
            "Registrar saída",
            "Ver entradas ativas",
            "Histórico de visitas",
            "─── Regras de Acesso ───",
            "Cadastrar nova regra",
            "Listar regras",
        ])

        if escolha == -1:
            break
        elif escolha == 0:
            _registrar_entrada()
        elif escolha == 1:
            _registrar_saida()
        elif escolha == 2:
            _listar_entradas_ativas()
        elif escolha == 3:
            _historico_visitas()
        elif escolha == 5:
            if sessao["perfil"] != "admin":
                print(C.erro("  Apenas administradores podem cadastrar regras."))
                pausar()
            else:
                _cadastrar_regra()
        elif escolha == 6:
            _listar_regras()

def _registrar_entrada():
    limpar_tela()
    cabecalho("Nova Entrada")

    tipo = _escolher_tipo_visita()
    if not tipo:
        return

    nome = pedir("Nome do visitante/prestador")
    documento = pedir("Documento (CPF/RG)", obrigatorio=False)
    unidade = pedir("Unidade destino (ex: 101, 202)")

    print()
    permitido, msg_previa = acesso.verificar_regras(tipo)
    if not permitido:
        print(f"  {C.aviso('ATENÇÃO: As regras indicam que este acesso será NEGADO.')}")
        print(f"  {C.GRAY}{msg_previa}{C.RESET}")
        if not confirmar("Deseja registrar mesmo assim (a negação será auditada)?"):
            return

    resultado = acesso.registrar_visita(
        nome_visitante=nome,
        tipo=tipo,
        unidade_destino=unidade,
        operador_id=sessao["id"],
        documento=documento,
    )

    if resultado["ok"]:
        print(f"\n  {C.ok(resultado['mensagem'])}")
        print(f"  Protocolo de entrada: #{resultado['visita_id']}")
    else:
        print(f"\n  {C.erro(resultado['mensagem'])}")
        print(f"  Registro de negação: #{resultado['visita_id']}")
    pausar()

def _escolher_tipo_visita() -> str | None:
    tipos = ["visitante", "prestador", "entregador"]
    escolha = menu("Tipo de visitante", [t.capitalize() for t in tipos])
    if escolha == -1:
        return None
    return tipos[escolha]

def _registrar_saida():
    limpar_tela()
    cabecalho("Registrar Saída")

    ativas = acesso.listar_visitas_ativas()
    if not ativas:
        print(C.info("  Nenhuma visita ativa no momento."))
        pausar()
        return

    _exibir_tabela_visitas(ativas, mostrar_saida=False)

    try:
        vid = int(pedir("ID da visita para registrar saída"))
    except ValueError:
        print(C.erro("ID inválido."))
        pausar()
        return

    resultado = acesso.registrar_saida(vid, sessao["id"])
    if resultado["ok"]:
        print(f"\n  {C.ok(resultado['mensagem'])}")
    else:
        print(f"\n  {C.erro(resultado['mensagem'])}")
    pausar()

def _listar_entradas_ativas():
    limpar_tela()
    cabecalho("Entradas Ativas")
    ativas = acesso.listar_visitas_ativas()
    if not ativas:
        print(C.info("  Nenhuma visita ativa no momento."))
    else:
        _exibir_tabela_visitas(ativas)
    pausar()

def _historico_visitas():
    limpar_tela()
    cabecalho("Histórico de Visitas", "Últimas 20 entradas")
    visitas = acesso.listar_visitas_recentes(20)
    if not visitas:
        print(C.info("  Nenhuma visita registrada."))
    else:
        _exibir_tabela_visitas(visitas)
    pausar()

def _exibir_tabela_visitas(visitas: list, mostrar_saida: bool = True):
    colunas = ["ID", "Visitante", "Tipo", "Unidade", "Status", "Entrada"]
    linhas = []
    for v in visitas:
        linhas.append([
            v["id"],
            v["nome_visitante"][:20],
            v["tipo"],
            v["unidade_destino"],
            status_badge(v["status"]),
            (v["entrada_em"] or "-")[:16],
        ])
    tabela(colunas, linhas, [4, 22, 10, 8, 18, 16])

def _cadastrar_regra():
    limpar_tela()
    cabecalho("Cadastrar Regra de Acesso")

    print(C.info("  Dias: seg, ter, qua, qui, sex, sab, dom (separados por vírgula)\n"))
    descricao   = pedir("Descrição da regra")
    tipo        = _escolher_tipo_visita() or "todos"
    hora_inicio = pedir("Hora início (HH:MM)")
    hora_fim    = pedir("Hora fim    (HH:MM)")
    dias        = pedir("Dias permitidos (ex: seg,ter,qua,qui,sex)")

    rid = acesso.criar_regra(descricao, tipo, hora_inicio, hora_fim, dias, sessao["id"])
    print(f"\n  {C.ok(f'Regra #{rid} cadastrada com sucesso.')}")
    pausar()

def _listar_regras():
    limpar_tela()
    cabecalho("Regras de Acesso Cadastradas")
    regras = acesso.listar_regras()
    if not regras:
        print(C.info("  Nenhuma regra cadastrada."))
    else:
        colunas = ["ID", "Descrição", "Tipo", "Início", "Fim", "Dias", "Ativo"]
        linhas = [[r["id"], r["descricao"][:25], r["tipo_visita"],
                   r["hora_inicio"], r["hora_fim"], r["dias_semana"], "✓" if r["ativo"] else "✗"]
                  for r in regras]
        tabela(colunas, linhas, [4, 27, 10, 7, 7, 20, 6])

        if sessao["perfil"] == "admin":
            separador()
            if confirmar("Deseja desativar alguma regra?"):
                try:
                    rid = int(pedir("ID da regra"))
                    acesso.desativar_regra(rid, sessao["id"])
                    print(C.ok("Regra desativada."))
                except ValueError:
                    print(C.erro("ID inválido."))
    pausar()

# ═══════════════════════════════════════════════════════════════════
# MÓDULO DE ENCOMENDAS
# ═══════════════════════════════════════════════════════════════════

def menu_encomendas():
    while True:
        limpar_tela()
        cabecalho("Módulo de Encomendas", "Recebimento · Notificação · Retirada")

        escolha = menu("Encomendas", [
            "Registrar recebimento",
            "Processar retirada (com senha)",
            "Encomendas pendentes",
            "Histórico de encomendas",
        ])

        if escolha == -1:
            break
        elif escolha == 0:
            _receber_encomenda()
        elif escolha == 1:
            _retirar_encomenda()
        elif escolha == 2:
            _encomendas_pendentes()
        elif escolha == 3:
            _historico_encomendas()

def _receber_encomenda():
    limpar_tela()
    cabecalho("Registrar Recebimento de Encomenda")

    unidade    = pedir("Unidade destino (ex: 101)")
    descricao  = pedir("Descrição da encomenda")
    rastreio   = pedir("Código de rastreio", obrigatorio=False)
    remetente  = pedir("Remetente", obrigatorio=False)

    resultado = encomendas.receber_encomenda(
        descricao=descricao,
        unidade_destino=unidade,
        operador_id=sessao["id"],
        codigo_rastreio=rastreio,
        remetente=remetente,
    )

    if resultado["ok"]:
        print(f"  {C.ok(resultado['mensagem'])}")
    else:
        print(f"  {C.erro(resultado['mensagem'])}")
    pausar()

def _retirar_encomenda():
    limpar_tela()
    cabecalho("Processar Retirada de Encomenda")

    pendentes = encomendas.listar_encomendas_pendentes()
    if not pendentes:
        print(C.info("  Nenhuma encomenda pendente."))
        pausar()
        return

    _exibir_tabela_encomendas(pendentes)
    separador()
    print(C.aviso("  A senha de confirmação do morador é obrigatória para liberar a encomenda.\n"))

    try:
        eid = int(pedir("ID da encomenda"))
    except ValueError:
        print(C.erro("ID inválido."))
        pausar()
        return

    retirada_por = pedir("Nome de quem está retirando")
    senha = pedir("Senha de confirmação do morador", oculto=True)

    resultado = encomendas.retirar_encomenda(
        encomenda_id=eid,
        senha_confirmacao=senha,
        retirada_por=retirada_por,
        operador_id=sessao["id"],
    )

    if resultado["ok"]:
        print(f"\n  {C.ok(resultado['mensagem'])}")
    else:
        print(f"\n  {C.erro(resultado['mensagem'])}")
    pausar()

def _encomendas_pendentes():
    limpar_tela()
    cabecalho("Encomendas Pendentes")
    pendentes = encomendas.listar_encomendas_pendentes()
    if not pendentes:
        print(C.info("  Nenhuma encomenda pendente no momento."))
    else:
        _exibir_tabela_encomendas(pendentes)
    pausar()

def _historico_encomendas():
    limpar_tela()
    cabecalho("Histórico de Encomendas", "Últimas 20")
    hist = encomendas.listar_encomendas_recentes(20)
    if not hist:
        print(C.info("  Nenhuma encomenda registrada."))
    else:
        _exibir_tabela_encomendas(hist)
    pausar()

def _exibir_tabela_encomendas(enc_list: list):
    colunas = ["ID", "Unidade", "Descrição", "Status", "Recebida em", "Rastreio"]
    linhas = [[
        e["id"],
        e["unidade_destino"],
        e["descricao"][:25],
        status_badge(e["status"]),
        e["recebida_em"][:16],
        (e["codigo_rastreio"] or "-")[:15],
    ] for e in enc_list]
    tabela(colunas, linhas, [4, 8, 27, 18, 16, 17])

# ═══════════════════════════════════════════════════════════════════
# TRILHA DE AUDITORIA
# ═══════════════════════════════════════════════════════════════════

def menu_auditoria():
    while True:
        limpar_tela()
        total = auditoria.total_eventos()
        cabecalho("Trilha de Auditoria", f"Total de eventos registrados: {total}")

        escolha = menu("Auditoria", [
            "Ver eventos recentes (todos)",
            "Filtrar por módulo",
            "Inspecionar payload JSON de um evento",
        ])

        if escolha == -1:
            break
        elif escolha == 0:
            _auditoria_recente()
        elif escolha == 1:
            _auditoria_por_modulo()
        elif escolha == 2:
            _inspecionar_evento()

def _auditoria_recente(modulo=None, limite=30):
    limpar_tela()
    cabecalho("Trilha de Auditoria", f"Módulo: {modulo or 'todos'} · Últimos {limite} eventos")

    eventos = auditoria.buscar_trilha(modulo=modulo, limite=limite)
    if not eventos:
        print(C.info("  Nenhum evento encontrado."))
        pausar()
        return

    colunas = ["ID", "Ação", "Módulo", "Operador", "Data/Hora"]
    linhas = [[
        e["id"],
        e["acao"][:25],
        e["modulo"],
        (e["operador_login"] or "sistema")[:15],
        e["registrado_em"][:16],
    ] for e in eventos]
    tabela(colunas, linhas, [5, 27, 10, 17, 16])
    pausar()

def _auditoria_por_modulo():
    modulos = ["acesso", "encomenda", "sistema", "operador", "morador"]
    escolha = menu("Filtrar por módulo", [m.capitalize() for m in modulos])
    if escolha == -1:
        return
    _auditoria_recente(modulo=modulos[escolha])

def _inspecionar_evento():
    limpar_tela()
    cabecalho("Inspecionar Evento de Auditoria")

    try:
        eid = int(pedir("ID do evento"))
    except ValueError:
        print(C.erro("ID inválido."))
        pausar()
        return

    from db.database import get_connection
    conn = get_connection()
    ev = conn.execute(
        """
        SELECT a.*, o.nome AS op_nome, o.login AS op_login
        FROM auditoria a
        LEFT JOIN operadores o ON o.id = a.operador_id
        WHERE a.id = ?
        """,
        (eid,),
    ).fetchone()
    conn.close()

    if not ev:
        print(C.erro("Evento não encontrado."))
        pausar()
        return

    separador("Metadados")
    print(f"  ID:          {ev['id']}")
    print(f"  Ação:        {C.BOLD}{ev['acao']}{C.RESET}")
    print(f"  Módulo:      {ev['modulo']}")
    print(f"  Operador:    {ev['op_nome'] or 'Sistema'} ({ev['op_login'] or '-'})")
    print(f"  Registrado:  {ev['registrado_em']}")
    print(f"  IP:          {ev['ip_origem'] or '-'}")
    exibir_json_formatado(ev["payload_json"], titulo="Payload JSON:")
    pausar()

# ═══════════════════════════════════════════════════════════════════
# GESTÃO DE OPERADORES (apenas admin)
# ═══════════════════════════════════════════════════════════════════

def menu_operadores():
    while True:
        limpar_tela()
        cabecalho("Gerenciar Operadores", "Apenas administradores")

        escolha = menu("Operadores", [
            "Listar operadores",
            "Cadastrar novo operador",
            "Desativar operador",
        ])

        if escolha == -1:
            break
        elif escolha == 0:
            _listar_operadores()
        elif escolha == 1:
            _cadastrar_operador()
        elif escolha == 2:
            _desativar_operador()

def _listar_operadores():
    limpar_tela()
    cabecalho("Operadores Cadastrados")
    ops = auth.listar_operadores()
    colunas = ["ID", "Nome", "Login", "Perfil", "Ativo"]
    linhas = [[o["id"], o["nome"][:25], o["login"], o["perfil"], "✓" if o["ativo"] else "✗"]
              for o in ops]
    tabela(colunas, linhas, [4, 27, 15, 10, 6])
    pausar()

def _cadastrar_operador():
    limpar_tela()
    cabecalho("Cadastrar Novo Operador")

    nome   = pedir("Nome completo")
    login  = pedir("Login (único)")
    senha  = pedir("Senha", oculto=True)
    perfis = ["porteiro", "admin"]
    idx    = menu("Perfil", ["Porteiro", "Admin"])
    if idx == -1:
        return
    perfil = perfis[idx]

    resultado = auth.criar_operador(nome, login, senha, perfil, sessao["id"])
    if resultado["ok"]:
        print(f"\n  {C.ok(resultado['mensagem'])}")
    else:
        print(f"\n  {C.erro(resultado['mensagem'])}")
    pausar()

def _desativar_operador():
    _listar_operadores()
    try:
        oid = int(pedir("ID do operador para desativar"))
    except ValueError:
        print(C.erro("ID inválido."))
        pausar()
        return

    if confirmar(f"Confirma desativação do operador #{oid}?"):
        resultado = auth.desativar_operador(oid, sessao["id"])
        if resultado["ok"]:
            print(C.ok(resultado["mensagem"]))
        else:
            print(C.erro(resultado["mensagem"]))
    pausar()

# ═══════════════════════════════════════════════════════════════════
# GESTÃO DE MORADORES (apenas admin)
# ═══════════════════════════════════════════════════════════════════

def menu_moradores():
    while True:
        limpar_tela()
        cabecalho("Gerenciar Moradores")

        escolha = menu("Moradores", [
            "Listar moradores",
            "Cadastrar morador",
            "Desativar morador",
        ])

        if escolha == -1:
            break
        elif escolha == 0:
            _listar_moradores()
        elif escolha == 1:
            _cadastrar_morador()
        elif escolha == 2:
            _desativar_morador()

def _listar_moradores():
    limpar_tela()
    cabecalho("Moradores Cadastrados")
    mors = auth.listar_moradores()
    colunas = ["ID", "Nome", "Unidade", "Telefone", "Ativo"]
    linhas = [[m["id"], m["nome"][:25], m["unidade"], m["telefone"] or "-", "✓" if m["ativo"] else "✗"]
              for m in mors]
    tabela(colunas, linhas, [4, 27, 8, 15, 6])
    pausar()

def _cadastrar_morador():
    limpar_tela()
    cabecalho("Cadastrar Morador")

    nome    = pedir("Nome do morador")
    unidade = pedir("Unidade (ex: 101, B204)")
    tel     = pedir("Telefone", obrigatorio=False)

    print(C.info("\n  A senha de encomenda será exigida na retirada de pacotes."))
    senha = pedir("Senha de confirmação de encomenda", oculto=True)

    resultado = auth.criar_morador(nome, unidade, senha, sessao["id"], tel)
    if resultado["ok"]:
        print(f"\n  {C.ok(resultado['mensagem'])}")
    else:
        print(f"\n  {C.erro(resultado['mensagem'])}")
    pausar()


def _desativar_morador():
    _listar_moradores()
    try:
        mid = int(pedir("ID do morador para desativar"))
    except ValueError:
        print(C.erro("ID inválido."))
        pausar()
        return
    if confirmar(f"Confirma desativação do morador #{mid}?"):
        resultado = auth.desativar_morador(mid, sessao["id"])
        print(C.ok(resultado["mensagem"]) if resultado["ok"] else C.erro(resultado["mensagem"]))
    pausar()


# ═══════════════════════════════════════════════════════════════════
# SEED — dados iniciais para demonstração
# ═══════════════════════════════════════════════════════════════════

def _seed_dados_iniciais():
    """Popula o banco com dados de exemplo se ainda não existirem."""
    from db.database import get_connection
    conn = get_connection()
    existe = conn.execute("SELECT id FROM operadores WHERE login = 'admin'").fetchone()
    conn.close()

    if existe:
        return

    import hashlib
    def h(s): return hashlib.sha256(s.encode()).hexdigest()

    conn = get_connection()

    conn.execute("INSERT INTO operadores (nome, login, senha_hash, perfil) VALUES (?,?,?,?)",
                 ("Administrador", "admin", h("admin123"), "admin"))
    conn.execute("INSERT INTO operadores (nome, login, senha_hash, perfil) VALUES (?,?,?,?)",
                 ("João Porteiro", "joao", h("porteiro123"), "porteiro"))

    conn.execute("INSERT INTO moradores (nome, unidade, telefone, senha_encomenda) VALUES (?,?,?,?)",
                 ("Maria Silva", "101", "11999990001", "1234"))
    conn.execute("INSERT INTO moradores (nome, unidade, telefone, senha_encomenda) VALUES (?,?,?,?)",
                 ("Carlos Souza", "202", "11999990002", "5678"))
    conn.execute("INSERT INTO moradores (nome, unidade, telefone, senha_encomenda) VALUES (?,?,?,?)",
                 ("Ana Lima", "303", "11999990003", "9999"))

    conn.execute("""
        INSERT INTO regras_acesso (descricao, tipo_visita, hora_inicio, hora_fim, dias_semana)
        VALUES (?,?,?,?,?)
    """, ("Visitantes horário comercial", "visitante", "08:00", "22:00", "seg,ter,qua,qui,sex,sab,dom"))
    conn.execute("""
        INSERT INTO regras_acesso (descricao, tipo_visita, hora_inicio, hora_fim, dias_semana)
        VALUES (?,?,?,?,?)
    """, ("Prestadores dias úteis", "prestador", "08:00", "18:00", "seg,ter,qua,qui,sex"))
    conn.execute("""
        INSERT INTO regras_acesso (descricao, tipo_visita, hora_inicio, hora_fim, dias_semana)
        VALUES (?,?,?,?,?)
    """, ("Entregadores horário amplo", "entregador", "07:00", "21:00", "seg,ter,qua,qui,sex,sab"))

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════

def main():
    init_db()
    _seed_dados_iniciais()

    limpar_tela()
    cabecalho("Sistema de Portaria", "v1.0  ·  Controle · Logística · Auditoria")
    print(f"""
  {C.BOLD}Credenciais de demonstração:{C.RESET}

  {C.CYAN}Admin{C.RESET}    →  login: {C.BOLD}admin{C.RESET}     senha: {C.BOLD}admin123{C.RESET}
  {C.CYAN}Porteiro{C.RESET} →  login: {C.BOLD}joao{C.RESET}      senha: {C.BOLD}porteiro123{C.RESET}

  {C.GRAY}Moradores de exemplo: unidades 101, 202, 303{C.RESET}
  {C.GRAY}Senhas de encomenda:  1234  /  5678  /  9999{C.RESET}
    """)
    pausar()

    while True:
        if not sessao:
            tela_login()
        else:
            menu_principal()


if __name__ == "__main__":
    main()