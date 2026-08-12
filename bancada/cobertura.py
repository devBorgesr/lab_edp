#!/usr/bin/env python3
"""
bancada.cobertura — o intervalo de confiança que você vai congelar cobre mesmo?

AUTOCONTIDO: stdlib apenas, zero imports de edp/bancada/sujeitos — mesma
propriedade de `bancada.auditoria`. Não usa numpy nem scipy de propósito: o
`pyproject.toml` deste repo não declara nenhuma dependência de runtime, e
adicionar uma para rodar um bootstrap percentil (que é ~20 linhas de stdlib)
seria pagar caro por conveniência.

──────────────────────────────────────────────────────────────────────────────
A ARMADILHA QUE ESTE MÓDULO EXISTE PARA EVITAR
──────────────────────────────────────────────────────────────────────────────

Escrever "IC 90%" num critério de decisão pré-registrado e nunca verificar se
ele cobre 90%. O nome do método não é garantia: bootstrap percentil sobre
**estimador de razão** (Σa/Σb) com n pequeno **subcobre** — mede-se ~87% onde o
rótulo diz 90%.

Consequência prática num teste de equivalência: o IC sai mais estreito do que a
incerteza real, empurrando o veredito para "dentro da faixa" mais do que o
nível nominal deixa entender. Ou seja, o erro é na direção de **aceitar H0
falsamente**, que costuma ser a direção que o experimentador queria.

Congelar sem medir esconde isso. Medir custa um minuto.

Achado que motivou o módulo (calibração de tokens do EDP, 12/08/2026, replicado
com duas sementes independentes): n=30, IC nominal 90%, cobertura real 0.858 a
0.882 conforme o modelo de ruído. Uma tentativa de "corrigir" subindo n para
100 **não** mostrou convergência clara nem em n=200 (0.885) — então subir n não
é a saída óbvia que parece.

──────────────────────────────────────────────────────────────────────────────
LIMITE DECLARADO
──────────────────────────────────────────────────────────────────────────────

`cobertura_simulada` mede a cobertura sob o gerador de dado sintético que VOCÊ
passar. A direção do viés (subcobertura em n pequeno para estimador de razão) é
conhecida e não depende do gerador; **o número exato depende**, e varia alguns
pontos percentuais só trocando a semente. Reporte a ordem de grandeza, não o
terceiro dígito.

USO:
    from bancada.cobertura import ic_bootstrap_percentil, cobertura_simulada
"""
from __future__ import annotations

import random
from typing import Callable, Sequence


def razao_agregada(pares: Sequence[tuple[float, float]]) -> float:
    """
    Σnumerador / Σdenominador — NÃO a média das razões individuais.

    A distinção decide resultado: média de razões pondera igualmente uma
    observação minúscula e uma enorme, e é justamente na minúscula que efeitos
    de overhead fixo dominam. A razão agregada pondera pelo tamanho, que é o
    que quase sempre se quer quando o denominador é um custo.
    """
    num = den = 0.0
    for a, b in pares:
        num += a
        den += b
    if den == 0:
        raise ValueError("denominador agregado zero")
    return num / den


def ic_bootstrap_percentil(
    pares: Sequence[tuple[float, float]],
    b: int = 2000,
    conf: float = 0.90,
    rng: random.Random | None = None,
) -> tuple[float, float]:
    """
    IC percentil por bootstrap não-paramétrico, reamostrando **pares**.

    Reamostrar o par (e não cada lado independentemente) é o que preserva a
    estrutura do estimador: numerador e denominador da mesma observação são
    correlacionados, e quebrá-los produziria um IC otimista.

    Bootstrap e não erro-padrão de média: Σa/Σb não é média simples, e aplicar
    a fórmula de SE de média sobre ele é usar a fórmula errada.
    """
    if not pares:
        raise ValueError("amostra vazia")
    rng = rng or random.Random()
    n = len(pares)
    idx = range(n)
    replicas = []
    for _ in range(b):
        num = den = 0.0
        for i in rng.choices(idx, k=n):
            a, d = pares[i]
            num += a
            den += d
        if den:
            replicas.append(num / den)
    replicas.sort()
    alfa = (1.0 - conf) / 2.0
    lo = replicas[max(0, int(alfa * len(replicas)))]
    hi = replicas[min(len(replicas) - 1, int((1.0 - alfa) * len(replicas)))]
    return lo, hi


def cobertura_simulada(
    gerador: Callable[[random.Random], Sequence[tuple[float, float]]],
    alvo: float,
    reps: int = 500,
    b: int = 1000,
    conf: float = 0.90,
    semente: int | None = None,
) -> dict:
    """
    Mede a cobertura REAL do IC contra um valor verdadeiro conhecido.

    `gerador(rng)` devolve uma amostra de pares cujo `alvo` (a razão agregada
    verdadeira, sem ruído amostral) você conhece por construção. Rode isto
    ANTES de congelar um nível de confiança em pré-registro.

    Devolve `cobertura`, `se` (erro-padrão binomial da própria estimativa) e
    `largura_media`. Compare a cobertura com `conf`: se a diferença passar de
    2·se, a subcobertura é sistemática, não ruído de Monte Carlo.

    Custo: reps × b × n operações em Python puro. reps=500, b=1000, n=30 leva
    dezenas de segundos — é instrumento de rodar uma vez, não de laço quente.
    """
    rng = random.Random(semente)
    acertos = 0
    larguras = []
    for _ in range(reps):
        amostra = gerador(rng)
        lo, hi = ic_bootstrap_percentil(amostra, b=b, conf=conf, rng=rng)
        larguras.append(hi - lo)
        if lo <= alvo <= hi:
            acertos += 1
    p = acertos / reps
    return {
        "cobertura": p,
        "se": (p * (1 - p) / reps) ** 0.5,
        "largura_media": sum(larguras) / len(larguras),
        "nominal": conf,
        "reps": reps,
        "b": b,
    }


def gerador_razao(
    n: int,
    razao: float,
    ruido_rel: float = 0.08,
    overhead: float = 0.0,
    faixa: tuple[float, float] = (200.0, 12000.0),
) -> Callable[[random.Random], list[tuple[float, float]]]:
    """
    Gerador sintético para `cobertura_simulada`.

    `overhead > 0` injeta custo fixo no denominador — o regime em que a razão
    verdadeira **depende do tamanho** da observação (andaime fixo dominando
    observação pequena). Vale testar os dois: a cobertura muda entre eles, e
    qual dos dois descreve seu dado real é pergunta empírica, não suposição.

    Com `overhead > 0` o alvo NÃO é `razao` — use `alvo_com_overhead`.
    """
    def _gera(rng: random.Random) -> list[tuple[float, float]]:
        out = []
        for _ in range(n):
            a = rng.uniform(*faixa)
            d = a / razao * (1.0 + rng.gauss(0.0, ruido_rel)) + overhead
            out.append((a, max(d, 1.0)))
        return out
    return _gera


def alvo_com_overhead(
    razao: float,
    overhead: float,
    faixa: tuple[float, float] = (200.0, 12000.0),
    n_grid: int = 200_000,
    semente: int = 0,
) -> float:
    """Razão agregada verdadeira sob overhead fixo, sem ruído amostral."""
    rng = random.Random(semente)
    num = den = 0.0
    for _ in range(n_grid):
        a = rng.uniform(*faixa)
        num += a
        den += a / razao + overhead
    return num / den
