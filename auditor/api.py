"""
API HTTP. Orquestra o engine e NAO reimplementa nenhuma regra de auditoria.

    POST /v1/audits            cria (assincrona)  -> audit_id, QUEUED
    GET  /v1/audits            lista
    GET  /v1/audits/{id}       AuditResult v1
    GET  /v1/audits/{id}/status
    GET  /v1/audits/{id}/report?tipo=executive|technical
    GET  /v1/audits/{id}/manifest

Toda a logica vive em `auditor.servico.executa`. Se um handler daqui comecar a
decidir alguma coisa sobre auditoria, o servico passa a ter duas
implementacoes — e a divergencia aparece quando o cliente compara o que o CLI
disse com o que a API disse.

`fastapi` e importado SO aqui: o nucleo do auditor continua rodando sem ele.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .esquemas import EntradaInvalida
from .servico import QUEUED, RUNNING, executa, status_do_job


class Jobs:
    """
    Registro em memoria. Um job NAO depende da conexao HTTP ficar aberta.

    IDEMPOTENCIA (item 12): `request_id` mapeia para o audit_id ja criado. Um
    retry de rede nao pode virar duas auditorias — o cliente pagaria duas vezes
    e receberia dois manifestos diferentes do mesmo sistema.
    """

    def __init__(self, raiz: Path, protocolos: dict):
        self.raiz = Path(raiz)
        self.protocolos = protocolos
        self._jobs: dict[str, dict[str, Any]] = {}
        self._por_request: dict[str, str] = {}
        self._lock = threading.Lock()

    def cria(self, entrada: dict[str, Any]) -> dict[str, Any]:
        rid = entrada.get("request_id")
        with self._lock:
            if rid and rid in self._por_request:
                aid = self._por_request[rid]
                return {**self._jobs[aid], "idempotente": True}
            aid = uuid.uuid4().hex[:12]
            job = {"audit_id": aid, "status": QUEUED, "request_id": rid,
                   "criado_em": datetime.now(timezone.utc).isoformat(
                       timespec="seconds"), "erro": None}
            self._jobs[aid] = job
            if rid:
                self._por_request[rid] = aid
        threading.Thread(target=self._roda, args=(aid, entrada),
                         daemon=True).start()
        return job

    def _roda(self, aid: str, entrada: dict[str, Any]) -> None:
        with self._lock:
            self._jobs[aid]["status"] = RUNNING
        try:
            r = executa(entrada, self.raiz, self.protocolos, audit_id=aid)
            with self._lock:
                self._jobs[aid].update(status=status_do_job(r), resultado=r)
        except EntradaInvalida as e:
            with self._lock:
                self._jobs[aid].update(status="INVALID", erro=str(e))
        except Exception as e:
            # ERROR e falha do SERVICO. Nunca vira veredito sobre o sistema
            # auditado — o cliente precisa saber que nada foi medido.
            with self._lock:
                self._jobs[aid].update(status="ERROR", erro=f"{type(e).__name__}: {e}")

    def ver(self, aid: str) -> dict[str, Any] | None:
        with self._lock:
            return self._jobs.get(aid)

    def lista(self) -> list[dict[str, Any]]:
        with self._lock:
            return [{k: v for k, v in j.items() if k != "resultado"}
                    for j in self._jobs.values()]


def cria_app(raiz: Path, protocolos: dict):
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import PlainTextResponse

    app = FastAPI(title="Auditoria de retrieval", version="0.3.0")
    jobs = Jobs(raiz, protocolos)

    def _job(aid: str) -> dict[str, Any]:
        j = jobs.ver(aid)
        if not j:
            raise HTTPException(404, f"auditoria {aid} nao encontrada")
        return j

    def _pronto(aid: str) -> dict[str, Any]:
        j = _job(aid)
        if j["status"] in (QUEUED, RUNNING):
            raise HTTPException(409, f"auditoria {aid} esta {j['status']}")
        if not j.get("resultado"):
            raise HTTPException(422, j.get("erro") or "sem resultado")
        return j["resultado"]

    @app.post("/v1/audits", status_code=202)
    def cria(entrada: dict):
        return jobs.cria(entrada)

    @app.get("/v1/audits")
    def lista():
        return {"audits": jobs.lista()}

    @app.get("/v1/audits/{aid}")
    def ver(aid: str):
        return _pronto(aid)

    @app.get("/v1/audits/{aid}/status")
    def status(aid: str):
        j = _job(aid)
        return {"audit_id": aid, "status": j["status"], "erro": j.get("erro")}

    @app.get("/v1/audits/{aid}/manifest")
    def manifesto(aid: str):
        return _pronto(aid)

    @app.get("/v1/audits/{aid}/report", response_class=PlainTextResponse)
    def report(aid: str, tipo: str = Query("executive",
                                           pattern="^(executive|technical)$")):
        r = _pronto(aid)
        p = Path(r["workspace"]) / "reports" / f"{tipo}.md"
        if not p.exists():
            raise HTTPException(404, f"relatorio {tipo} nao gerado")
        return p.read_text(encoding="utf-8")

    return app


def main(argv=None) -> int:
    import argparse
    from .cli import PROTOCOLOS
    ap = argparse.ArgumentParser("auditor.api")
    ap.add_argument("--raiz", default="./auditorias_servico")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args(argv)
    import uvicorn
    uvicorn.run(cria_app(Path(a.raiz), PROTOCOLOS), host=a.host, port=a.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
