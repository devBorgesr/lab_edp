"""
tests/test_exp_e7.py — E7 HARNESS: regressão das partes puras (§5 métricas,
§6 veredito) e da guarda de poder (§4). NÃO testa o retrieve real (exige
`edp` instalado + store de verdade) — mesmo precedente de exp008/009/010,
que também não têm testes de pipeline completo por esse motivo (ver FASE B1).

Fixture calculável à mão: 6 turnos, top_k=5.
    q1={A,B,C,D,E}  q2={A,B,F,G,H}  q3={I,J,K,L,M}
    q4={N,O,P,Q,R}  q5={N,O,S,T,U}  q6={N,O,V,W,X}
Pares consecutivos (ordem real): (q1,q2)=2/5 [bin], (q2,q3)=0, (q3,q4)=0,
(q4,q5)=2/5 [bin], (q5,q6)=2/5 [bin] — 3 pares com overlap 2/5, 2 sem.
"""
from __future__ import annotations

import pytest

from sujeitos.edp.experimentos.exp_e7 import (
    CORTE_H0_PP,
    CORTE_H1_PP,
    MIN_TURNOS,
    SEED_SHUFFLE,
    _ler_sequencia,
    _sha256_arquivo,
    calcula_condicao,
    calcula_veredito,
    classifica_veredito,
    instrumento_valido,
    main,
    permuta_shuffled,
)


def _r(query: str, ids: str) -> dict:
    return {"query": query, "results": [{"id": i, "texto": i.lower()} for i in ids]}


FIXTURE_REGISTROS = [
    _r("q1", "ABCDE"),
    _r("q2", "ABFGH"),
    _r("q3", "IJKLM"),
    _r("q4", "NOPQR"),
    _r("q5", "NOSTU"),
    _r("q6", "NOVWX"),
]


def test_calcula_condicao_bate_com_valores_calculados_a_mao():
    c = calcula_condicao(FIXTURE_REGISTROS, top_k=5)

    assert c["n_pares"] == 5
    assert c["k_bin"] == 3
    assert c["binario"] == 3 / 5
    assert c["continuo"] == pytest.approx((2 / 5 + 0 + 0 + 2 / 5 + 2 / 5) / 5)
    assert c["ref_binario"] == pytest.approx(4 / 15)   # C(6,2)=15 pares; so (q1,q2),(q4,q5),(q4,q6),(q5,q6) tem overlap
    assert c["ref_continuo"] == pytest.approx((4 * (2 / 5)) / 15)
    assert c["ci_low"] < c["binario"] < c["ci_high"]


def test_referencia_neutra_e_invariante_a_permutacao():
    real = calcula_condicao(FIXTURE_REGISTROS, top_k=5)
    embaralhado = calcula_condicao(permuta_shuffled(FIXTURE_REGISTROS), top_k=5)

    # matriz completa e simetrica por conjunto: a ordem nao muda a referencia
    assert embaralhado["ref_binario"] == real["ref_binario"]
    assert embaralhado["ref_continuo"] == real["ref_continuo"]


def test_permuta_shuffled_e_reproduzivel_com_mesma_seed():
    a = permuta_shuffled(FIXTURE_REGISTROS, seed=SEED_SHUFFLE)
    b = permuta_shuffled(FIXTURE_REGISTROS, seed=SEED_SHUFFLE)

    assert [r["query"] for r in a] == [r["query"] for r in b]


def test_permuta_shuffled_preserva_conjunto_mas_muda_ordem():
    embaralhado = permuta_shuffled(FIXTURE_REGISTROS, seed=SEED_SHUFFLE)

    assert sorted(r["query"] for r in embaralhado) == sorted(r["query"] for r in FIXTURE_REGISTROS)
    assert [r["query"] for r in embaralhado] != [r["query"] for r in FIXTURE_REGISTROS]
    assert [r["query"] for r in embaralhado] == ["q6", "q3", "q1", "q5", "q4", "q2"]


def test_veredito_h1_quando_shuffled_destroi_a_adjacencia():
    resultado = calcula_veredito(FIXTURE_REGISTROS)

    # seed congelada 20260728 -> shuffled binario cai pra 1/5; gap = 40pp
    assert resultado["gap_pp"] == pytest.approx(40.0)
    assert resultado["veredito"] == "H1 — TOPICALIDADE DOMINA"
    # referencia neutra (4/15≈0.267) cai entre shuffled (0.2) e real (0.6)
    assert resultado["instrumento_valido"] is True


def test_classifica_veredito_nos_cortes_exatos():
    assert classifica_veredito(CORTE_H1_PP) == "H1 — TOPICALIDADE DOMINA"
    assert classifica_veredito(CORTE_H1_PP + 0.01) == "H1 — TOPICALIDADE DOMINA"
    assert classifica_veredito(CORTE_H1_PP - 0.01) == "MISTO"
    assert classifica_veredito(CORTE_H0_PP) == "H0 — PATOLOGIA"
    assert classifica_veredito(CORTE_H0_PP - 0.01) == "H0 — PATOLOGIA"
    assert classifica_veredito(CORTE_H0_PP + 0.01) == "MISTO"
    assert classifica_veredito((CORTE_H0_PP + CORTE_H1_PP) / 2) == "MISTO"


def test_instrumento_valido_dentro_e_fora_do_intervalo():
    assert instrumento_valido(ref=0.3, a=0.2, b=0.6) is True    # entre shuffled e real, em qualquer ordem
    assert instrumento_valido(ref=0.3, a=0.6, b=0.2) is True
    assert instrumento_valido(ref=0.9, a=0.2, b=0.6) is False   # fora do intervalo
    assert instrumento_valido(ref=None, a=0.2, b=0.6) is None


def test_guarda_de_poder_para_com_menos_de_min_turnos_sem_tocar_edp(tmp_path, monkeypatch, capsys):
    linhas = [f'{{"query": "q{i}", "id": "e{i}", "timestamp": {i}}}' for i in range(MIN_TURNOS - 1)]
    seq_path = tmp_path / "e7_sequencia.jsonl"
    seq_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    rc = main(["--sequencia", str(seq_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert f"n_turnos           : {MIN_TURNOS - 1}" in out
    assert "PARAR (poder insuficiente" in out
    assert _sha256_arquivo(seq_path) in out
    # nao criou export de resultados: a guarda parou ANTES de tocar edp/isolamento
    assert not (tmp_path / "e7_resultados.jsonl").exists()


def test_le_sequencia_falha_explicita_se_arquivo_ausente(tmp_path, capsys):
    ausente = tmp_path / "nao_existe.jsonl"

    try:
        main(["--sequencia", str(ausente)])
        assert False, "esperava SystemExit"
    except SystemExit as e:
        assert e.code == 2
    err = capsys.readouterr().err
    assert "não encontrada" in err


def test_ler_sequencia_preserva_ordem_do_arquivo(tmp_path):
    seq_path = tmp_path / "seq.jsonl"
    seq_path.write_text(
        '{"query": "primeira", "id": "e1", "timestamp": 1}\n'
        '{"query": "segunda", "id": "e2", "timestamp": 2}\n',
        encoding="utf-8",
    )

    sequencia = _ler_sequencia(seq_path)

    assert [t["query"] for t in sequencia] == ["primeira", "segunda"]
