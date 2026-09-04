"""
`MesaDeSolicitacoes` — o canal real entre o provedor Python e o painel.

O PROBLEMA QUE ELE RESOLVE

O Runtime nao pode iniciar nada em direcao a uma extensao: nenhum processo
externo pode. Entao a direcao se inverte na implementacao, mas NAO na
arquitetura: o provedor continua "pedindo", e o painel e quem busca o pedido.

    provedor  --publica-->  MESA  <--busca--  painel
    provedor  <--espera---  MESA  <--responde--  painel

`ChromeDebuggerProvider` nao sabe disto. Ele fala com `CanalBrowser`, e este
modulo e uma implementacao. WebSocket ou Native Messaging trocam so a
implementacao — o provedor, o Registry e a Politica ficam intactos.

`request_id` E OBRIGATORIO, E NAO E DECORACAO

Duas solicitacoes simultaneas sobre a mesma mesa sao normais: duas tarefas, ou
duas iteracoes que se sobrepoem. Sem correlacao, a resposta de uma vira
observacao da outra — e o modelo receberia como fato do ambiente algo que
pertence a outra tarefa. Uma resposta sem `request_id` conhecido e DESCARTADA,
nunca entregue ao pedido mais proximo.

ISOLAMENTO POR CLIENTE

Cada solicitacao carrega o `client_id` de quem a criou, e o painel so recebe
as do proprio cliente. Sem isso, um painel autenticado como um cliente
executaria comando pedido por outro.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .provedores.browser import PROTOCOLO, CanalIndisponivel

#: Teto de solicitacoes vivas. Uma mesa sem teto vira vazamento quando o
#: painel some: cada tarefa publica, ninguem busca, nada expira.
MAX_PENDENTES = 64

#: Depois disto uma solicitacao nao buscada e considerada morta e removida.
#: Nao e o timeout do provedor — e a faxina da mesa.
TTL_S = 120.0


@dataclass
class Pendente:
    request_id:  str
    client_id:   str
    solicitacao: dict[str, Any]
    criado_em:   float
    evento:      threading.Event = field(default_factory=threading.Event)
    resposta:    dict[str, Any] | None = None
    buscado_em:  float | None = None


class MesaDeSolicitacoes:
    """Compartilhada entre o provedor (que espera) e o HTTP (que serve)."""

    def __init__(self, max_pendentes: int = MAX_PENDENTES, ttl_s: float = TTL_S):
        self._lock = threading.Lock()
        self._fila: list[str] = []                  # ordem de publicacao
        self._por_id: dict[str, Pendente] = {}
        self.max_pendentes = max_pendentes
        self.ttl_s = ttl_s

    # ── lado do provedor ────────────────────────────────────────────────────

    def publica(self, solicitacao: dict[str, Any], client_id: str) -> Pendente:
        with self._lock:
            self._faxina()
            if len(self._por_id) >= self.max_pendentes:
                raise CanalIndisponivel(
                    f"mesa cheia ({self.max_pendentes} solicitacoes vivas). "
                    f"O painel nao esta buscando — nenhuma capacidade de "
                    f"navegador pode ser executada agora.")
            rid = f"R-{uuid.uuid4().hex[:12]}"
            p = Pendente(request_id=rid, client_id=client_id,
                         solicitacao={**solicitacao,
                                      "kind": "capability.request",
                                      "request_id": rid},
                         criado_em=time.time())
            self._por_id[rid] = p
            self._fila.append(rid)
            return p

    def espera(self, p: Pendente, timeout_s: float) -> dict[str, Any]:
        """
        Bloqueia ate a resposta chegar. Timeout REMOVE a solicitacao: deixa-la
        na mesa faria o painel executar, mais tarde, um comando que ninguem
        mais espera — atuacao sem destinatario.
        """
        if not p.evento.wait(timeout_s):
            with self._lock:
                self._remove(p.request_id)
            raise CanalIndisponivel(
                f"o painel nao respondeu em {timeout_s}s (request_id={p.request_id})")
        with self._lock:
            self._remove(p.request_id)
        return p.resposta or {}

    # ── lado do painel ──────────────────────────────────────────────────────

    def proxima(self, client_id: str) -> dict[str, Any] | None:
        """
        Devolve a solicitacao mais antiga AINDA NAO BUSCADA deste cliente.

        Marcar como buscada impede que dois polls do mesmo painel executem o
        mesmo comando duas vezes — CDP nao e idempotente em geral, e mesmo
        `inspect` gastaria duas anexacoes.
        """
        with self._lock:
            self._faxina()
            for rid in self._fila:
                p = self._por_id.get(rid)
                if p and p.buscado_em is None and p.client_id == client_id:
                    p.buscado_em = time.time()
                    return dict(p.solicitacao)
        return None

    def responde(self, resposta: dict[str, Any], client_id: str) -> bool:
        """
        `False` quando a resposta nao corresponde a nenhum pedido vivo DESTE
        cliente. Nunca entrega ao pedido mais proximo: resposta sem dono e
        resposta descartada.
        """
        if not isinstance(resposta, dict):
            return False
        if resposta.get("protocol") != PROTOCOLO:
            return False
        rid = resposta.get("request_id")
        if not isinstance(rid, str) or not rid:
            return False
        with self._lock:
            p = self._por_id.get(rid)
            if p is None or p.client_id != client_id or p.resposta is not None:
                return False
            p.resposta = resposta
            p.evento.set()
            return True

    # ── manutencao ──────────────────────────────────────────────────────────

    def _remove(self, rid: str) -> None:
        self._por_id.pop(rid, None)
        try:
            self._fila.remove(rid)
        except ValueError:
            pass

    def _faxina(self) -> None:
        agora = time.time()
        for rid in [r for r in self._fila
                    if agora - self._por_id[r].criado_em > self.ttl_s]:
            p = self._por_id.get(rid)
            if p is not None and p.resposta is None:
                p.evento.set()          # desbloqueia quem espera
            self._remove(rid)

    def vivas(self) -> int:
        with self._lock:
            return len(self._por_id)


class CanalMesa:
    """
    `CanalBrowser` sobre a mesa. E o adaptador — nao guarda estado proprio.
    """

    def __init__(self, mesa: MesaDeSolicitacoes, client_id: str = "default"):
        self.mesa = mesa
        self.client_id = client_id

    def pede(self, solicitacao: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        p = self.mesa.publica(solicitacao, self.client_id)
        r = self.mesa.espera(p, timeout_s)
        # O `request_id` volta conferido: uma resposta que chegou pela mesa mas
        # cita outro pedido nao pode virar observacao deste.
        if r.get("request_id") != p.request_id:
            raise CanalIndisponivel(
                f"resposta com request_id {r.get('request_id')!r} para o "
                f"pedido {p.request_id!r}")
        if r.get("type") == "browser.error":
            raise CanalIndisponivel(f"painel recusou: {r.get('error')}")
        return r
