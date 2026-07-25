"""
tests/test_auditoria.py — FASE B4: fixture sintetica unica com 10 queries,
cobrindo as 4 patologias que bancada.auditoria detecta:
  Q1, Q2   — duplicata por ID
  Q3, Q4   — duplicata por hash de texto normalizado (SEM id)
  Q5, Q6   — overlap alto cross-query (par consecutivo)
  Q7..Q10  — escala de score esmagada

Valores esperados calculados a mao (ver derivacao no commit da FASE B4).
"""
from __future__ import annotations

import json

import pytest

from bancada.auditoria import (
    analyze_cross_query_repetition,
    analyze_intra_query_duplication,
    analyze_score_scale,
    build_report,
    gerar_relatorio,
    main,
    parse_jsonl,
)


def _rec(query: str, results: list) -> dict:
    return {"query": query, "results": results}


FIXTURE = [
    # Q1, Q2 — duplicata por ID (mesmo id, textos diferentes)
    _rec("q1", [
        {"id": "a1", "texto": "Texto A", "score": 0.9},
        {"id": "a1", "texto": "Texto B diferente", "score": 0.5},
        {"id": "a2", "texto": "Texto C", "score": 0.4},
    ]),
    _rec("q2", [
        {"id": "b1", "texto": "X", "score": 0.9},
        {"id": "b1", "texto": "Y", "score": 0.8},
        {"id": "b2", "texto": "Z", "score": 0.7},
        {"id": "b3", "texto": "W", "score": 0.6},
    ]),
    # Q3, Q4 — duplicata por hash de texto normalizado, SEM id
    _rec("q3", [
        {"id": None, "texto": "Gato preto", "score": 0.9},
        {"id": None, "texto": "  GATO   preto  ", "score": 0.85},
        {"id": None, "texto": "Cachorro", "score": 0.7},
    ]),
    _rec("q4", [
        {"id": None, "texto": "Chuva forte hoje", "score": 0.6},
        {"id": None, "texto": "chuva   forte HOJE", "score": 0.55},
        {"id": None, "texto": "Sol brilhante", "score": 0.5},
        {"id": None, "texto": "Vento fraco", "score": 0.4},
    ]),
    # Q5, Q6 — overlap alto cross-query (par consecutivo: p1,p2 em comum)
    _rec("q5", [
        {"id": "p1", "texto": "Doc 1", "score": 0.9},
        {"id": "p2", "texto": "Doc 2", "score": 0.8},
        {"id": "p3", "texto": "Doc 3", "score": 0.7},
    ]),
    _rec("q6", [
        {"id": "p1", "texto": "Doc 1", "score": 0.85},
        {"id": "p2", "texto": "Doc 2", "score": 0.75},
        {"id": "p4", "texto": "Doc 4", "score": 0.65},
    ]),
    # Q7..Q10 — escala de score esmagada (scores identicos/quase identicos)
    _rec("q7", [
        {"id": "e1", "texto": "E um", "score": 0.5},
        {"id": "e2", "texto": "E dois", "score": 0.5},
        {"id": "e3", "texto": "E tres", "score": 0.5},
        {"id": "e4", "texto": "E quatro", "score": 0.5},
    ]),
    _rec("q8", [
        {"id": "f1", "texto": "F um", "score": 0.5},
        {"id": "f2", "texto": "F dois", "score": 0.5},
        {"id": "f3", "texto": "F tres", "score": 0.5},
    ]),
    _rec("q9", [
        {"id": "g1", "texto": "G um", "score": 0.5},
        {"id": "g2", "texto": "G dois", "score": 0.5},
    ]),
    _rec("q10", [
        {"id": "h1", "texto": "H um", "score": 0.5},
        {"id": "h2", "texto": "H dois", "score": 0.5},
        {"id": "h3", "texto": "H tres", "score": 0.5},
        {"id": "h4", "texto": "H quatro", "score": 0.5},
        {"id": "h5", "texto": "H cinco", "score": 0.5},
    ]),
]


def _write_fixture(tmp_path) -> str:
    p = tmp_path / "export.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for r in FIXTURE:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return str(p)


# ── duplicata por ID (Q1, Q2) ────────────────────────────────────────────────

def test_dup_por_id():
    dup = analyze_intra_query_duplication(FIXTURE, top_k=None)
    row_q1 = dup["rows"][0]
    row_q2 = dup["rows"][1]
    assert row_q1["dup_id_count"] == 1
    assert row_q1["dup_id_rate"] == pytest.approx(1 / 3)
    assert row_q2["dup_id_count"] == 1
    assert row_q2["dup_id_rate"] == pytest.approx(0.25)
    assert dup["worst_id"]["query"] == "q1"
    assert dup["avg_dup_id_rate"] == pytest.approx((1 / 3 + 0.25) / 8)


# ── duplicata por hash, SEM id (Q3, Q4) ──────────────────────────────────────

def test_dup_por_hash_sem_id():
    dup = analyze_intra_query_duplication(FIXTURE, top_k=None)
    row_q3 = dup["rows"][2]
    row_q4 = dup["rows"][3]
    assert row_q3["dup_hash_count"] == 1
    assert row_q3["dup_hash_rate"] == pytest.approx(1 / 3)
    assert row_q3["dup_id_rate"] is None       # sem id -> omitido, nao 0.0
    assert row_q4["dup_hash_count"] == 1
    assert row_q4["dup_hash_rate"] == pytest.approx(0.25)
    assert dup["n_queries_sem_id"] == 2
    assert dup["worst_hash"]["query"] == "q3"
    assert dup["avg_dup_hash_rate"] == pytest.approx((1 / 3 + 0.25) / 10)


# ── overlap alto cross-query (Q5, Q6 consecutivas) ───────────────────────────

def test_overlap_alto_cross_query():
    rep = analyze_cross_query_repetition(FIXTURE, top_k=None)
    par_q5_q6 = rep["consecutive"][4]   # (Q5,Q6): indice 4 dos 9 pares consecutivos
    assert par_q5_q6["overlap"] == 2
    assert par_q5_q6["frac"] == pytest.approx(2 / 3)
    assert par_q5_q6["binary"] is True

    # unico par nao-zero entre os 9 consecutivos -> agregados = (Q5,Q6)/9
    assert rep["cons_binary_rate"] == pytest.approx(1 / 9)
    assert rep["cons_continuous_mean"] == pytest.approx((2 / 3) / 9)

    # matriz completa: 45 pares (C(10,2)), so (Q5,Q6) tem overlap
    assert rep["total_pairs"] == 45
    assert rep["ref_binary_rate"] == pytest.approx(1 / 45)
    assert rep["ref_continuous_mean"] == pytest.approx((2 / 3) / 45)


# ── escala esmagada (Q7..Q10) ─────────────────────────────────────────────────

def test_escala_esmagada():
    scale = analyze_score_scale(FIXTURE, top_k=None)
    # Q7: 4 scores iguais -> 3/3 pares empatados; Q8: 3 iguais -> 2/2;
    # Q9: 2 iguais -> 1/1; Q10: 5 iguais -> 4/4. Q1..Q6 nao tem empates.
    assert scale["tie_fraction"] == pytest.approx(10 / 24)
    assert scale["flagged"] is True
    # Q3 e Q5 tem o mesmo spread minimo (2/9) entre as nao-esmagadas;
    # mediana das 10 (4 zeros + 6 nao-zero, ordenadas) cai exatamente em 2/9.
    assert scale["median_spread"] == pytest.approx(2 / 9)


# ── relatorio ponta-a-ponta: determinismo + secoes presentes ────────────────

def test_relatorio_determinismo_e_secoes(tmp_path):
    path = _write_fixture(tmp_path)
    r1 = gerar_relatorio(path, top_k=None)
    r2 = gerar_relatorio(path, top_k=None)
    assert r1 == r2   # mesma entrada -> mesma saida, sempre
    assert "Sumário executivo" in r1 or "Sumario executivo" in r1
    assert "Escala esmagada" in r1 or "escala esmagada" in r1.lower()
    assert "Limitações deste diagnóstico" in r1 or "Limitacoes deste diagnostico" in r1


def test_cli_imprime_no_stdout(tmp_path, capsys):
    path = _write_fixture(tmp_path)
    rc = main([path])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Relatorio de Auditoria de Retrieval" in out or "Relatório de Auditoria de Retrieval" in out


# ── robustez: linhas malformadas nunca abortam a auditoria ──────────────────

def test_linhas_malformadas_sao_puladas_nao_abortam(tmp_path):
    p = tmp_path / "export_malformado.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"query": "ok", "results": [{"texto": "t"}]}) + "\n")
        f.write("{not valid json\n")
        f.write(json.dumps({"results": [{"texto": "sem query"}]}) + "\n")
        f.write(json.dumps({"query": "results nao lista", "results": "oops"}) + "\n")

    parsed = parse_jsonl(str(p))
    assert parsed.n_malformed_lines == 3
    assert len(parsed.records) == 1
    assert parsed.records[0]["query"] == "ok"

    # nao abortar: build_report ainda produz markdown, mesmo com so 1 query valida.
    dup = analyze_intra_query_duplication(parsed.records, top_k=None)
    rep = analyze_cross_query_repetition(parsed.records, top_k=None)
    scale = analyze_score_scale(parsed.records, top_k=None)
    report = build_report(parsed, dup, rep, scale, top_k=None)
    assert "3 linha" in report
