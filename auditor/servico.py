"""
Ponto de entrada UNICO do servico. CLI e HTTP chamam daqui.

    AuditInput v1 -> valida -> workspace isolado -> engine -> redacao
                  -> manifesto + relatorios -> AuditResult v1

Nenhuma regra de auditoria vive no CLI nem no handler HTTP. Duas
implementacoes da mesma regra sao duas que divergem, e a divergencia aparece
no pior momento possivel: quando um cliente compara o que o CLI disse com o
que a API disse.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from . import claims, relatorio
from . import jobs as J
from .esquemas import RESULTADO_VERSAO, valida_entrada
from .estados import Estado, StatusAuditoria
from .pipeline import Auditoria
from .redacao import Politica, varre_segredos
from .registro import conhecidos, constroi
from .workspace import Workspace

# Estados do JOB. Coincidem com os da auditoria por construcao (item 11): um
# job COMPLETE nao pode existir sobre uma auditoria BLOCKED.
QUEUED, RUNNING = "QUEUED", "RUNNING"


def _adaptadores() -> dict[str, Any]:
    """Um lugar so onde se descobre o que existe — ver `auditor.registro`."""
    return conhecidos()


def constroi_sistema(nome: str, entrada: dict) -> Any:
    return constroi(nome, entrada)


def executa(entrada: dict[str, Any], raiz_servico: Path,
            protocolos: dict, audit_id: str | None = None,
            so_check: bool = False) -> dict[str, Any]:
    """
    Uma auditoria, do schema ao AuditResult. Isolada em workspace proprio.

    `so_check=True` e o dry-run: as mesmas verificacoes, sem julgador e sem
    metrica de protocolo, e sem gravar relatorio.
    """
    t0 = time.perf_counter()
    entrada = valida_entrada(entrada, protocolos, _adaptadores())
    aid = audit_id or uuid.uuid4().hex[:12]
    ws = Workspace.cria(Path(raiz_servico), aid)

    from .cli import carrega_queries
    pol = Politica(exemplos_em_claro=bool(
        (entrada.get("options") or {}).get("exemplos_em_claro", False)))

    aud = Auditoria(protocolos[entrada["protocol"]],
                    constroi_sistema(entrada["adapter"], entrada),
                    carrega_queries(Path(entrada["queries"])),
                    modo=(entrada.get("options") or {}).get("mode", "AUDIT"),
                    politica=pol, audit_id=aid)
    aud.origem_do_dataset = Path(entrada["queries"]).name

    # O job nasce ANTES da execucao. Se o processo morrer no meio, fica o
    # registro de que a auditoria comecou — um servico que esquece o que
    # executou nao e auditavel.
    reg = J.Registro(Path(raiz_servico))
    job = reg.grava(J.Job(audit_id=aid, status=J.RUNNING,
                          request_id=entrada.get("request_id"),
                          protocol=entrada["protocol"],
                          adapter=entrada["adapter"]))
    m = aud.roda()

    ws.grava_json("input", "audit_input.json",
                  {**entrada, "recebido_como": entrada["schema"]})
    d = m.salva(ws.raiz / "manifest.json", politica=pol)
    ws.grava_json("artifacts", "checks.json",
                  [{"nome": c.nome, "estado": c.estado.value,
                    "detecta": c.detecta, "evidencia": c.evidencia}
                   for c in m.checks])

    if not so_check:
        escopo = (m.protocolo_spec or {}).get("escopo", "protocolo")
        for nome, txt in (("executive.md", relatorio.executivo(m)),
                          ("technical.md", relatorio.markdown(m))):
            restou = varre_segredos(txt)
            if restou:
                raise RuntimeError(f"segredo no relatorio {nome}: {restou}")
            # BARREIRA DE CLAIM, no mesmo ponto da redacao e pelo mesmo motivo:
            # e o ultimo lugar antes de o texto virar entregavel. Verifica o
            # TEXTO GERADO, nao o codigo-fonte — foi assim que duas violacoes
            # minhas passaram por revisao e por 283 testes.
            claims.exige_limpo(txt, escopo, f"relatorio {nome}")
            ws.grava("reports", nome, txt)

    reg.grava(J.de_resultado(job, {"schema": RESULTADO_VERSAO, **d,
                                   "audit_id": aid, "workspace": str(ws.raiz),
                                   "invalido": any(c.estado is Estado.INVALID
                                                   for c in m.checks)}))
    return {
        "schema":      RESULTADO_VERSAO,
        **d,
        "audit_id":    aid,
        "workspace":   str(ws.raiz),
        "retencao":    ws.politica_de_retencao(),
        "invalido":    any(c.estado is Estado.INVALID for c in m.checks),
        "observabilidade": {
            "tempo_servico_s": round(time.perf_counter() - t0, 3),
            "tempo_engine":    d.get("custos", {}).get("tempo_por_etapa_s", {}),
            "nota": ("log operacional; NAO e resultado da auditoria e nao deve "
                     "ser lido como medicao do sistema do cliente"),
        },
    }


def status_do_job(resultado: dict[str, Any]) -> str:
    """
    Estado do JOB derivado do estado da AUDITORIA — nunca escrito a mao.

    Se fossem independentes, um job poderia dizer COMPLETE sobre uma auditoria
    BLOCKED, e o cliente leria "terminou bem" onde nao houve metrica.
    """
    return J.INVALID if resultado.get("invalido") else resultado["status"]
