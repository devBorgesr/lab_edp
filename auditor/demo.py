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


INTERPRETACAO = {
    "complete": """# Como ler este exemplo

**Status `COMPLETE`** — o `DIAGNOSTICO v1` executou. As cinco medicoes sao o
resultado dessa regua.

## O que os numeros dizem

Cada linha traz `N`, unidade e intervalo. Um numero sem esses campos nao sai do
servico: numero sem referente e alegacao, nao medida.

## O que eles NAO dizem

Nada sobre qualidade de resposta, Recall@K ou relevancia — nenhum julgamento
foi feito. E nao ha linha de base: com poucos sistemas medidos, nao da para
dizer se um valor observado e alto ou baixo em relacao a outros.

Descrevem **o que foi recuperado**, nao **se o que foi recuperado era o certo**.

## Limitacoes

Corpus sintetico. Nenhum dado de cliente. Serve para mostrar o formato da
entrega, nao para sustentar afirmacao sobre sistema nenhum.
""",
    "blocked": """# Como ler este exemplo

**Status `BLOCKED`** — o protocolo nao pode ser executado sobre este sistema.

## Isto nao e falha do servico

`BLOCKED` significa que **aquela regua** nao se aplica **aquele sistema**. Nao
significa que o sistema seja inauditavel: outra regua pode se aplicar a ele.

## O que o cliente recebe mesmo assim

As medicoes descritivas, quando o ranking tem procedencia provada. Um `BLOCKED`
por requisito de protocolo nao apaga o que ja era valido.

O que apaga tudo e ranking sem procedencia — nesse caso nao ha medicao nenhuma,
porque medir sobre ranking nao verificado nao mede nada.

## Limitacoes

Corpus sintetico. Nenhum dado de cliente.
""",
}


def gera(destino: Path) -> dict[str, str]:
    """
    Exemplos publicos. Corpus sintetico, nenhum dado real.

    Cada um traz input, manifesto, os dois relatorios e a interpretacao — o que
    um cliente precisa para julgar o formato antes de entregar qualquer coisa.
    """
    import json as _json
    destino.mkdir(parents=True, exist_ok=True)
    saida = {}
    casos = (("complete", "DIAGNOSTICO", 0.6), ("blocked", "BASICO", 0.6))
    for rot, prot, taxa in casos:
        d = destino / rot
        (d / "artefatos").mkdir(parents=True, exist_ok=True)
        sis = ClienteSintetico(d / "_corpus", taxa_duplicacao=taxa)
        sis.estatistica = lambda: {"cobertura_do_pool": 0.71, "n_queries": 24}
        qs = queries_cliente(24)
        aud = Auditoria(PROTOCOLOS[prot], sis, qs)
        aud.origem_do_dataset = "exemplo sintetico"
        m = aud.roda()
        (d / "input.json").write_text(_json.dumps({
            "schema": "AuditInput v1", "snapshot": "<corpus sintetico>",
            "queries": f"<{len(qs)} perguntas sinteticas>",
            "protocol": prot, "adapter": "sintetico"}, indent=2), encoding="utf-8")
        m.salva(d / "manifesto.json")
        (d / "relatorio.md").write_text(relatorio.executivo(m), encoding="utf-8")
        (d / "relatorio_tecnico.md").write_text(relatorio.markdown(m),
                                                encoding="utf-8")
        (d / "COMO_LER.md").write_text(INTERPRETACAO[rot], encoding="utf-8")
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
