"""
Pre-condicoes estatisticas. Uma metrica calculavel nem sempre e interpretavel.

Estes checks rodam ANTES do calculo, nao depois. Um kappa de 0,9 sob prevalencia
de 97% nao e um bom kappa — e um numero que a prevalencia produz sozinha, e
publicar isso e o modo mais facil de o servico mentir sem errar uma conta.
"""
from __future__ import annotations

from collections import Counter
from typing import Sequence

from ..estados import Estado
from .base import Resultado

# Fora desta faixa o kappa fica dominado pela prevalencia (paradoxo classico).
PREVALENCIA_MIN = 0.10
PREVALENCIA_MAX = 0.90


def prevalencia_permite_acordo(rotulos: Sequence[int],
                               nome_do_estrato: str = "") -> Resultado:
    """
    §4.15 — a grandeza aqui e a PREVALENCIA, nao o kappa.

    Olhar so para o kappa nao move: 0,9 aparece tanto num instrumento bom quanto
    num estrato onde 97% das respostas sao iguais. A prevalencia e o numero que
    distingue os dois casos, e por isso e ela que barra.
    """
    D = ("paradoxo da prevalencia: acordo alto produzido pelo desbalanceamento "
         "do estrato, nao pela qualidade do instrumento")
    N = "estatistica.prevalencia_permite_acordo"

    if not rotulos:
        return Resultado(N, Estado.BLOCKED, D, {}, "sem rotulos para avaliar")
    c = Counter(rotulos)
    p = c.get(1, 0) / len(rotulos)
    ev = {"n": len(rotulos), "prevalencia_positiva": round(p, 4),
          "faixa_aceita": [PREVALENCIA_MIN, PREVALENCIA_MAX],
          "estrato": nome_do_estrato}

    if not (PREVALENCIA_MIN <= p <= PREVALENCIA_MAX):
        return Resultado(N, Estado.BLOCKED, D, ev,
                         f"prevalencia {p:.1%} fora da faixa "
                         f"[{PREVALENCIA_MIN:.0%}, {PREVALENCIA_MAX:.0%}]: um "
                         f"indice de acordo neste estrato mede o "
                         f"desbalanceamento, nao a concordancia. "
                         f"(NORTE §4.14 — concordancia nao e verdade.)")
    return Resultado(N, Estado.PASS, D, ev)


def unidades_suficientes(n_unidades: int, minimo: int,
                         unidade: str = "query") -> Resultado:
    """
    Bootstrap por cluster precisa de clusters, nao de itens.

    §4.15 — contar ITENS nao move: 500 pares parecem muitos e sao 50 queries.
    Itens dentro da mesma query nao sao independentes, e o IC calculado sobre
    500 seria estreito por construcao.
    """
    D = ("intervalo de confianca estreito por construcao: itens correlacionados "
         "contados como independentes")
    N = "estatistica.unidades_suficientes"
    ev = {"unidades": n_unidades, "minimo": minimo, "unidade": unidade}
    if n_unidades < minimo:
        return Resultado(N, Estado.BLOCKED, D, ev,
                         f"{n_unidades} {unidade}(s) independentes; o bootstrap "
                         f"por cluster exige {minimo}")
    return Resultado(N, Estado.PASS, D, ev)
