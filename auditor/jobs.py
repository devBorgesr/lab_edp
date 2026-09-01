"""
O job de auditoria, PERSISTIDO. CLI e HTTP leem o mesmo registro.

Antes disto o job vivia num dicionario em memoria dentro do `api.py`, o que
tinha duas consequencias ruins: o CLI nao conseguia responder `status` nem
`report` (o processo ja tinha morrido), e o HTTP perdia tudo ao reiniciar. Um
servico que esquece o que executou nao e auditavel.

O registro fica em `<raiz>/<audit_id>/job.json`, ao lado do manifesto — mesma
raiz isolada, mesma retencao.

ESTADOS

    QUEUED    criado, ainda nao comecou
    RUNNING   executando
    COMPLETE  terminou; ha resultado da regua
    BLOCKED   a regua nao pode ser executada sobre este sistema
    INVALID   a entrada nao e auditavel
    ERROR     falha do SERVICO — nunca um veredito sobre o sistema auditado

Os quatro terminais derivam do estado da AUDITORIA, nunca sao escritos a mao:
um job nao pode dizer COMPLETE sobre auditoria BLOCKED.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEUED, RUNNING = "QUEUED", "RUNNING"
COMPLETE, BLOCKED, INVALID, ERROR = "COMPLETE", "BLOCKED", "INVALID", "ERROR"
# READY: as pre-condicoes passaram e a regua nao tinha metrica de protocolo
# configurada. E terminal e legitimo — o `DIAGNOSTICO v1` chega a COMPLETE
# porque suas medicoes SAO o resultado, mas uma regua sem resultado definido
# para em READY. Faltava aqui, e a auditoria que terminava assim derrubava o
# job com TransicaoInvalida.
READY = "READY"
TERMINAIS = (COMPLETE, READY, BLOCKED, INVALID, ERROR)

# Transicoes permitidas. Terminal nao volta.
#
# Sem isto, um retry mal escrito poderia levar BLOCKED de volta a RUNNING e
# depois a COMPLETE — e o cliente veria "terminou bem" numa auditoria que nunca
# produziu metrica. O caminho de um estado terminal para outro nao existe.
TRANSICOES: dict[str, tuple[str, ...]] = {
    QUEUED:   (RUNNING, INVALID, ERROR),
    RUNNING:  (COMPLETE, READY, BLOCKED, INVALID, ERROR),
    COMPLETE: (),
    READY:    (),
    BLOCKED:  (),
    INVALID:  (),
    ERROR:    (),
}


class TransicaoInvalida(RuntimeError):
    """Mudanca de estado que o servico nao admite."""


class EstadoImpossivel(RuntimeError):
    """Job internamente inconsistente — nao pode ser gravado."""


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    audit_id:         str
    status:           str = QUEUED
    client_id:        str = "default"
    service_version:  str = ""
    created_at:       str = field(default_factory=agora)
    updated_at:       str = field(default_factory=agora)
    protocol:         str = ""
    protocol_version: int | None = None
    adapter:          str = ""      # nome registrado, o que o cliente pediu
    adapter_class:    str = ""      # classe que implementa
    adapter_version:  str = ""
    snapshot:         dict[str, Any] = field(default_factory=dict)
    dataset:          dict[str, Any] = field(default_factory=dict)
    manifest:         str = ""
    reports:          dict[str, str] = field(default_factory=dict)
    request_id:       str | None = None
    erro:             str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def confere(self) -> None:
        """
        Estado impossivel nao chega ao disco.

        Um job COMPLETE sem manifesto, ou BLOCKED com relatorio de resultado,
        e pior que um job com erro: ele PARECE valido para quem consome o
        registro, e a inconsistencia so aparece quando alguem confia nele.
        """
        if self.status not in TRANSICOES:
            raise EstadoImpossivel(f"status desconhecido: {self.status}")
        if self.status == COMPLETE and not self.manifest:
            raise EstadoImpossivel("COMPLETE sem manifesto")
        if self.status in (COMPLETE, READY, BLOCKED) and not self.protocol:
            raise EstadoImpossivel(f"{self.status} sem protocolo identificado")
        if self.status == INVALID and not self.erro and not self.manifest:
            raise EstadoImpossivel("INVALID sem motivo nem manifesto")
        if self.status == ERROR and not self.erro:
            raise EstadoImpossivel("ERROR sem descricao do erro")
        if not self.updated_at or not self.created_at:
            raise EstadoImpossivel("job sem carimbo de tempo")
        if self.updated_at < self.created_at:
            raise EstadoImpossivel("updated_at anterior a created_at")

    def transita(self, novo: str) -> "Job":
        if novo == self.status:
            return self
        if novo not in TRANSICOES[self.status]:
            raise TransicaoInvalida(
                f"{self.status} -> {novo} nao e permitido. "
                f"De {self.status} so se vai para {TRANSICOES[self.status] or '(nenhum: terminal)'}."
            )
        self.status = novo
        return self


class Registro:
    """Jobs em disco. Uma raiz de servico, um diretorio por auditoria."""

    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)

    def _arq(self, audit_id: str) -> Path:
        # O audit_id COMPOE O CAMINHO. Sem validacao, `../outro/id` lia o job
        # de outro cliente — ver `tenancy.exige_audit_id`.
        from .tenancy import exige_audit_id
        return self.raiz / exige_audit_id(audit_id) / "job.json"

    def grava(self, job: Job) -> Job:
        """
        Valida contra o estado PERSISTIDO, nao contra o objeto em memoria.

        Consequencia deliberada: cada transicao precisa ser gravada. Pular uma
        gravacao faz um caminho legitimo (QUEUED->RUNNING->COMPLETE) parecer
        ilegitimo (QUEUED->COMPLETE), e falha alto.

        E o que se quer: o registro em disco e a verdade auditavel. Se ele nao
        viu o RUNNING, entao do ponto de vista de quem le o registro depois a
        auditoria pulou de enfileirada para pronta, e isso nao aconteceu.
        """
        anterior = self.ver(job.audit_id)
        if anterior is not None and anterior.status != job.status:
            if job.status not in TRANSICOES[anterior.status]:
                raise TransicaoInvalida(
                    f"{job.audit_id}: {anterior.status} -> {job.status} "
                    f"nao e permitido"
                )
        job.updated_at = agora()
        job.confere()
        p = self._arq(job.audit_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        # ESCRITA ATOMICA. Terceira ocorrencia da mesma causa-raiz nesta base:
        # a fila e o adaptador de referencia ja tinham sido corrigidos, e este
        # ficou. `write_text` nao e atomico — um leitor concorrente
        # (`por_request_id` varre todos os jobs) via JSON pela metade e
        # levantava JSONDecodeError, que aparecia como suite instavel.
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, p)          # o arquivo so aparece completo
        return job

    def ver(self, audit_id: str) -> Job | None:
        from .tenancy import NaoAutorizado
        try:
            p = self._arq(audit_id)
        except NaoAutorizado:
            # id hostil e tratado como inexistente: distinguir "invalido" de
            # "nao existe" ja diz ao atacante que o formato dele passou.
            return None
        if not p.exists():
            return None
        return Job(**json.loads(p.read_text(encoding="utf-8")))

    def _le_silencioso(self, audit_id: str) -> Job | None:
        """
        Para varreduras (`lista`, `por_request_id`), onde um job ilegivel nao
        pode derrubar a consulta inteira. Com a escrita atomica isto nao
        deveria acontecer; se acontecer, o certo e ignorar aquele registro e
        nao devolver erro sobre os outros.
        """
        try:
            return self.ver(audit_id)
        except (json.JSONDecodeError, TypeError):
            return None

    def lista(self) -> list[Job]:
        if not self.raiz.exists():
            return []
        js = [self._le_silencioso(d.name)
              for d in sorted(self.raiz.iterdir()) if d.is_dir()]
        return [j for j in js if j is not None]

    def por_request_id(self, rid: str) -> Job | None:
        """
        Idempotencia que sobrevive a reinicio.

        Em memoria, um retry depois de restart criaria uma segunda auditoria —
        e o cliente pagaria duas vezes por dois manifestos do mesmo sistema.
        """
        if not rid:
            return None
        for j in self.lista():
            if j.request_id == rid:
                return j
        return None


J_INVALID = INVALID


def de_resultado(job: Job, r: dict[str, Any]) -> Job:
    """
    Preenche o job a partir do AuditResult. O `status` DERIVA do resultado.

    Escrever o status a mao permitiria um job COMPLETE sobre auditoria
    BLOCKED, e o cliente leria "terminou bem" onde nao houve metrica.
    """
    spec = r.get("protocolo_spec") or {}
    job.transita(J_INVALID if r.get("invalido") else r["status"])
    job.service_version  = r.get("versao_servico", "")
    job.protocol         = spec.get("nome", r.get("protocolo", ""))
    job.protocol_version = spec.get("versao")
    # NAO sobrescreve `adapter`: ele guarda o nome REGISTRADO ("cliente",
    # "edp"), que e o que o cliente pediu. A classe que implementa vai em
    # `adapter_class` — as duas coisas sao diferentes e a primeira versao disto
    # trocava uma pela outra, gravando "AdaptadorDeReferencia" onde deveria
    # estar o adaptador escolhido.
    job.adapter          = job.adapter or (r.get("retriever") or {}).get("adaptador", "")
    job.adapter_class    = (r.get("retriever") or {}).get("adaptador", "")
    job.adapter_version  = (r.get("retriever") or {}).get("versao_adaptador", "")
    job.snapshot         = r.get("snapshot") or {}
    job.dataset          = r.get("dataset") or {}
    ws = Path(r.get("workspace", ""))
    job.manifest = str(ws / "manifest.json")
    job.reports = {t: str(ws / "reports" / f"{t}.md")
                   for t in ("executive", "technical")
                   if (ws / "reports" / f"{t}.md").exists()}
    return job
