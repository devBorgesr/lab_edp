"""
Catalogo de capacidades. O que um agente PODE pedir, e o que isso custa.

TRES NIVEIS, e a fronteira entre eles nao e estilistica:

    L0  OBSERVAR    le o ambiente. Nao altera nada.
    L1  ALTERAR     muda a pagina do usuario. Reversivel, escopo local.
    L2  PRIVILEGIADO navega, baixa, toca credencial ou rede. Nao reversivel
                     por conta propria.

POR QUE L1 E L2 ESTAO DECLARADOS E NAO IMPLEMENTADOS

`sf_exportador/claude-exporter-v4.2/copilot/debugger_capturer.js` carrega um
bloco chamado "O que este modulo NUNCA FAZ", e ele diz, textualmente:

    nunca Input.*, Page.navigate, Page.reload ou qualquer comando que ALTERE
    a aba. So observa.

Isso nao e uma lacuna de engenharia — e uma fronteira de seguranca escrita de
proposito, no modulo que fala com o `chrome.debugger`. O mesmo arquivo redige
`authorization`, `cookie` e `x-api-key` por default.

Implementar L1/L2 significa ROMPER essa fronteira. Isso e decisao do
pesquisador, com consequencia declarada, e esta em
`docs/agent_runtime/DECISAO_ATUACAO.md` — em branco. Ate la, pedir uma
capacidade L1/L2 levanta `CapacidadeNaoImplementada`, com o ponteiro para o
documento. Nunca degrada em silencio para "nao fez nada".
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Nivel(IntEnum):
    OBSERVAR = 0
    ALTERAR = 1
    PRIVILEGIADO = 2


class CapacidadeDesconhecida(KeyError):
    """Nome fora do catalogo. Provedor nao inventa capacidade."""


class CapacidadeNaoImplementada(NotImplementedError):
    """
    Declarada no catalogo, sem implementacao — por decisao pendente, nao por
    esquecimento. A mensagem diz onde a decisao mora.
    """


@dataclass(frozen=True)
class Capacidade:
    nome:       str
    nivel:      Nivel
    o_que_faz:  str
    toca:       str          # o que do ambiente esta em jogo
    reversivel: bool
    implementada: bool


def _c(nome, nivel, o_que_faz, toca, reversivel, implementada):
    return Capacidade(nome, nivel, o_que_faz, toca, reversivel, implementada)


CATALOGO: dict[str, Capacidade] = {c.nome: c for c in [
    # ── L0 — observar ───────────────────────────────────────────────────────
    _c("observe.network", Nivel.OBSERVAR,
       "le requisicoes e respostas ja capturadas",
       "trafego da aba, ja redigido pelo capturador", True, True),
    _c("observe.console", Nivel.OBSERVAR,
       "le mensagens de console ja capturadas",
       "saida de console da aba", True, True),
    _c("analyze.json", Nivel.OBSERVAR,
       "estrutura e resume um corpo JSON ja observado",
       "nada do ambiente — so o que ja foi colhido", True, True),
    _c("memory.read", Nivel.OBSERVAR,
       "le a memoria da propria tarefa",
       "memoria do runtime", True, True),
    _c("memory.write", Nivel.OBSERVAR,
       "grava conclusao/hipotese na memoria da tarefa",
       "memoria do runtime — NAO o store do EDP", True, True),

    # ── L1 — alterar a pagina do usuario ────────────────────────────────────
    _c("act.click", Nivel.ALTERAR,
       "clica em um elemento",
       "DOM da aba do usuario", False, False),
    _c("act.fill", Nivel.ALTERAR,
       "preenche um campo",
       "DOM e possivelmente dado do usuario", False, False),
    _c("act.javascript", Nivel.ALTERAR,
       "executa JS na pagina",
       "tudo que a pagina alcanca, incluindo sessao autenticada", False, False),
    _c("act.reload", Nivel.ALTERAR,
       "recarrega a aba",
       "estado nao salvo da pagina", False, False),

    # ── L2 — privilegiado ───────────────────────────────────────────────────
    _c("act.navigate", Nivel.PRIVILEGIADO,
       "leva a aba para outra URL",
       "para onde o navegador autenticado do usuario vai", False, False),
    _c("act.download", Nivel.PRIVILEGIADO,
       "baixa arquivo",
       "disco do host", False, False),
    _c("act.network", Nivel.PRIVILEGIADO,
       "emite requisicao propria",
       "rede, com os cookies do usuario", False, False),
]}


def busca(nome: str) -> Capacidade:
    if nome not in CATALOGO:
        raise CapacidadeDesconhecida(
            f"capacidade '{nome}' nao existe no catalogo. Um provedor nao "
            f"pode inventar capacidade — se pudesse, a politica nao teria o "
            f"que autorizar. Conhecidas: {sorted(CATALOGO)}"
        )
    return CATALOGO[nome]


def exige_implementada(nome: str) -> Capacidade:
    c = busca(nome)
    if not c.implementada:
        raise CapacidadeNaoImplementada(
            f"'{nome}' e L{int(c.nivel)} e esta DECLARADA, nao implementada.\n"
            f"  o que faria: {c.o_que_faz}\n"
            f"  o que tocaria: {c.toca}\n"
            f"  reversivel: {'sim' if c.reversivel else 'NAO'}\n"
            f"Implementar exige romper o bloco 'O que este modulo NUNCA FAZ' "
            f"de debugger_capturer.js, que proibe qualquer comando CDP que "
            f"altere a aba. Decisao do pesquisador, em "
            f"docs/agent_runtime/DECISAO_ATUACAO.md (em branco)."
        )
    return c


def por_nivel(nivel: Nivel) -> list[str]:
    return sorted(n for n, c in CATALOGO.items() if c.nivel == nivel)
