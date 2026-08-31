"""
CLI do MVP-0. HTTP fica para depois: primeiro o pipeline precisa estar certo.

    python -m auditor run --input <store> --protocol REL-001 --output <dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import relatorio
from .estados import StatusAuditoria
from .pipeline import Auditoria, Protocolo

PROTOCOLOS = {
    "REL-001": Protocolo("REL-001", 50, {"topo": 5, "cauda": 3, "controle": 2},
                         (19, 50), 50),
}


def _monta(a) -> tuple[Protocolo, object, list[dict]]:
    prot = PROTOCOLOS[a.protocol]
    from .adaptadores.edp import EDPAuditavel
    sis = EDPAuditavel(Path(a.input), Path(a.dominios) if a.dominios else None)
    am = json.loads(Path(a.amostra).read_text("utf-8"))
    qs = [{"id": q["sha256_query"][:12], "query": q["query"],
           "dominio": q.get("dominio", "")} for q in am["queries"]]
    return prot, sis, qs


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser("audit", description="MVP-0 do servico de auditoria")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="roda uma auditoria")
    r.add_argument("--input",    required=True, help="store do sistema auditado")
    r.add_argument("--protocol", required=True, choices=sorted(PROTOCOLOS))
    r.add_argument("--output",   required=True, help="diretorio do resultado")
    r.add_argument("--amostra",  required=True)
    r.add_argument("--dominios", default=None)
    r.add_argument("--mode", default="AUDIT", choices=["AUDIT", "DIAGNOSTIC"])
    a = ap.parse_args(argv)

    prot, sis, qs = _monta(a)
    m = Auditoria(prot, sis, qs, modo=a.mode).roda()

    out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
    m.salva(out / "manifesto.json")
    (out / "relatorio.md").write_text(relatorio.markdown(m), encoding="utf-8")

    print(f"\nstatus ....... {m.status.value}")
    for c in m.barreiras:
        print(f"  BARRA  {c.nome}: {c.motivo[:90]}")
    print(f"\n{out / 'relatorio.md'}\n{out / 'manifesto.json'}")
    # BLOQUEADO nao e erro de execucao: e um resultado legitimo do servico.
    # Codigo 2 permite ao chamador distinguir sem tratar como crash.
    return 0 if m.status is StatusAuditoria.COMPLETE else 2


if __name__ == "__main__":
    sys.exit(main())
