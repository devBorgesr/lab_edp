"""
test_cobertura.py — `bancada.cobertura`.

Reps e B baixos de propósito: estes testes travam o CONTRATO do instrumento
(reamostra pares, devolve IC ordenado, calcula razão agregada e não média de
razões), não reproduzem o estudo de cobertura — esse leva dezenas de segundos e
é para rodar à mão antes de congelar um pré-registro.

O achado que motivou o módulo está no docstring dele e não é re-medido aqui:
teste que roda 30s em toda suíte vira teste que alguém desliga.
"""
from __future__ import annotations

import random

import pytest

from bancada.cobertura import (
    alvo_com_overhead,
    cobertura_simulada,
    gerador_razao,
    ic_bootstrap_percentil,
    razao_agregada,
)


# ── razão agregada != média de razões ────────────────────────────────────────

def test_razao_agregada_nao_e_media_de_razoes():
    """
    A distinção decide resultado. Aqui a média das razões é (1+10)/2 = 5.5; a
    agregada é (10+1000)/(10+100) ≈ 9.18 — porque pondera pelo tamanho, que é o
    que se quer quando o denominador é custo.
    """
    pares = [(10.0, 10.0), (1000.0, 100.0)]
    assert razao_agregada(pares) == pytest.approx(1010 / 110)
    media_de_razoes = sum(a / b for a, b in pares) / len(pares)
    assert razao_agregada(pares) != pytest.approx(media_de_razoes)


def test_razao_agregada_exata_sem_ruido():
    assert razao_agregada([(4.0, 1.0)] * 50) == pytest.approx(4.0)


def test_denominador_zero_levanta():
    with pytest.raises(ValueError):
        razao_agregada([(1.0, 0.0)])


# ── IC ───────────────────────────────────────────────────────────────────────

def test_ic_contem_o_ponto_estimado():
    rng = random.Random(1)
    pares = gerador_razao(80, 4.0)(rng)
    lo, hi = ic_bootstrap_percentil(pares, b=300, rng=rng)
    assert lo < razao_agregada(pares) < hi


def test_ic_e_ordenado_e_estreita_com_n():
    """Mais dado, menos incerteza — se não estreitar, o bootstrap está errado."""
    rng = random.Random(2)
    l1, h1 = ic_bootstrap_percentil(gerador_razao(20, 4.0)(rng), b=300, rng=rng)
    l2, h2 = ic_bootstrap_percentil(gerador_razao(400, 4.0)(rng), b=300, rng=rng)
    assert l1 < h1 and l2 < h2
    assert (h2 - l2) < (h1 - l1)


def test_ic_de_amostra_sem_variancia_colapsa():
    rng = random.Random(3)
    lo, hi = ic_bootstrap_percentil([(4.0, 1.0)] * 40, b=200, rng=rng)
    assert lo == pytest.approx(4.0) and hi == pytest.approx(4.0)


def test_amostra_vazia_levanta():
    with pytest.raises(ValueError):
        ic_bootstrap_percentil([])


def test_ic_e_reprodutivel_com_semente():
    """Sem isto, dois relatórios do mesmo dado divergiriam sem explicação."""
    pares = gerador_razao(50, 4.0)(random.Random(4))
    a = ic_bootstrap_percentil(pares, b=300, rng=random.Random(9))
    b = ic_bootstrap_percentil(pares, b=300, rng=random.Random(9))
    assert a == b


# ── overhead fixo: a razão verdadeira deixa de ser o parâmetro ──────────────

def test_overhead_afasta_o_alvo_do_parametro():
    """
    Com custo fixo no denominador, a razão agregada verdadeira NÃO é `razao` —
    é menor. Quem simular cobertura contra `razao` nesse regime mede a coisa
    errada e conclui que o IC é péssimo.
    """
    alvo = alvo_com_overhead(4.0, overhead=40.0)
    assert alvo < 4.0
    assert 3.5 < alvo < 4.0


def test_sem_overhead_o_alvo_e_o_parametro():
    assert alvo_com_overhead(4.0, overhead=0.0) == pytest.approx(4.0)


# ── contrato do estudo de cobertura ─────────────────────────────────────────

def test_cobertura_simulada_devolve_o_contrato():
    r = cobertura_simulada(gerador_razao(30, 4.0), alvo=4.0,
                           reps=25, b=120, semente=5)
    assert set(r) == {"cobertura", "se", "largura_media", "nominal", "reps", "b"}
    assert 0.0 <= r["cobertura"] <= 1.0
    assert r["se"] > 0 and r["largura_media"] > 0
    assert r["nominal"] == 0.90


def test_cobertura_de_ic_absurdamente_estreito_e_baixa():
    """
    Sanidade do medidor: com conf=0.01 o IC é quase um ponto e a cobertura tem
    de desabar. Se não desabasse, o instrumento não estaria medindo cobertura.
    """
    r = cobertura_simulada(gerador_razao(30, 4.0), alvo=4.0,
                           reps=25, b=120, conf=0.01, semente=6)
    assert r["cobertura"] < 0.5
