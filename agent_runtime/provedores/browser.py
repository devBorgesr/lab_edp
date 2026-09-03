"""
`ChromeDebuggerProvider` — `chrome.debugger` como provedor de capacidade.

A REGRA QUE ESTE MODULO EXISTE PARA SUSTENTAR

O Python **nao chama** `chrome.debugger`. Nao pode: so um contexto de extensao
pode. Este provedor emite uma SOLICITACAO DE CAPACIDADE estruturada, a
extensao a executa, e devolve uma observacao normalizada.

    Runtime  ->  {"capability": "browser.inspect", "target": {...}}  ->  extensao
    extensao ->  {"type": "browser.observation", "observations": [...]}  ->  Runtime

O modelo **nunca** recebe `chrome.debugger.sendCommand()` e nunca fornece CDP
arbitrario. Ele pede uma capacidade pelo nome; o provedor decide quais comandos
CDP aquilo significa. Se o modelo pudesse escolher o comando, o Registry
deixaria de ser a superficie de capacidades e viraria decoracao.

TRANSPORTE E DETALHE SUBSTITUIVEL

`CanalBrowser` e um `Protocol`. O primeiro slice roda sobre o transporte que ja
existe; Native Messaging ou WebSocket trocam **so a implementacao do canal**,
sem tocar em provedor, Registry ou Politica. Por isso o canal e injetado e nao
construido aqui.

ESCOPO DE ABA: NO CODIGO, NAO NA INTENCAO

O argumento que torna esta capacidade aceitavel e que o alvo e o dashboard do
proprio EDP, e nao a aba autenticada de ninguem. Esse argumento **cai junto**
se o provedor puder anexar a qualquer aba. Entao o alvo e um registro
explicito, conferido antes de todo comando — nunca `tabs.query({active:true})`,
que responde "a aba que estiver na frente" e nao "a aba que foi autorizada".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..contrato import Observacao, ProvedorDeCapacidade

PROTOCOLO = "edp.browser.v1"

#: Comandos CDP que `browser.inspect` pode significar. Lista fechada: a
#: extensao recusa o que nao estiver aqui, e o Python tambem. Duas travas para
#: a mesma regra, porque so uma delas roda no navegador.
COMANDOS_INSPECT = ("Page.getNavigationHistory", "DOM.getDocument",
                    "Runtime.evaluate")

#: Chaves de observacao que o provedor aceita de volta. Objeto Chrome cru nao
#: atravessa esta fronteira.
CAMPOS_OBS = {"kind", "url", "title", "dom_nodes", "history_len", "erro"}


class AlvoInvalido(RuntimeError):
    """O alvo pedido nao e o alvo registrado. Nunca e aviso: recusa."""


class CanalIndisponivel(RuntimeError):
    """A extensao nao respondeu. Falha de transporte, nao veredito da pagina."""


@runtime_checkable
class CanalBrowser(Protocol):
    """
    O que o provedor precisa do transporte, e nada mais.

    Uma implementacao pode ser polling sobre o HTTP atual, WebSocket, ou
    Native Messaging. O provedor nao sabe qual, e nao deve saber.
    """

    def pede(self, solicitacao: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        """Envia a solicitacao e devolve a resposta bruta da extensao."""
        ...


@dataclass(frozen=True)
class AlvoDashboard:
    """
    A aba autorizada. `frozen` de proposito: um alvo que pode ser reescrito
    depois de registrado nao e escopo, e sugestao.
    """
    tab_id:      int
    origin:      str
    session_id:  str
    registrado_em: str

    def confere(self, tab_id: int | None, origin: str | None) -> None:
        if tab_id is None or int(tab_id) != self.tab_id:
            raise AlvoInvalido(
                f"tab_id {tab_id!r} nao e o alvo registrado ({self.tab_id})")
        if origin is None or origin != self.origin:
            raise AlvoInvalido(
                f"origin {origin!r} nao e a origem autorizada ({self.origin})")


_ORIGEM_LOCAL = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\])(:\d{1,5})?$")


def registra_alvo(tab_id: int, origin: str, session_id: str,
                  registrado_em: str, so_local: bool = True) -> AlvoDashboard:
    """
    Registra a aba do dashboard como alvo.

    `so_local` default `True`: a justificativa desta capacidade e que o alvo e
    a propria ferramenta, em loopback. Aceitar origem arbitraria aqui
    devolveria a capacidade para a categoria de risco que a decisao evitou —
    agir sobre a sessao autenticada de alguem.
    """
    if so_local and not _ORIGEM_LOCAL.match(origin or ""):
        raise AlvoInvalido(
            f"origem {origin!r} nao e loopback. O alvo autorizado desta "
            f"capacidade e o dashboard do proprio EDP; para outra origem, "
            f"a decisao e outra (ver docs/agent_runtime/DECISAO_ATUACAO.md).")
    if not isinstance(tab_id, int) or tab_id < 0:
        raise AlvoInvalido(f"tab_id invalido: {tab_id!r}")
    return AlvoDashboard(tab_id=tab_id, origin=origin, session_id=session_id,
                         registrado_em=registrado_em)


class ChromeDebuggerProvider(ProvedorDeCapacidade):
    """
    Traduz capacidade em solicitacao; normaliza a resposta em `Observacao`.

    NAO reaproveita as invariantes do `debugger_capturer.js`. Aquele modulo
    continua sendo o capturador de trafego, so observacao; este e o componente
    autorizado a falar CDP em nome do agente. Tratar as duas coisas como uma
    faria a promessa antiga cobrir codigo que ela nunca examinou.
    """
    nome = "chrome_debugger"

    def __init__(self, canal: CanalBrowser, alvo: AlvoDashboard,
                 timeout_s: float = 10.0):
        self.canal = canal
        self.alvo = alvo
        self.timeout_s = timeout_s

    def capacidades(self) -> set[str]:
        # UMA capacidade. As outras entram uma a uma, cada qual pelo Registry,
        # pela Politica e por teste proprio — nao por esta lista crescer.
        return {"browser.inspect"}

    def executa(self, capacidade: str, parametros: dict[str, Any],
                tarefa_id: str, iteracao: int) -> list[Observacao]:
        if capacidade != "browser.inspect":
            raise AlvoInvalido(
                f"'{capacidade}' nao e implementada por este provedor")

        # O alvo NAO vem do modelo. Se `parametros` trouxer tab_id/origin, eles
        # sao conferidos contra o registro e recusados se divergirem — nunca
        # usados no lugar dele.
        self.alvo.confere(parametros.get("tab_id", self.alvo.tab_id),
                          parametros.get("origin", self.alvo.origin))

        solicitacao = {
            "protocol": PROTOCOLO,
            "capability": "browser.inspect",
            "target": {"tab_id": self.alvo.tab_id, "origin": self.alvo.origin,
                       "session_id": self.alvo.session_id},
            "comandos": list(COMANDOS_INSPECT),
            "parameters": {},          # esta capacidade nao recebe parametro
        }
        try:
            bruto = self.canal.pede(solicitacao, self.timeout_s)
        except AlvoInvalido:
            raise
        except Exception as e:
            raise CanalIndisponivel(f"{type(e).__name__}: {e}") from e

        return self._normaliza(bruto, tarefa_id, iteracao)

    def _normaliza(self, bruto: dict[str, Any], tarefa_id: str,
                   iteracao: int) -> list[Observacao]:
        """
        Objeto Chrome cru nao atravessa esta fronteira.

        A extensao pode devolver qualquer coisa — e um processo que nao e este.
        Filtrar por lista de campos conhecidos evita que uma mudanca do lado do
        navegador vire, sem ninguem decidir, dado novo dentro da `Observacao`.
        """
        if not isinstance(bruto, dict):
            raise CanalIndisponivel(f"resposta nao e objeto: {type(bruto).__name__}")
        if bruto.get("protocol") != PROTOCOLO:
            raise CanalIndisponivel(
                f"protocolo {bruto.get('protocol')!r}; este provedor fala {PROTOCOLO!r}")
        if bruto.get("type") != "browser.observation":
            raise CanalIndisponivel(f"type inesperado: {bruto.get('type')!r}")

        alvo = bruto.get("target") or {}
        # Confere o alvo NA VOLTA tambem: a extensao pode ter anexado noutra
        # aba, por defeito ou por corrida com o usuario trocando de aba.
        self.alvo.confere(alvo.get("tab_id"), alvo.get("origin"))

        obs: list[Observacao] = []
        for item in (bruto.get("observations") or []):
            if not isinstance(item, dict):
                continue
            dados = {k: v for k, v in item.items() if k in CAMPOS_OBS}
            if not dados:
                continue
            obs.append(Observacao(
                capacidade="browser.inspect", tarefa_id=tarefa_id,
                iteracao=iteracao, dados=dados,
                fonte=f"chrome.debugger tab={self.alvo.tab_id}"))
        if not obs:
            # Lista vazia e observacao valida ("nao achei nada"), e o contrato
            # de ProvedorDeCapacidade diz isso. Mas devolver [] silenciosamente
            # aqui esconderia uma resposta malformada — entao registra o fato.
            obs.append(Observacao(
                capacidade="browser.inspect", tarefa_id=tarefa_id,
                iteracao=iteracao,
                dados={"kind": "page", "erro": "extensao devolveu 0 observacoes"},
                fonte=f"chrome.debugger tab={self.alvo.tab_id}"))
        return obs
