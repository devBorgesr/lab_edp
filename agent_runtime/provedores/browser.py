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
import threading
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..contrato import Observacao, ProvedorDeCapacidade

PROTOCOLO = "edp.browser.v1"

#: Comandos CDP que `browser.inspect` significa. Esta lista NAO VIAJA pelo
#: canal: o controller tem a dele e nao consulta esta. Mandar a lista pelo fio
#: criaria uma superficie onde alguem poderia tentar influenciar quais comandos
#: rodam — e "capacidade" deixaria de ser a fronteira. Ela fica aqui como
#: documentacao verificavel do que a capacidade custa, e como teste de que
#: nada de escrita entrou.
COMANDOS_INSPECT = ("Page.getNavigationHistory", "DOM.getDocument",
                    "Runtime.evaluate")

#: Chaves de observacao que o provedor aceita de volta. Objeto Chrome cru nao
#: atravessa esta fronteira.
CAMPOS_OBS = {"kind", "url", "title", "dom_nodes", "history_len", "erro"}


#: Ciclo de vida do alvo. `REGISTRADO` NAO e operacional: o Runtime pode ter
#: aceitado a aba enquanto `chrome.debugger.attach` ainda vai falhar. Tratar os
#: dois como a mesma coisa deixaria o Runtime afirmando "alvo pronto" sobre uma
#: aba a que ninguem esta anexado.
REGISTRADO, ANEXANDO, ANEXADO, FALHOU = ("REGISTRADO", "ANEXANDO", "ANEXADO",
                                         "FALHOU")
OPERACIONAL = (ANEXADO,)

TRANSICOES_ALVO: dict[str, tuple[str, ...]] = {
    REGISTRADO: (ANEXANDO, FALHOU),
    ANEXANDO:   (ANEXADO, FALHOU),
    ANEXADO:    (FALHOU,),      # detach/aba fechada derrubam; nao "voltam"
    FALHOU:     (),             # some do registro; nao se recupera no lugar
}


class AlvoInvalido(RuntimeError):
    """O alvo pedido nao e o alvo registrado. Nunca e aviso: recusa."""


class AlvoNaoOperacional(RuntimeError):
    """
    Ha alvo registrado, mas o debugger ainda nao esta anexado a ele.

    Erro proprio, e nao `AlvoInvalido`: "voce pediu a aba errada" e "a aba
    certa ainda nao esta pronta" pedem coisas diferentes de quem chamou.
    """


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


class RegistroDeAlvos:
    """
    `client_id -> (alvo, estado)`. Compartilhado entre os endpoints HTTP (que
    escrevem) e o provedor (que le na hora de executar).

    Existir era o buraco: `POST /v1/browser/alvo` guardava o alvo, e o
    provedor da tarefa usava outro, montado na construcao do app. As duas
    metades estavam certas e nao se falavam.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._por_cliente: dict[str, tuple[AlvoDashboard, str]] = {}

    def define(self, client_id: str, alvo: "AlvoDashboard") -> str:
        with self._lock:
            self._por_cliente[client_id] = (alvo, REGISTRADO)
        return REGISTRADO

    def transita(self, client_id: str, novo: str) -> str:
        with self._lock:
            atual = self._por_cliente.get(client_id)
            if atual is None:
                raise AlvoInvalido(f"nenhum alvo registrado para {client_id!r}")
            alvo, estado = atual
            if novo == estado:
                return estado
            if novo not in TRANSICOES_ALVO.get(estado, ()):
                raise AlvoInvalido(
                    f"{estado} -> {novo} nao e transicao de alvo valida")
            if novo == FALHOU:
                # FALHOU nao fica no registro: um alvo que falhou o attach nao
                # e um alvo em estado ruim, e a ausencia de alvo.
                self._por_cliente.pop(client_id, None)
                return FALHOU
            self._por_cliente[client_id] = (alvo, novo)
            return novo

    def estado(self, client_id: str) -> str | None:
        with self._lock:
            a = self._por_cliente.get(client_id)
            return a[1] if a else None

    def para(self, client_id: str) -> "AlvoDashboard":
        """
        So devolve alvo OPERACIONAL. Registrado-mas-nao-anexado levanta —
        executar assim faria o comando morrer no controller, e o modelo leria
        o erro como fato sobre a pagina.
        """
        with self._lock:
            a = self._por_cliente.get(client_id)
        if a is None:
            raise AlvoNaoOperacional(
                f"nenhum alvo registrado para {client_id!r}. O painel precisa "
                f"chamar POST /v1/browser/alvo e anexar antes.")
        alvo, estado = a
        if estado not in OPERACIONAL:
            raise AlvoNaoOperacional(
                f"alvo em {estado}; o debugger ainda nao esta anexado")
        return alvo

    def esquece(self, client_id: str) -> None:
        with self._lock:
            self._por_cliente.pop(client_id, None)


class AlvoFixo:
    """Um alvo so, para teste unitario. Ignora `client_id` de proposito."""

    def __init__(self, alvo: "AlvoDashboard"):
        self._alvo = alvo

    def para(self, client_id: str) -> "AlvoDashboard":
        return self._alvo

    def estado(self, client_id: str) -> str:
        return ANEXADO


def canal_fixo(canal: CanalBrowser):
    """`canal_de` de um canal so, para teste unitario."""
    return lambda _client_id: canal


class ChromeDebuggerProvider(ProvedorDeCapacidade):
    """
    Traduz capacidade em solicitacao; normaliza a resposta em `Observacao`.

    NAO reaproveita as invariantes do `debugger_capturer.js`. Aquele modulo
    continua sendo o capturador de trafego, so observacao; este e o componente
    autorizado a falar CDP em nome do agente. Tratar as duas coisas como uma
    faria a promessa antiga cobrir codigo que ela nunca examinou.
    """
    nome = "chrome_debugger"

    def __init__(self, canal_de, alvos, dono_da_tarefa=None,
                 timeout_s: float = 10.0):
        """
        `canal_de(client_id) -> CanalBrowser` e `alvos.para(client_id)`.

        O alvo e resolvido NA HORA DE EXECUTAR, e nao na construcao. Fixa-lo
        aqui foi o defeito da primeira versao: o endpoint que registrava a aba
        e o provedor que executava a tarefa guardavam alvos diferentes.

        `dono_da_tarefa(tarefa_id) -> client_id` diz em nome de quem o provedor
        age. Sem isso, uma tarefa de um cliente usaria a aba de outro.
        """
        self.canal_de = canal_de
        self.alvos = alvos
        self.dono_da_tarefa = dono_da_tarefa or (lambda _tid: "default")
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

        client_id = self.dono_da_tarefa(tarefa_id) or "default"
        alvo = self.alvos.para(client_id)      # levanta se nao operacional

        # O alvo NAO vem do modelo. Se `parametros` trouxer tab_id/origin, eles
        # sao conferidos contra o registro e recusados se divergirem — nunca
        # usados no lugar dele.
        alvo.confere(parametros.get("tab_id", alvo.tab_id),
                     parametros.get("origin", alvo.origin))

        solicitacao = {
            "protocol": PROTOCOLO,
            "kind": "capability.request",
            "capability": "browser.inspect",
            "target": {"tab_id": alvo.tab_id, "origin": alvo.origin,
                       "session_id": alvo.session_id},
            "parameters": {},          # esta capacidade nao recebe parametro
        }
        try:
            bruto = self.canal_de(client_id).pede(solicitacao, self.timeout_s)
        except (AlvoInvalido, AlvoNaoOperacional):
            raise
        except CanalIndisponivel:
            raise
        except Exception as e:
            raise CanalIndisponivel(f"{type(e).__name__}: {e}") from e

        return self._normaliza(bruto, tarefa_id, iteracao, alvo)

    def _normaliza(self, bruto: dict[str, Any], tarefa_id: str,
                   iteracao: int, alvo: AlvoDashboard) -> list[Observacao]:
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
        if bruto.get("kind") != "capability.result":
            raise CanalIndisponivel(f"kind inesperado: {bruto.get('kind')!r}")
        if bruto.get("type") != "browser.observation":
            raise CanalIndisponivel(f"type inesperado: {bruto.get('type')!r}")

        vindo = bruto.get("target") or {}
        # Confere o alvo NA VOLTA tambem: a extensao pode ter anexado noutra
        # aba, por defeito ou por corrida com o usuario trocando de aba.
        alvo.confere(vindo.get("tab_id"), vindo.get("origin"))

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
                fonte=f"chrome.debugger tab={alvo.tab_id}"))
        if not obs:
            # Lista vazia e observacao valida ("nao achei nada"), e o contrato
            # de ProvedorDeCapacidade diz isso. Mas devolver [] silenciosamente
            # aqui esconderia uma resposta malformada — entao registra o fato.
            obs.append(Observacao(
                capacidade="browser.inspect", tarefa_id=tarefa_id,
                iteracao=iteracao,
                dados={"kind": "page", "erro": "extensao devolveu 0 observacoes"},
                fonte=f"chrome.debugger tab={alvo.tab_id}"))
        return obs
