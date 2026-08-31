"""
Checks de estrato. Nasceram de dois defeitos reais do REL-001.

1. o `topo` era ordem de arquivo — 4 conjuntos para 50 queries;
2. o `controle` saia de `corpus_de_outro_dominio`, que TAMBEM esta no ranking:
   8 colisoes em 500 pares, 6 delas topo ∩ controle. Um documento que o
   retriever poe no top-5 nao e controle negativo de outro dominio.
"""
from __future__ import annotations

from collections import Counter
from typing import Sequence

from ..estados import Estado
from .base import Resultado


def sem_sobreposicao(pool: Sequence[dict]) -> Resultado:
    """
    Nenhum documento em dois estratos da MESMA query.

    §4.15 — contar o tamanho do pool (10) nao move: um documento repetido em
    `topo` e `cauda` mantem 10. A grandeza que se move e `documentos distintos
    no pool`, e o custo de errar e o par entrar duas vezes no kappa.
    """
    D = "mesmo documento julgado duas vezes, entrando duas vezes na estatistica"
    N = "estratos.sem_sobreposicao"

    docs = [p["doc"] for p in pool]
    c = Counter(docs)
    rep = {d: n for d, n in c.items() if n > 1}
    ev = {"pool": len(docs), "docs_distintos": len(c), "repetidos": len(rep)}

    if rep:
        onde = {d: sorted({p["estrato"] for p in pool if p["doc"] == d})
                for d in list(rep)[:5]}
        ev["exemplos"] = onde
        return Resultado(N, Estado.FAIL, D, ev,
                         f"{len(rep)} documento(s) em mais de um estrato: {onde}")
    return Resultado(N, Estado.PASS, D, ev)


def controle_fora_do_ranking(controle: Sequence[str],
                             ranking: Sequence[tuple[str, float]]) -> Resultado:
    """
    O controle negativo nao pode ser documento que o retriever rankeou.

    Um documento no top-50 e, pela medida do proprio retriever, relacionado a
    query. Chama-lo de "outro dominio" contradiz o instrumento, e a previsao
    pre-registrada (~100% de acordo em irrelevante) fica errada por construcao.
    """
    D = ("controle negativo contaminado: documento rankeado pelo retriever "
         "usado como 'outro dominio'")
    N = "estratos.controle_fora_do_ranking"

    no_rank = {d for d, _ in ranking}
    colisao = sorted(set(controle) & no_rank)
    ev = {"controle": len(controle), "colisoes": len(colisao)}
    if colisao:
        ev["exemplos"] = colisao[:5]
        return Resultado(N, Estado.FAIL, D, ev,
                         f"{len(colisao)} documento(s) de controle aparecem no "
                         f"ranking da propria query")
    return Resultado(N, Estado.PASS, D, ev)


def tamanhos(pool: Sequence[dict], exigido: dict[str, int]) -> Resultado:
    """Cada estrato tem exatamente o tamanho que o protocolo congelou."""
    D = "pool incompleto — muda a prevalencia e portanto muda o kappa"
    N = "estratos.tamanhos"

    tem = Counter(p["estrato"] for p in pool)
    ev = {"obtido": dict(tem), "exigido": dict(exigido)}
    dif = {e: (tem.get(e, 0), n) for e, n in exigido.items() if tem.get(e, 0) != n}
    if dif:
        return Resultado(N, Estado.FAIL, D, ev,
                         f"estrato fora do tamanho congelado: {dif}")
    return Resultado(N, Estado.PASS, D, ev)
