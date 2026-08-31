"""
Checks de ranking. Todos nasceram da invalidacao 01 do REL-001.

O defeito original: `[i for i in txt]` — os documentos em ordem de insercao do
arquivo — passou por ranking do retriever, e nada reclamou. Uma lista de ids e
uma lista de ids. Custou 500 pares e 492 rotulos.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from ..estados import Estado
from .base import Resultado


def veio_do_retriever(ranking: Sequence[tuple[str, float]]) -> Resultado:
    """
    O ranking carrega prova de origem.

    §4.15 — a grandeza escolhida e o SCORE, nao um campo `procedencia`. Uma
    string se escreve; o que ordem de arquivo nao tem e RRF estritamente
    positivo e nao-crescente. Este numero se move quando o defeito existe.
    """
    D = ("ranking fabricado: ordem de arquivo, ordem alfabetica, ou qualquer "
         "sequencia que nao saiu do retriever")
    N = "ranking.veio_do_retriever"

    if not ranking:
        return Resultado(N, Estado.FAIL, D, motivo="ranking vazio")
    if not all(isinstance(x, (tuple, list)) and len(x) == 2 for x in ranking):
        return Resultado(N, Estado.FAIL, D,
                         motivo="ranking nao e sequencia de (doc_id, score); "
                                "lista de ids nua nao prova procedencia")
    scores = [float(s) for _, s in ranking]
    ev = {"n": len(ranking), "score_max": max(scores), "score_min": min(scores)}

    if any(s <= 0 for s in scores):
        return Resultado(N, Estado.FAIL, D, ev,
                         f"score nao-positivo (min={min(scores)}): score perdido "
                         f"no caminho ou ranking fabricado")
    if len(set(scores)) == 1:
        return Resultado(N, Estado.FAIL, D, ev,
                         "todos os scores identicos: ordem de arquivo com um "
                         "numero constante colado")
    if any(a < b for a, b in zip(scores, scores[1:])):
        return Resultado(N, Estado.FAIL, D, ev,
                         "scores nao sao nao-crescentes: o ranking nao esta na "
                         "ordem que o retriever devolveu")
    return Resultado(N, Estado.PASS, D, ev)


def cardinalidade(ranking: Sequence[tuple[str, float]],
                  minimo: int) -> Resultado:
    """
    Ha documentos DISTINTOS suficientes — nao slots suficientes.

    §4.15 — contar slots foi o erro do REL-001A. Com `top_k=50` o retriever
    devolve 50 slots haja ou nao duplicacao: e a unica contagem que o defeito
    nao toca. A grandeza que se move e `ids distintos`.
    """
    D = ("duplicacao no indice consumindo a janela top-k: slots cheios, "
         "documentos distintos insuficientes")
    N = "ranking.cardinalidade"

    if not all(isinstance(x, (tuple, list)) and len(x) == 2 for x in ranking):
        return Resultado(N, Estado.BLOCKED, D, {},
                         "formato do ranking desconhecido: rode "
                         "`ranking.veio_do_retriever` antes deste check")
    ids = [d for d, _ in ranking]
    dist = len(set(ids))
    ev = {"slots": len(ids), "ids_distintos": dist, "exigido": minimo,
          "ids_repetidos": len(ids) - dist}

    if dist < minimo:
        return Resultado(N, Estado.BLOCKED, D, ev,
                         f"{len(ids)} slots devolvidos, mas apenas {dist} "
                         f"documentos DISTINTOS; o protocolo exige {minimo}. "
                         f"Contar slots teria passado.")
    return Resultado(N, Estado.PASS, D, ev)


def duplicacao_medida(ranking: Sequence[tuple[str, float]],
                      texto_de: dict[str, str] | None = None) -> Resultado:
    """
    Mede a duplicacao em dois eixos e NUNCA barra — e diagnostico.

    Dois eixos porque sao dois defeitos diferentes: o mesmo id em duas camadas
    (consolidacao que promove sem remover) e o mesmo TEXTO sob ids diferentes
    (resumo regenerado). O segundo sobrevive a qualquer dedup por id.
    """
    ids = [d for d, _ in ranking]
    c = Counter(ids)
    ev: dict[str, Any] = {
        "slots": len(ids),
        "ids_distintos": len(c),
        "ids_repetidos": sum(n - 1 for n in c.values() if n > 1),
    }
    if texto_de:
        textos = [(texto_de.get(d) or "").strip() for d in set(ids)]
        ev["textos_distintos"] = len(set(textos))
        ev["ids_com_texto_repetido"] = len(c) - len(set(textos))
    return Resultado("ranking.duplicacao_medida", Estado.PASS,
                     "duplicacao por id e por texto no material recuperado",
                     ev, bloqueia=False)
