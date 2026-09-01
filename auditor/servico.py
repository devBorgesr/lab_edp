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
            so_check: bool = False,
            client_id: str = "default") -> dict[str, Any]:
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
    job = reg.ver(aid)
    if job is None:
        job = reg.grava(J.Job(audit_id=aid, client_id=client_id,
                              request_id=entrada.get("request_id"),
                              protocol=entrada["protocol"],
                              adapter=entrada["adapter"]))
    reg.grava(job.transita(J.RUNNING))
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

    job.client_id = client_id
    reg.grava(J.de_resultado(job, {"schema": RESULTADO_VERSAO, **d,
                                   "audit_id": aid, "workspace": str(ws.raiz),
                                   "invalido": any(c.estado is Estado.INVALID
                                                   for c in m.checks)}))
    return {
        "schema":      RESULTADO_VERSAO,
        **d,
        "audit_id":    aid,
        "client_id":   client_id,
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


def verifica_integracao(entrada: dict[str, Any], protocolos: dict,
                       cliente=None) -> dict[str, Any]:
    """
    DRY-RUN DE VERDADE. Responde READY ou BLOCKED sem auditar.

    DEFEITO CORRIGIDO 01/09. O `check` anterior chamava `executa(so_check=True)`,
    que rodava o pipeline INTEIRO e so deixava de gravar os dois relatorios.
    Medido: 1,81 s no check contra 1,74 s no run — o mesmo trabalho. E a
    documentacao entregue ao cliente prometia "responde em segundos, SEM
    PROCESSAR NADA".

    O que esta funcao faz, e so isso:

        valida o schema e os limites
        confere que o snapshot existe e hasheia
        constroi o adaptador
        pede UMA consulta e verifica a procedencia do ranking

    O que ela NAO faz: copiar corpus para workspace, medir, montar estrato,
    gravar manifesto, gravar relatorio, chamar julgador.

    UMA consulta basta para o que o check promete: procedencia e propriedade do
    formato do score, e um retriever que devolve distancia crua na primeira
    query devolve nas outras. O que UMA consulta nao decide e cardinalidade —
    e a resposta diz isso, em vez de deixar o cliente supor que verificou.
    """
    from .checks import procedencia as CP, ranking as CR
    from .cli import carrega_queries
    from .estados import Estado

    entrada = valida_entrada(entrada, protocolos, _adaptadores())
    prot = protocolos[entrada["protocol"]]
    verificado: list[dict[str, Any]] = []

    def reg(r):
        verificado.append({"nome": r.nome, "estado": r.estado.value,
                           "detecta": r.detecta, "motivo": r.motivo,
                           "evidencia": r.evidencia})
        return r

    sistema = constroi_sistema(entrada["adapter"], entrada)
    qs = carrega_queries(Path(entrada["queries"]))
    if cliente is not None:
        from .tenancy import confere_limites
        confere_limites(entrada, cliente, len(qs), 0, 0)

    ok = reg(CP.snapshot_tem_hash(Path(sistema.snapshot_dir))).estado is Estado.PASS
    if ok and qs:
        rk = sistema.consulta(qs[0]["query"], prot.top_k)
        ok = reg(CR.veio_do_retriever(rk)).estado is Estado.PASS

    barreiras = [v["nome"] for v in verificado if v["estado"] != "PASS"]
    return {
        "modo": "check",
        "status": "READY" if not barreiras else "BLOCKED",
        "protocolo": prot.identidade,
        "n_queries": len(qs),
        "verificado": verificado,
        "barreiras": barreiras,
        "NAO_VERIFICADO": [
            "cardinalidade do ranking em todas as queries",
            "estratos e controle negativo",
            "pre-condicoes estatisticas",
        ],
        "nota": ("dry-run: nenhum corpus copiado, nenhuma medicao calculada, "
                 "nenhum relatorio gravado, nenhum julgador executado"),
    }


def status_do_job(resultado: dict[str, Any]) -> str:
    """
    Estado do JOB derivado do estado da AUDITORIA — nunca escrito a mao.

    Se fossem independentes, um job poderia dizer COMPLETE sobre uma auditoria
    BLOCKED, e o cliente leria "terminou bem" onde nao houve metrica.
    """
    return J.INVALID if resultado.get("invalido") else resultado["status"]
