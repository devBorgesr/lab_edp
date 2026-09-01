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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEUED, RUNNING = "QUEUED", "RUNNING"
COMPLETE, BLOCKED, INVALID, ERROR = "COMPLETE", "BLOCKED", "INVALID", "ERROR"
TERMINAIS = (COMPLETE, BLOCKED, INVALID, ERROR)


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    audit_id:         str
    status:           str = QUEUED
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


class Registro:
    """Jobs em disco. Uma raiz de servico, um diretorio por auditoria."""

    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)

    def _arq(self, audit_id: str) -> Path:
        return self.raiz / audit_id / "job.json"

    def grava(self, job: Job) -> Job:
        job.updated_at = agora()
        p = self._arq(job.audit_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2),
                     encoding="utf-8")
        return job

    def ver(self, audit_id: str) -> Job | None:
        p = self._arq(audit_id)
        if not p.exists():
            return None
        return Job(**json.loads(p.read_text(encoding="utf-8")))

    def lista(self) -> list[Job]:
        if not self.raiz.exists():
            return []
        js = [self.ver(d.name) for d in sorted(self.raiz.iterdir()) if d.is_dir()]
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


def de_resultado(job: Job, r: dict[str, Any]) -> Job:
    """
    Preenche o job a partir do AuditResult. O `status` DERIVA do resultado.

    Escrever o status a mao permitiria um job COMPLETE sobre auditoria
    BLOCKED, e o cliente leria "terminou bem" onde nao houve metrica.
    """
    spec = r.get("protocolo_spec") or {}
    job.status           = INVALID if r.get("invalido") else r["status"]
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
