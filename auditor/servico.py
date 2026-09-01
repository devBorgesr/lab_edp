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
from .esquemas import RESULTADO_VERSAO, valida_entrada
from .estados import Estado, StatusAuditoria
from .pipeline import Auditoria
from .redacao import Politica, varre_segredos
from .workspace import Workspace

# Estados do JOB. Coincidem com os da auditoria por construcao (item 11): um
# job COMPLETE nao pode existir sobre uma auditoria BLOCKED.
QUEUED, RUNNING = "QUEUED", "RUNNING"


def _adaptadores() -> dict[str, Any]:
    return {"edp": "auditor.adaptadores.edp:EDPAuditavel",
            "sintetico": "auditor.fixtures:ClienteSintetico"}


def constroi_sistema(nome: str, entrada: dict) -> Any:
    op = entrada.get("options") or {}
    if nome == "edp":
        from .adaptadores.edp import EDPAuditavel
        return EDPAuditavel(Path(entrada["snapshot"]),
                            Path(op["dominios"]) if op.get("dominios") else None)
    if nome == "sintetico":
        from .fixtures import ClienteSintetico
        return ClienteSintetico(Path(entrada["snapshot"]),
                                taxa_duplicacao=float(op.get("taxa_duplicacao", 0.0)))
    raise ValueError(f"adaptador desconhecido: {nome}")


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
    if resultado.get("invalido"):
        return StatusAuditoria.BLOCKED.value if False else "INVALID"
    return resultado["status"]
