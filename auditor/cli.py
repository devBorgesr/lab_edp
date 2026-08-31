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


def _sistema(a):
    if a.adaptador == "edp":
        from .adaptadores.edp import EDPAuditavel
        return EDPAuditavel(Path(a.input),
                            Path(a.dominios) if a.dominios else None)
    raise SystemExit(f"adaptador desconhecido: {a.adaptador}")


def _roda(a):
    prot = PROTOCOLOS[a.protocol]
    pol = Politica(exemplos_em_claro=getattr(a, "exemplos_em_claro", False))
    aud = Auditoria(prot, _sistema(a), carrega_queries(Path(a.queries)),
                    modo=a.mode, politica=pol)
    aud.origem_do_dataset = str(Path(a.queries).name)
    return aud.roda()


def _codigo(m) -> int:
    if any(c.estado is Estado.INVALID for c in m.checks):
        return EXIT["INVALID"]
    if m.status is StatusAuditoria.BLOCKED:
        return EXIT["BLOCKED"]
    # COMPLETE e READY nao tem problema bloqueante. READY significa "auditavel,
    # sem metrica de protocolo configurada" — e o caso comercial do MVP-1:
    # medicoes entregues, Recall@K nao autorizado ainda.
    return EXIT["COMPLETE"]


def _imprime(m) -> None:
    print(f"\nstatus ....... {m.status.value}")
    for c in m.barreiras:
        print(f"  BARRA  {c.nome}\n         {c.motivo}")
    for x in m.medicoes:
        d = x.to_dict()
        print(f"  medido {d['nome']:<32} {round(d['valor'], 4)} "
              f"{d['unidade']} (N={d['N']})")


def cmd_check(a) -> int:
    """Dry-run: READY ou BLOCKED, sem julgador e sem metrica de protocolo."""
    m = _roda(a)
    _imprime(m)
    pronto = not m.barreiras
    print(f"\n{'READY — a infraestrutura sustenta o protocolo' if pronto else 'BLOCKED — ver motivos acima'}")
    print("(dry-run: nenhum julgador executado, nenhuma metrica de protocolo calculada)")
    return _codigo(m)


def cmd_run(a) -> int:
    m = _roda(a)
    out = Path(a.output)
    (out / "artefatos").mkdir(parents=True, exist_ok=True)
    m.salva(out / "manifesto.json")
    (out / "relatorio.md").write_text(relatorio.executivo(m), encoding="utf-8")
    (out / "relatorio_tecnico.md").write_text(relatorio.markdown(m), encoding="utf-8")
    (out / "artefatos" / "checks.json").write_text(
        json.dumps([{"nome": c.nome, "estado": c.estado.value,
                     "detecta": c.detecta, "evidencia": c.evidencia}
                    for c in m.checks], ensure_ascii=False, indent=2),
        encoding="utf-8")
    _imprime(m)
    print(f"\n{out/'relatorio.md'}\n{out/'relatorio_tecnico.md'}\n{out/'manifesto.json'}")
    return _codigo(m)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser("audit", description="servico de auditoria (MVP-1)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def comum(p, com_output: bool):
        p.add_argument("--input",    required=True, help="snapshot do sistema")
        p.add_argument("--protocol", required=True, choices=sorted(PROTOCOLOS))
        p.add_argument("--queries",  required=True)
        p.add_argument("--adaptador", default="edp")
        p.add_argument("--dominios", default=None)
        p.add_argument("--mode", default="AUDIT", choices=["AUDIT", "DIAGNOSTIC"])
        p.add_argument("--exemplos-em-claro", action="store_true",
                       dest="exemplos_em_claro",
                       help="mostra texto do cliente nos artefatos (segredo "
                            "continua removido). Default: so hash.")
        if com_output:
            p.add_argument("--output", required=True)

    comum(sub.add_parser("check", help="dry-run: READY ou BLOCKED"), False)
    comum(sub.add_parser("run", help="auditoria completa"), True)
    a = ap.parse_args(argv)

    try:
        return cmd_check(a) if a.cmd == "check" else cmd_run(a)
    except Exception:
        traceback.print_exc()
        print("\nERRO OPERACIONAL do servico — nao e veredito sobre o sistema "
              "auditado. Nenhuma conclusao deve ser tirada desta execucao.",
              file=sys.stderr)
        return EXIT["ERRO"]


if __name__ == "__main__":
    sys.exit(main())
