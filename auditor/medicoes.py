"""
Medicoes descritivas — o produto comercial do MVP-1.

A DISTINCAO QUE FAZ ISTO EXISTIR

    resultado   metrica DE PROTOCOLO (Recall@K, kappa). Exige que TODAS as
                pre-condicoes passem. Sob BLOCKED, nao existe.

    medicao     fato observavel sobre o material recuperado (duplicacao,
                cardinalidade, distribuicao de score). Exige apenas que o
                ranking seja REAL.

Confundir as duas nas duas direcoes seria erro:

  - tratar medicao como resultado venderia "seu RAG tem 24,8% de duplicacao,
    portanto sua qualidade e X" — nao se segue;
  - tratar resultado como medicao publicaria kappa sob pre-condicao quebrada.

A auditoria do EDP terminou BLOCKED e AINDA ASSIM tem entrega: 50 slots para
30-41 documentos distintos e um achado que o cliente nao tinha. E por isso que
o MVP-1 pode ser vendido sem Recall@K.

TODA MEDICAO CARREGA SEU REFERENTE: o que mede, N, k, snapshot, fonte, e
intervalo quando aplicavel. Numero sem referente nao entra em relatorio.
"""
from __future__ import annotations

import random
import statistics as st
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class Medicao:
    """Um numero e tudo que ele precisa para ser contestado."""
    nome:      str
    valor:     float | int
    o_que_mede: str
    n:         int
    unidade:   str
    k:         int | None = None
    ic95:      tuple[float, float] | None = None
    snapshot:  str = ""
    fonte:     str = ""
    detalhe:   dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "nome": self.nome, "valor": self.valor, "o_que_mede": self.o_que_mede,
            "N": self.n, "unidade": self.unidade, "snapshot": self.snapshot,
            "fonte": self.fonte,
        }
        if self.k is not None:
            d["k"] = self.k
        if self.ic95 is not None:
            d["ic95"] = [round(self.ic95[0], 4), round(self.ic95[1], 4)]
        if self.detalhe:
            d["detalhe"] = self.detalhe
        return d


def _ic_bootstrap(vals: Sequence[float], seed: int = 20260831,
                  b: int = 2000) -> tuple[float, float]:
    """
    IC por bootstrap sobre a QUERY, nao sobre o item.

    Itens da mesma query nao sao independentes; reamostrar item produziria um
    intervalo estreito por construcao. A unidade e a query.
    """
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    meds = []
    n = len(vals)
    for _ in range(b):
        meds.append(sum(rng.choice(vals) for _ in range(n)) / n)
    meds.sort()
    return (meds[int(0.025 * b)], meds[int(0.975 * b)])


def calcula(rankings: dict[str, list[tuple[str, float]]],
            texto_de,
            snapshot: str,
            k: int) -> list[Medicao]:
    """
    As cinco medicoes do MVP-1. Nenhuma delas afirma qualidade de resposta.

    `rankings` — {query_id: [(doc_id, score), ...]}, ja verificado como real.
    """
    F = "ranking real do retriever do sistema auditado"
    qs = list(rankings)
    M: list[Medicao] = []

    # 1. cardinalidade — quantos documentos DISTINTOS a janela top-k entrega
    dist = [len({d for d, _ in rankings[q]}) for q in qs]
    ic = _ic_bootstrap(dist)
    M.append(Medicao(
        "cardinalidade_do_ranking", st.median(dist),
        "documentos DISTINTOS entregues na janela top-k (mediana entre queries). "
        "Slots cheios nao implicam documentos distintos.",
        len(qs), "documentos por query", k, ic, snapshot, F,
        {"min": min(dist), "max": max(dist),
         "slots_por_query": st.median([len(rankings[q]) for q in qs])}))

    # 2. duplicacao por ID dentro da query
    taxa_id = []
    for q in qs:
        ids = [d for d, _ in rankings[q]]
        taxa_id.append((len(ids) - len({*ids})) / len(ids) if ids else 0.0)
    M.append(Medicao(
        "duplicacao_intra_query_por_id", st.median(taxa_id),
        "fracao dos slots do top-k ocupados por um documento que ja apareceu "
        "na MESMA query (mediana entre queries)",
        len(qs), "fracao dos slots", k, _ic_bootstrap(taxa_id), snapshot, F))

    # 3. duplicacao por TEXTO — sobrevive a qualquer dedup por id
    taxa_txt = []
    for q in qs:
        ids = {d for d, _ in rankings[q]}
        txt = {(texto_de(d) or "").strip() for d in ids}
        taxa_txt.append((len(ids) - len(txt)) / len(ids) if ids else 0.0)
    # DETALHE OBRIGATORIO AQUI (NORTE §4.15): a duplicacao por texto e RARA e
    # CONCENTRADA — no EDP, 5 de 50 queries. A mediana dessas 50 e 0,0, e um
    # relatorio que mostrasse so a mediana esconderia o achado inteiro. A
    # mediana e exatamente a grandeza que este defeito nao move; quantas
    # queries sao afetadas, move.
    afetadas = sum(1 for x in taxa_txt if x > 0)
    M.append(Medicao(
        "duplicacao_por_texto", st.median(taxa_txt),
        "fracao dos documentos DISTINTOS cujo texto e identico ao de outro "
        "documento com id diferente. Sobrevive a deduplicacao por id. "
        "ATENCAO: efeito concentrado — leia `queries_afetadas`, nao a mediana.",
        len(qs), "fracao dos documentos distintos", k,
        _ic_bootstrap(taxa_txt), snapshot, F,
        {"queries_afetadas": afetadas,
         "fracao_das_queries_afetadas": round(afetadas / len(qs), 4) if qs else 0,
         "max": max(taxa_txt) if taxa_txt else 0}))

    # 4. sobreposicao entre queries — o mesmo material servindo a tudo
    conj = [{d for d, _ in rankings[q]} for q in qs]
    pares, jac = 0, []
    for i in range(len(conj)):
        for j in range(i + 1, len(conj)):
            u = conj[i] | conj[j]
            if u:
                jac.append(len(conj[i] & conj[j]) / len(u)); pares += 1
    M.append(Medicao(
        "sobreposicao_cross_query", st.median(jac) if jac else 0.0,
        "Jaccard mediano entre os top-k de pares de queries distintas. Alto "
        "indica que o retriever devolve o mesmo material independente da pergunta.",
        pares, "Jaccard entre pares de queries", k,
        _ic_bootstrap(jac) if jac else None, snapshot, F,
        {"queries": len(qs)}))

    # 5. distribuicao de score — separacao entre topo e cauda
    topo, cauda = [], []
    for q in qs:
        s = [sc for _, sc in rankings[q]]
        if len(s) >= 10:
            topo.append(st.median(s[:5])); cauda.append(st.median(s[-5:]))
    razao = [t / c if c else float("nan") for t, c in zip(topo, cauda)]
    razao = [r for r in razao if r == r]
    M.append(Medicao(
        "razao_score_topo_cauda", st.median(razao) if razao else float("nan"),
        "score mediano das 5 primeiras posicoes dividido pelo das 5 ultimas. "
        "Proximo de 1 indica ranking pouco discriminativo.",
        len(razao), "razao adimensional", k,
        _ic_bootstrap(razao) if razao else None, snapshot, F))

    return M
