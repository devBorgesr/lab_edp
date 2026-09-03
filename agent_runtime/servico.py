"""
`TaskService` — a tarefa PERSISTIDA, e o boundary de entrada do Runtime.

POR QUE ISTO EXISTE (e por que nao existia)

A primeira versao do transporte rodava a tarefa DENTRO da requisicao HTTP e
devolvia o resultado na mesma resposta. Isso veio de ler "primeiro faca
request/response confiavel" como "execucao sincrona" — e nao e a mesma coisa.
`request/response` descreve o formato do transporte; nao diz onde a tarefa
executa.

A consequencia foi concreta: sem tarefa guardada nao ha o que consultar, e
`get_task`, `get_result`, `cancel_task`, idempotencia, isolamento entre
tarefas e consulta de estado ficaram todos impossiveis de uma vez.

Este modulo e a correcao. Ele guarda a tarefa em disco antes de executar,
executa fora da requisicao, e responde perguntas sobre ela depois.

O QUE ELE NAO SABE

Nada sobre HTTP. `transporte.py` chama este servico; este servico nao importa
`fastapi`, nao conhece status code, nao conhece header. Quem transporta nao
decide, e quem decide nao transporta.

POR QUE `_id_seguro` ESTA DUPLICADO AQUI

`auditor/tenancy.py` ja resolve exatamente isto, e melhor documentado. Nao e
importado de proposito: `agent_runtime/__init__.py` declara que esta linha de
produto NAO faz parte do MVP de auditoria e nao toca nele. Importar criaria a
dependencia que aquela frase existe para negar — e uma mudanca no isolamento
do auditor passaria a mudar o isolamento do runtime sem ninguem pedir.

A duplicacao e a decisao. Esta anotada nos dois lados.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .capacidades import Nivel
from .contrato import Observacao, ProvedorDeCapacidade
from .executor import Executor, Intencao
from .politica import Politica
from .requisicao import RequisicaoInvalida, para_tarefa
from .tarefa import EstadoTarefa, Tarefa

# ── estados do SERVICO ──────────────────────────────────────────────────────
#
# Nao sao os de `EstadoTarefa`. A tarefa nao sabe que foi enfileirada nem que
# alguem pediu cancelamento — sao fatos do servico, nao do loop. Os terminais
# da tarefa entram aqui por valor, para que o cliente leia UMA palavra sobre o
# que aconteceu, e nao duas que precisem ser reconciliadas.
RECEBIDA, EXECUTANDO, CANCELADA = "RECEBIDA", "EXECUTANDO", "CANCELADA"
CONCLUIDA, ESGOTADA = "CONCLUIDA", "ESGOTADA"
BLOQUEADA, FALHA = "BLOQUEADA", "FALHA"

TERMINAIS = (CONCLUIDA, ESGOTADA, BLOQUEADA, FALHA, CANCELADA)

#: Terminal nao volta. Sem isto, um retry mal escrito levaria CANCELADA de
#: volta a EXECUTANDO e depois a CONCLUIDA — e o cliente leria "terminou bem"
#: numa tarefa que ele mandou parar.
TRANSICOES: dict[str, tuple[str, ...]] = {
    RECEBIDA:   (EXECUTANDO, CANCELADA, FALHA),
    EXECUTANDO: (CONCLUIDA, ESGOTADA, BLOQUEADA, FALHA, CANCELADA),
    CONCLUIDA: (), ESGOTADA: (), BLOQUEADA: (), FALHA: (), CANCELADA: (),
}

#: `EstadoTarefa` terminal -> estado do servico. O mapa e explicito porque
#: derivar por nome faria um `EstadoTarefa` novo virar `FALHA` silenciosamente.
DE_TAREFA = {
    EstadoTarefa.CONCLUIDA:  CONCLUIDA,
    EstadoTarefa.ESGOTADA:   ESGOTADA,
    EstadoTarefa.BLOQUEADA:  BLOQUEADA,
    EstadoTarefa.FALHA:      FALHA,
    EstadoTarefa.DECLARADA:  FALHA,   # nunca saiu de DECLARADA: o loop abortou
    EstadoTarefa.EXECUTANDO: FALHA,   # ficou EXECUTANDO no fim: idem
}


class TransicaoInvalida(RuntimeError):
    """Mudanca de estado que o servico nao admite."""


class EstadoImpossivel(RuntimeError):
    """Registro internamente inconsistente — nao pode ser gravado."""


class TaskIdInvalido(ValueError):
    """Id que nao pode compor caminho."""


class Cancelada(Exception):
    """
    Levantada pelo propositor embrulhado quando alguem pediu cancelamento.

    Escapa de `Executor.roda` de proposito: o executor embrulha excecao do
    PROVEDOR, nao do propositor (`executor.py:117`). Cancelar por excecao
    aproveita esse caminho sem tocar no Executor, e sem que ele precise
    aprender o que e cancelamento.

    A alternativa — devolver `Intencao(concluir=True)` — marcaria a tarefa
    CONCLUIDA. Uma tarefa que o operador mandou parar nao concluiu nada.
    """


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def _id_seguro(v: str) -> bool:
    return bool(v) and ".." not in v and "/" not in v and bool(_ID.match(v))


def exige_task_id(task_id: str) -> str:
    """
    O `task_id` COMPOE O CAMINHO em disco. Um id como `../outro/x` leria o
    registro de outra tarefa — a defesa e recusar o id, nao normalizar depois.
    """
    if not _id_seguro(task_id):
        raise TaskIdInvalido(f"task_id invalido: {task_id!r}")
    return task_id


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class RegistroDeTarefa:
    task_id:        str
    status:         str = RECEBIDA
    client_id:      str = "default"
    request_id:     str | None = None      # idempotencia
    correlation_id: str | None = None      # rastreio do lado do cliente
    created_at:     str = field(default_factory=agora)
    updated_at:     str = field(default_factory=agora)
    started_at:     str | None = None
    finished_at:    str | None = None
    objetivo:       str = ""
    capacidades:    list[str] = field(default_factory=list)
    criada_por:     str = ""
    iteracoes:      int = 0
    motivo_parada:  str = ""
    negadas:        list[str] = field(default_factory=list)
    observacoes:    list[dict[str, Any]] = field(default_factory=list)
    duracao_ms:     float | None = None
    erro:           str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAIS

    def confere(self) -> None:
        """
        Estado impossivel nao chega ao disco.

        Um registro CONCLUIDA sem objetivo, ou FALHA sem erro, e pior que um
        registro com defeito: ele PARECE valido para quem consome, e a
        inconsistencia so aparece quando alguem ja confiou nele.
        """
        if self.status not in TRANSICOES:
            raise EstadoImpossivel(f"status desconhecido: {self.status}")
        if not self.objetivo:
            raise EstadoImpossivel("registro sem objetivo")
        if not self.capacidades:
            raise EstadoImpossivel("registro sem capacidade declarada")
        if self.status == FALHA and not (self.erro or self.motivo_parada):
            raise EstadoImpossivel("FALHA sem descricao")
        if self.terminal and not self.finished_at:
            raise EstadoImpossivel(f"{self.status} sem finished_at")
        if self.status == EXECUTANDO and not self.started_at:
            raise EstadoImpossivel("EXECUTANDO sem started_at")
        if self.updated_at < self.created_at:
            raise EstadoImpossivel("updated_at anterior a created_at")

    def transita(self, novo: str) -> "RegistroDeTarefa":
        if novo == self.status:
            return self
        if novo not in TRANSICOES[self.status]:
            raise TransicaoInvalida(
                f"{self.status} -> {novo} nao e permitido. De {self.status} "
                f"so se vai para {TRANSICOES[self.status] or '(nenhum: terminal)'}.")
        self.status = novo
        return self


class Registro:
    """Tarefas em disco. Uma raiz, um diretorio por tarefa."""

    def __init__(self, raiz: Path | str):
        self.raiz = Path(raiz)
        self._lock = threading.Lock()

    def _arq(self, task_id: str) -> Path:
        return self.raiz / exige_task_id(task_id) / "tarefa.json"

    def grava(self, r: RegistroDeTarefa) -> RegistroDeTarefa:
        """
        Valida contra o estado PERSISTIDO, nao contra o objeto em memoria.

        Consequencia deliberada: cada transicao precisa ser gravada. Pular uma
        gravacao faz um caminho legitimo (RECEBIDA->EXECUTANDO->CONCLUIDA)
        parecer ilegitimo, e falha alto. E o que se quer: o registro em disco
        e a verdade. Se ele nao viu o EXECUTANDO, entao para quem le depois a
        tarefa pulou de recebida para pronta — e isso nao aconteceu.
        """
        with self._lock:
            anterior = self._ver_sem_lock(r.task_id)
            if anterior is not None and anterior.status != r.status:
                if r.status not in TRANSICOES[anterior.status]:
                    raise TransicaoInvalida(
                        f"{r.task_id}: {anterior.status} -> {r.status} "
                        f"nao e permitido")
            r.updated_at = agora()
            r.confere()
            p = self._arq(r.task_id)
            p.parent.mkdir(parents=True, exist_ok=True)
            # ESCRITA ATOMICA. `write_text` nao e atomico, e um leitor
            # concorrente (`por_request_id` varre todos os registros) veria
            # JSON pela metade. Mesma causa-raiz ja corrigida tres vezes nesta
            # base — nao repetir a quarta.
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=2),
                           encoding="utf-8")
            os.replace(tmp, p)
            return r

    def _ver_sem_lock(self, task_id: str) -> RegistroDeTarefa | None:
        try:
            p = self._arq(task_id)
        except TaskIdInvalido:
            # Id hostil e tratado como inexistente: distinguir "invalido" de
            # "nao existe" ja diz a quem tentou que o formato dele passou.
            return None
        if not p.exists():
            return None
        try:
            return RegistroDeTarefa(**json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, TypeError):
            return None

    def ver(self, task_id: str) -> RegistroDeTarefa | None:
        with self._lock:
            return self._ver_sem_lock(task_id)

    def lista(self) -> list[RegistroDeTarefa]:
        if not self.raiz.exists():
            return []
        with self._lock:
            rs = [self._ver_sem_lock(d.name)
                  for d in sorted(self.raiz.iterdir()) if d.is_dir()]
        return [r for r in rs if r is not None]

    def por_request_id(self, rid: str, client_id: str) -> RegistroDeTarefa | None:
        """
        Idempotencia que sobrevive a reinicio.

        Em memoria, um reenvio depois de restart criaria uma segunda tarefa —
        e o mesmo trabalho rodaria duas vezes. O `client_id` entra na busca de
        proposito: dois clientes podem usar o mesmo `request_id` sem colidir,
        e sem que um enxergue a tarefa do outro.
        """
        if not rid:
            return None
        for r in self.lista():
            if r.request_id == rid and r.client_id == client_id:
                return r
        return None


class TaskService:
    """
    Recebe requisicao, guarda, executa fora da requisicao, responde depois.

    `propositor` e injetado como no `Executor` — o servico nao escolhe o que
    propoe as intencoes.
    """

    def __init__(self, raiz: Path | str, politica: Politica,
                 provedores: list[ProvedorDeCapacidade],
                 propositor: Callable[[Tarefa, list[Observacao]], Intencao],
                 teto_nivel: Nivel = Nivel.OBSERVAR,
                 max_simultaneas: int = 4):
        self.registro = Registro(raiz)
        self.politica = politica
        self.provedores = provedores
        self.propositor = propositor
        self.teto_nivel = teto_nivel
        self._pool = ThreadPoolExecutor(max_workers=max_simultaneas,
                                        thread_name_prefix="tarefa")
        self._cancelar: dict[str, bool] = {}
        self._lock = threading.Lock()

    # ── API pedida pelo brief ───────────────────────────────────────────────

    def submete(self, d: dict[str, Any], client_id: str = "default",
                request_id: str | None = None,
                correlation_id: str | None = None) -> RegistroDeTarefa:
        """
        Valida, guarda, e SO ENTAO agenda. Levanta `RequisicaoInvalida` antes
        de criar registro: uma requisicao recusada nao vira tarefa, e nao deve
        deixar rastro consultavel como se tivesse virado.
        """
        if request_id:
            ja = self.registro.por_request_id(request_id, client_id)
            if ja is not None:
                return ja                      # idempotencia

        tarefa = para_tarefa(d, self.teto_nivel)   # pode levantar
        r = RegistroDeTarefa(
            task_id=tarefa.id, client_id=client_id, request_id=request_id,
            correlation_id=correlation_id, objetivo=tarefa.objetivo,
            capacidades=list(tarefa.capacidades), criada_por=tarefa.criada_por)
        self.registro.grava(r)
        self._pool.submit(self._roda, tarefa, r.task_id)
        return r

    def estado(self, task_id: str, client_id: str = "default") -> RegistroDeTarefa | None:
        """
        `client_id` filtra SEMPRE. Sem isso, um cliente com um `task_id` de
        outro leria a tarefa alheia — e `task_id` nao e segredo, e devolvido
        na resposta de quem submeteu.
        """
        r = self.registro.ver(task_id)
        return r if (r is not None and r.client_id == client_id) else None

    def resultado(self, task_id: str, client_id: str = "default") -> RegistroDeTarefa | None:
        """
        Mesmo registro que `estado`. NAO existe um "resultado" separado que
        possa divergir do estado: duas fontes para o mesmo fato acabam
        discordando, e o cliente nao teria como saber qual acreditar.

        Quem chama decide o que fazer com um registro nao-terminal.
        """
        return self.estado(task_id, client_id)

    def cancela(self, task_id: str, client_id: str = "default") -> RegistroDeTarefa | None:
        """
        Cancelar tarefa terminal NAO e erro e NAO muda nada: devolve o
        registro como esta. Um cancelamento que "falha" porque chegou tarde
        faria o cliente tratar corrida normal como problema.
        """
        r = self.estado(task_id, client_id)
        if r is None or r.terminal:
            return r
        with self._lock:
            self._cancelar[task_id] = True
        if r.status == RECEBIDA:
            # Ainda nao comecou: encerra aqui mesmo. Se o pool ja tiver pegado
            # a tarefa entre esta leitura e a gravacao, `_roda` respeita a
            # transicao e nao ha caminho de volta — TRANSICOES garante.
            try:
                r.transita(CANCELADA)
                r.finished_at = agora()
                r.motivo_parada = "cancelada antes de comecar"
                return self.registro.grava(r)
            except TransicaoInvalida:
                return self.estado(task_id, client_id)
        return self.estado(task_id, client_id)

    # ── execucao ────────────────────────────────────────────────────────────

    def _pediram_cancelamento(self, task_id: str) -> bool:
        with self._lock:
            return self._cancelar.get(task_id, False)

    def _propositor_cancelavel(self, task_id: str):
        """
        Embrulha o propositor para observar o pedido de cancelamento ENTRE
        iteracoes. Nao interrompe um provedor no meio: matar execucao pela
        metade deixaria observacao parcial no registro, e observacao parcial e
        exatamente o que `Observacao` frozen existe para impedir.
        """
        def _p(tarefa, obs):
            if self._pediram_cancelamento(task_id):
                raise Cancelada()
            return self.propositor(tarefa, obs)
        return _p

    def _roda(self, tarefa: Tarefa, task_id: str) -> None:
        r = self.registro.ver(task_id)
        if r is None or r.terminal:
            return                       # cancelada antes de comecar
        try:
            r.transita(EXECUTANDO)
            r.started_at = agora()
            self.registro.grava(r)
        except TransicaoInvalida:
            return

        executor = Executor(self.politica, self.provedores)
        t0 = time.perf_counter()
        cancelada = False
        erro = None
        try:
            res = executor.roda(tarefa, self._propositor_cancelavel(task_id))
            obs, negadas = res.observacoes, res.negadas
        except Cancelada:
            cancelada, obs, negadas = True, [], []
        except Exception as e:           # falha do SERVICO, nunca do sistema
            erro, obs, negadas = f"{type(e).__name__}: {e}", [], []
        ms = (time.perf_counter() - t0) * 1000.0

        atual = self.registro.ver(task_id)
        if atual is None or atual.terminal:
            return
        if cancelada:
            atual.transita(CANCELADA)
            atual.motivo_parada = "cancelada durante a execucao"
        elif erro is not None:
            atual.transita(FALHA)
            atual.erro = erro
        else:
            atual.transita(DE_TAREFA.get(tarefa.estado, FALHA))
            atual.motivo_parada = tarefa.motivo_parada
            atual.iteracoes = tarefa.iteracao
            atual.negadas = list(negadas)
            atual.observacoes = [o.to_dict() for o in obs]
        atual.duracao_ms = round(ms, 2)
        atual.finished_at = agora()
        self.registro.grava(atual)

    def encerra(self, espera: bool = True) -> None:
        self._pool.shutdown(wait=espera)
