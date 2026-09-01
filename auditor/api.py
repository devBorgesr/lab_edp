"""
API HTTP. TRANSPORTA o engine; nao decide nada sobre auditoria.

    POST /v1/audits                    cria (assincrona) -> audit_id, QUEUED
    GET  /v1/audits                    lista as do cliente autenticado
    GET  /v1/audits/{id}               AuditResult v1 (le do disco)
    GET  /v1/audits/{id}/status        estado e metadados
    GET  /v1/audits/{id}/report        relatorio ja gerado
    GET  /v1/audits/{id}/manifest      manifesto original
    GET  /v1/protocols                 reguas disponiveis
    GET  /v1/protocols/{nome}
    GET  /health   /ready

NENHUM `GET` executa auditoria. Todos leem artefato ja produzido: um `GET` que
recalcula devolve, para a mesma URL, um numero diferente do que o cliente
recebeu — e o hash do manifesto deixa de significar coisa alguma.

ISOLAMENTO POR CAMINHO, nao por checagem: o `client_id` autenticado entra na
raiz (`data/<client_id>/<audit_id>/`), entao um id de outro cliente
simplesmente nao existe onde o handler procura. Nao depende de o handler
lembrar de comparar.

`fastapi` so e importado aqui — o nucleo roda sem ele.
"""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from . import jobs as J
from .esquemas import ENTRADA_VERSAO, EntradaInvalida, valida_entrada
from .fila import Fila, trabalha_uma
from .registro import conhecidos
from .tenancy import (Clientes, LimiteExcedido, NaoAutorizado, linha_de_log,
                      raiz_do_cliente)


def _conta_entrada(entrada: dict) -> tuple[int, int, int]:
    """Tamanhos declarados, para os limites. Nao le documento nenhum."""
    q = Path(entrada["queries"])
    n_q = 0
    if q.exists():
        d = json.loads(q.read_text(encoding="utf-8"))
        n_q = len(d.get("queries", d) if isinstance(d, dict) else d)
    snap = Path(entrada["snapshot"])
    n_bytes = sum(p.stat().st_size for p in snap.rglob("*") if p.is_file()) \
        if snap.exists() else 0
    corpus = snap / "corpus.json"
    n_docs = len(json.loads(corpus.read_text(encoding="utf-8"))) \
        if corpus.exists() else 0
    return n_q, n_docs, n_bytes


def cria_app(base: Path, protocolos: dict, arquivo_clientes: Path | None = None,
             worker_em_thread: bool = True):
    """
    `protocolos` e filtrado por `exposto`: uma regua pode existir no
    laboratorio e nao ser oferecida pelo servico. O REL-001 esta bloqueado, e
    aceita-lo por HTTP deixaria um cliente rodar um experimento cujo resultado
    nao foi validado — e receber um relatorio que parece produto.
    """
    from .cli import publicos
    protocolos = publicos(protocolos)
    from fastapi import Depends, FastAPI, Header, HTTPException, Query
    from fastapi.responses import PlainTextResponse

    from . import __version__

    base = Path(base)
    clientes = Clientes(arquivo_clientes or base / "clientes.json")
    app = FastAPI(title="Diagnostico de Retrieval", version=__version__)
    app.state.log: list[dict[str, Any]] = []

    def autentica(x_api_key: str | None = Header(default=None,
                                                 alias="X-API-Key")):
        try:
            return clientes.autentica(x_api_key)
        except NaoAutorizado as e:
            # 401 identico para chave ausente e invalida
            raise HTTPException(401, str(e))

    def _raiz(cli) -> Path:
        return raiz_do_cliente(base / "data", cli.client_id)

    def _job(cli, aid: str) -> J.Job:
        job = J.Registro(_raiz(cli)).ver(aid)
        if job is None:
            # 404 tambem quando existe para OUTRO cliente: dizer "existe mas
            # nao e sua" ja entrega a existencia do id.
            raise HTTPException(404, f"auditoria {aid} nao encontrada")
        return job

    def _terminal(job: J.Job) -> J.Job:
        if job.status in (J.QUEUED, J.RUNNING):
            raise HTTPException(409, f"auditoria {job.audit_id} esta {job.status}")
        return job

    # ── criacao ─────────────────────────────────────────────────────────────

    @app.post("/v1/audits", status_code=202)
    def cria(entrada: dict, cli=Depends(autentica)):
        raiz = _raiz(cli)
        reg, fila = J.Registro(raiz), Fila(raiz)

        rid = entrada.get("request_id")
        if rid:
            ja = reg.por_request_id(rid)
            if ja is not None:
                return {"audit_id": ja.audit_id, "status": ja.status,
                        "idempotente": True}
        try:
            entrada = valida_entrada(entrada, protocolos, conhecidos())
            from .tenancy import confere_limites
            confere_limites(entrada, cli, *_conta_entrada(entrada))
        except (EntradaInvalida, LimiteExcedido) as e:
            # INVALID, nao ERROR: a entrada e que nao serve.
            aid = uuid.uuid4().hex[:12]
            reg.grava(J.Job(aid, client_id=cli.client_id, request_id=rid,
                            service_version=__version__))
            job = reg.ver(aid)
            job.erro = str(e)
            reg.grava(job.transita(J.INVALID))
            app.state.log.append(linha_de_log(audit_id=aid,
                                              client_id=cli.client_id,
                                              status=J.INVALID,
                                              erro_tecnico=type(e).__name__))
            raise HTTPException(422, {"audit_id": aid, "status": J.INVALID,
                                      "erro": str(e)})

        aid = uuid.uuid4().hex[:12]
        reg.grava(J.Job(aid, client_id=cli.client_id, request_id=rid,
                        protocol=entrada["protocol"], adapter=entrada["adapter"],
                        service_version=__version__))
        fila.enfileira(aid, {"raiz": str(raiz), "client_id": cli.client_id,
                             "entrada": entrada})
        app.state.log.append(linha_de_log(audit_id=aid, client_id=cli.client_id,
                                          status=J.QUEUED))
        if worker_em_thread:
            threading.Thread(target=trabalha_uma, args=(raiz, protocolos),
                             daemon=True).start()
        return {"audit_id": aid, "status": J.QUEUED}

    # ── leitura: nenhuma destas executa auditoria ───────────────────────────

    @app.get("/v1/audits")
    def lista(cli=Depends(autentica)):
        return {"audits": [{"audit_id": j.audit_id, "status": j.status,
                            "protocol": j.protocol, "created_at": j.created_at}
                           for j in J.Registro(_raiz(cli)).lista()]}

    @app.get("/v1/audits/{aid}/status")
    def status(aid: str, cli=Depends(autentica)):
        j = _job(cli, aid)
        return {"audit_id": j.audit_id, "status": j.status,
                "protocol": f"{j.protocol} v{j.protocol_version or '?'}",
                "adapter": j.adapter, "service_version": j.service_version,
                "created_at": j.created_at, "updated_at": j.updated_at,
                "erro": j.erro}

    @app.get("/v1/audits/{aid}/manifest")
    def manifesto(aid: str, cli=Depends(autentica)):
        j = _terminal(_job(cli, aid))
        p = Path(j.manifest) if j.manifest else None
        if not p or not p.exists():
            raise HTTPException(404, f"manifesto nao existe (status {j.status})")
        # devolve o ORIGINAL; reconstruir invalidaria o sha256 gravado
        return json.loads(p.read_text(encoding="utf-8"))

    @app.get("/v1/audits/{aid}")
    def ver(aid: str, cli=Depends(autentica)):
        return manifesto(aid, cli)

    @app.get("/v1/audits/{aid}/report", response_class=PlainTextResponse)
    def report(aid: str, cli=Depends(autentica),
               tipo: str = Query("executive", pattern="^(executive|technical)$")):
        j = _terminal(_job(cli, aid))
        cam = j.reports.get(tipo)
        if not cam or not Path(cam).exists():
            raise HTTPException(404, f"relatorio `{tipo}` nao existe "
                                     f"(status {j.status})")
        return Path(cam).read_text(encoding="utf-8")

    # ── reguas ──────────────────────────────────────────────────────────────

    @app.get("/v1/protocols")
    def protocolos_():
        return {"protocols": [p.to_dict() for p in protocolos.values()]}

    @app.get("/v1/protocols/{nome}")
    def protocolo_(nome: str):
        if nome not in protocolos:
            raise HTTPException(404, f"protocolo {nome} desconhecido")
        return protocolos[nome].to_dict()

    # ── saude ───────────────────────────────────────────────────────────────

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "auditor", "version": __version__}

    @app.get("/ready")
    def ready():
        """Dependencias disponiveis. NAO executa auditoria."""
        checks: dict[str, Any] = {}
        try:
            d = base / "data"; d.mkdir(parents=True, exist_ok=True)
            t = d / ".escrita"; t.write_text("x"); t.unlink()
            checks["workspace_gravavel"] = True
        except Exception as e:
            checks["workspace_gravavel"] = False
            checks["erro"] = type(e).__name__
        checks["registro_de_clientes"] = clientes.arquivo.exists()
        checks["protocolos"] = sorted(protocolos)
        checks["adaptadores"] = sorted(conhecidos())
        pronto = checks["workspace_gravavel"]
        if not pronto:
            raise HTTPException(503, checks)
        return {"ready": True, **checks}

    return app


def main(argv=None) -> int:
    import argparse
    from .cli import PROTOCOLOS
    ap = argparse.ArgumentParser("auditor.api")
    ap.add_argument("--base", default="./dados_servico")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args(argv)
    import uvicorn
    uvicorn.run(cria_app(Path(a.base), PROTOCOLOS), host=a.host, port=a.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
