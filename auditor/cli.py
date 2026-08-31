"""
CLI do auditor. HTTP so depois disto estar estavel (item 13).

    python -m auditor check --input ... --protocol ... --queries ...
    python -m auditor run   --input ... --protocol ... --queries ... --output ...

`check` e o dry-run: responde READY ou BLOCKED sem executar julgador nem
calcular metrica de protocolo. Existe para o cliente validar a infraestrutura
ANTES de gastar modelo — e para nos: e o comando que teria barrado o REL-001
antes das 492 chamadas.

EXIT CODES — estaveis, sem ambiguidade:

    0  COMPLETE           executou e ha resultado
    2  BLOCKED            pre-condicao quebrada; ha diagnostico, nao metrica
    3  INVALID            a entrada nao e auditavel
    4  erro operacional   falha inesperada do proprio servico

BLOCKED nao e erro do servico: e o resultado que o servico deve dar. Por isso
tem codigo proprio, e nao 1.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from . import relatorio
from .estados import Estado, StatusAuditoria
from .pipeline import Auditoria, Protocolo
from .esquemas import ENTRADA_VERSAO, EntradaInvalida
from .redacao import Politica

EXIT = {"COMPLETE": 0, "BLOCKED": 2, "INVALID": 3, "ERRO": 4}

PROTOCOLOS = {
    "REL-001": Protocolo(
        "REL-001", 50, {"topo": 5, "cauda": 3, "controle": 2}, (19, 50), 50,
        min_unidades=30, versao=1, tipo="experimental",
        descricao=("regua do experimento REL-001. Exige 50 documentos "
                   "DISTINTOS no ranking porque a cauda sai das posicoes "
                   "20-50. O experimento esta BLOQUEADO: nenhum resultado "
                   "seu foi validado.")),
    "DIAGNOSTICO": Protocolo(
        "DIAGNOSTICO", 1, {}, (0, 0), 50, min_unidades=20, versao=1,
        tipo="demonstrativo", escopo="diagnostico",
        descricao=("Descreve o MATERIAL que o retriever devolve: cardinalidade, "
                   "duplicacao por id e por texto, sobreposicao entre queries e "
                   "distribuicao de score. NAO mede qualidade de resposta, nao "
                   "usa estratos, nao usa controle negativo e nao certifica "
                   "nada. Exige apenas que o ranking tenha procedencia provada.")),
    "BASICO": Protocolo(
        "BASICO", 10, {"topo": 5, "cauda": 3, "controle": 2}, (5, 10), 10,
        min_unidades=10, versao=1, tipo="demonstrativo",
        descricao=("protocolo DEMONSTRATIVO. Serve para exercitar o pipeline "
                   "e produzir demonstracao; NAO sustenta afirmacao cientifica "
                   "e NAO substitui o REL-001. Nenhum resultado sob esta regua "
                   "certifica coisa alguma.")),
}


def carrega_queries(caminho: Path) -> list[dict]:
    """
    Aceita dois formatos: a lista generica do servico e a amostra do REL-001.

    O adaptador nao decide o formato do cliente; o CLI traduz.
    """
    d = json.loads(Path(caminho).read_text("utf-8"))
    qs = d.get("queries", d) if isinstance(d, dict) else d
    out = []
    for i, q in enumerate(qs):
        if isinstance(q, str):
            out.append({"id": f"q{i}", "query": q, "dominio": ""})
        else:
            out.append({
                "id": q.get("id") or (q.get("sha256_query") or f"q{i}")[:12],
                "query": q["query"],
                "dominio": q.get("dominio", ""),
            })
    return out


def _entrada(a) -> dict:
    """Argumentos do CLI -> `AuditInput v1`. Um formato so, duas portas."""
    op = {"mode": a.mode, "exemplos_em_claro": bool(a.exemplos_em_claro)}
    if getattr(a, "dominios", None):
        op["dominios"] = a.dominios
    if getattr(a, "taxa_duplicacao", None) is not None:
        op["taxa_duplicacao"] = a.taxa_duplicacao
    return {"schema": ENTRADA_VERSAO, "snapshot": a.input,
            "queries": a.queries, "protocol": a.protocol,
            "adapter": a.adaptador, "options": op}


def _roda(a, so_check: bool):
    """
    CLI e HTTP entram pelo MESMO `servico.executa`.

    Nenhuma regra de auditoria mora no CLI. Duas implementacoes da mesma regra
    sao duas que divergem, e a divergencia aparece quando o cliente compara o
    que o CLI disse com o que a API disse.
    """
    from .servico import executa
    raiz = Path(getattr(a, "output", None) or ".auditorias")
    return executa(_entrada(a), raiz, PROTOCOLOS, so_check=so_check)


def _codigo(r: dict) -> int:
    if r.get("invalido"):
        return EXIT["INVALID"]
    if r["status"] == StatusAuditoria.BLOCKED.value:
        return EXIT["BLOCKED"]
    # COMPLETE e READY nao tem problema bloqueante. READY significa "auditavel,
    # sem metrica de protocolo configurada" — e o caso comercial do MVP-1:
    # medicoes entregues, Recall@K nao autorizado ainda.
    return EXIT["COMPLETE"]


def _imprime(r: dict) -> None:
    print(f"\nprotocolo .... {r['protocolo_identidade']} "
          f"({r['protocolo_spec']['tipo']})")
    print(f"status ....... {r['status']}")
    for nome in r["barreiras"]:
        c = next(x for x in r["checks"] if x["nome"] == nome)
        print(f"  BARRA  {nome}\n         {c['motivo']}")
    for d in r["medicoes"]:
        print(f"  medido {d['nome']:<32} {round(d['valor'], 4)} "
              f"{d['unidade']} (N={d['N']})")


def cmd_check(a) -> int:
    """Dry-run: READY ou BLOCKED, sem julgador e sem metrica de protocolo."""
    r = _roda(a, so_check=True)
    _imprime(r)
    pronto = not r["barreiras"]
    print("\n" + ("READY — a infraestrutura sustenta este protocolo"
                  if pronto else "BLOCKED — ver motivos acima"))
    print("(dry-run: nenhum julgador executado, nenhuma metrica de protocolo "
          "calculada, nenhum relatorio gravado)")
    return _codigo(r)


def cmd_run(a) -> int:
    r = _roda(a, so_check=False)
    _imprime(r)
    w = Path(r["workspace"])
    print(f"\n{w/'reports'/'executive.md'}\n{w/'reports'/'technical.md'}"
          f"\n{w/'manifest.json'}")
    return _codigo(r)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser("audit", description="servico de auditoria (MVP-1)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comum(p, com_output: bool):
        p.add_argument("--input",    required=True, help="snapshot do sistema")
        p.add_argument("--protocol", required=True, choices=sorted(PROTOCOLOS))
        p.add_argument("--queries",  required=True)
        p.add_argument("--adaptador", default="edp",
                       choices=["edp", "sintetico"])
        p.add_argument("--taxa-duplicacao", type=float, default=None,
                       dest="taxa_duplicacao",
                       help="so para o adaptador sintetico (demonstracao)")
        p.add_argument("--dominios", default=None)
        p.add_argument("--mode", default="AUDIT", choices=["AUDIT", "DIAGNOSTIC"])
        p.add_argument("--exemplos-em-claro", action="store_true",
                       dest="exemplos_em_claro",
                       help="mostra texto do cliente nos artefatos (segredo "
                            "continua removido). Default: so hash.")
        p.add_argument("--output", default=".auditorias",
                       help="raiz do servico; cada auditoria ganha "
                            "<raiz>/<audit_id>/ proprio")

    comum(sub.add_parser("check", help="dry-run: READY ou BLOCKED"), False)
    comum(sub.add_parser("run", help="auditoria completa"), True)
    a = ap.parse_args(argv)

    try:
        return cmd_check(a) if a.cmd == "check" else cmd_run(a)
    except EntradaInvalida as e:
        print(f"\nENTRADA INVALIDA ({ENTRADA_VERSAO}): {e}", file=sys.stderr)
        return EXIT["INVALID"]
    except Exception:
        traceback.print_exc()
        print("\nERRO OPERACIONAL do servico — nao e veredito sobre o sistema "
              "auditado. Nenhuma conclusao deve ser tirada desta execucao.",
              file=sys.stderr)
        return EXIT["ERRO"]


if __name__ == "__main__":
    sys.exit(main())
