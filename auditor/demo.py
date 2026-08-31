"""
Duas demonstracoes publicas, sem dado de ninguem.

    DEMO A  auditoria COMPLETE
    DEMO B  auditoria BLOCKED

A B e a comercialmente importante: mostra a caracteristica que distingue o
servico — ele nao inventa resultado, e ainda assim entrega diagnostico.

    python -m auditor.demo <diretorio>
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import relatorio
from .cli import PROTOCOLOS
from .fixtures import ClienteSintetico, queries_cliente
from .pipeline import Auditoria


def gera(destino: Path) -> dict[str, str]:
    destino.mkdir(parents=True, exist_ok=True)
    saida = {}
    for rot, taxa in (("A_completa", 0.0), ("B_bloqueada", 0.6)):
        d = destino / rot
        (d / "artefatos").mkdir(parents=True, exist_ok=True)
        sis = ClienteSintetico(d / "_corpus", taxa_duplicacao=taxa)
        sis.estatistica = lambda: {"cobertura_do_pool": 0.71, "n_queries": 24}
        m = Auditoria(PROTOCOLOS["BASICO"], sis, queries_cliente(24)).roda()
        m.salva(d / "manifesto.json")
        (d / "relatorio.md").write_text(relatorio.executivo(m), encoding="utf-8")
        (d / "relatorio_tecnico.md").write_text(relatorio.markdown(m),
                                                encoding="utf-8")
        saida[rot] = m.status.value
    return saida


def main(argv=None) -> int:
    destino = Path((argv or sys.argv[1:])[0] if (argv or sys.argv[1:]) else "demos")
    for rot, st in gera(destino).items():
        print(f"{rot:<14} {st}")
    print(f"\n{destino}")
    print("Corpus sintetico: nenhum dado de cliente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
