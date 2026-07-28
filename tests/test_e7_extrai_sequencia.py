"""
tests/test_e7_extrai_sequencia.py — E7 Passo 1 (§4): regressão do extrator de
sequência. Fixture sintética com entries mistas (session_summary, texto sem
formato Q:/A:, turnos válidos), fora de ordem cronológica de propósito, para
provar que a regra congelada (ordena → exclui summary → exclui não-forma →
extrai query) é aplicada na ordem certa e produz contagem exata.
"""
from __future__ import annotations

import json

from sujeitos.edp.experimentos.e7_extrai_sequencia import (
    MIN_TURNOS,
    _load_entries,
    constroi_sequencia,
    extrai_query,
    grava_jsonl,
    main,
)

# 7 entries fora de ordem cronológica: 2 session_summary, 1 sem formato Q:/A:,
# 4 turnos válidos (um deles com quebra de linha dentro da pergunta).
FIXTURE_MISTA = [
    {"id": "e5", "timestamp": 500, "text": "Q: pergunta final? A: resposta final."},
    {"id": "e1", "timestamp": 100, "text": "Q: primeira pergunta? A: primeira resposta."},
    {"id": "s1", "timestamp": 200, "text": "[session_summary] resumo da sessão"},
    {"id": "e3", "timestamp": 300, "text": "Isso não é formato Q/A."},
    {"id": "e2", "timestamp": 150, "text": "Q: segunda pergunta? A: segunda resposta."},
    {"id": "s2", "timestamp": 50, "text": "[session_summary] outro resumo antigo"},
    {"id": "e4", "timestamp": 400, "text": "Q: com quebra\nde linha? A: ok, resposta."},
]


def test_ordena_por_timestamp_e_conta_exclusoes_exatas():
    res = constroi_sequencia(FIXTURE_MISTA)

    assert res["n_total"] == 7
    assert res["n_excluido_summary"] == 2
    assert res["n_excluido_forma"] == 1
    assert res["n_final"] == 4

    # ordem cronológica (por timestamp), não ordem de inserção na fixture
    ids_finais = [row["id"] for row in res["sequencia"]]
    assert ids_finais == ["e1", "e2", "e4", "e5"]
    assert [row["query"] for row in res["sequencia"]] == [
        "primeira pergunta?",
        "segunda pergunta?",
        "com quebra\nde linha?",
        "pergunta final?",
    ]


def test_extrai_query_pega_trecho_ate_o_primeiro_A():
    assert extrai_query("Q: horas da reunião? A: 14h30.") == "horas da reunião?"
    # DOTALL: pergunta com quebra de linha ainda é capturada inteira
    assert extrai_query("Q: linha um\nlinha dois? A: tudo bem.") == "linha um\nlinha dois?"
    # texto sem "A:" não tem query extraível
    assert extrai_query("Q: pergunta sem resposta nenhuma") is None


def test_grava_jsonl_sha_estavel_entre_duas_execucoes(tmp_path):
    res = constroi_sequencia(FIXTURE_MISTA)
    p1 = tmp_path / "run1.jsonl"
    p2 = tmp_path / "run2.jsonl"

    sha1 = grava_jsonl(res["sequencia"], p1)
    sha2 = grava_jsonl(res["sequencia"], p2)

    assert sha1 == sha2
    # conteúdo de fato bate linha a linha (mesma ordem, mesmo JSON)
    assert p1.read_text(encoding="utf-8") == p2.read_text(encoding="utf-8")
    assert len(p1.read_text(encoding="utf-8").splitlines()) == res["n_final"]


def _monta_store(tmp_path, entries, session_id="default", scope="cognitive"):
    sess_dir = tmp_path / "sessions" / f"{session_id}_{scope}"
    sess_dir.mkdir(parents=True)
    (sess_dir / "episodic.json").write_text(
        json.dumps(entries, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def test_veredito_prossegue_quando_n_final_atinge_o_minimo(tmp_path, monkeypatch, capsys):
    entries = [
        {"id": f"e{i}", "timestamp": i, "text": f"Q: pergunta {i}? A: resposta {i}."}
        for i in range(MIN_TURNOS)
    ]
    base = _monta_store(tmp_path, entries)
    monkeypatch.setenv("EDP_BASE_DIR", str(base))
    monkeypatch.chdir(tmp_path)

    rc = main(["--out", "saida.jsonl"])
    out = capsys.readouterr().out

    assert rc == 0
    assert f"n_final            : {MIN_TURNOS}" in out
    assert "PROSSEGUIR" in out
    assert "PARAR" not in out
    assert (tmp_path / "saida.jsonl").exists()


def test_veredito_para_quando_n_final_fica_abaixo_do_minimo(tmp_path, monkeypatch, capsys):
    entries = [
        {"id": f"e{i}", "timestamp": i, "text": f"Q: pergunta {i}? A: resposta {i}."}
        for i in range(MIN_TURNOS - 1)
    ]
    base = _monta_store(tmp_path, entries)
    monkeypatch.setenv("EDP_BASE_DIR", str(base))
    monkeypatch.chdir(tmp_path)

    rc = main(["--out", "saida.jsonl"])
    out = capsys.readouterr().out

    assert rc == 0
    assert f"n_final            : {MIN_TURNOS - 1}" in out
    assert "PARAR (poder insuficiente" in out


def test_load_entries_aceita_dict_com_chave_entries(tmp_path):
    """Formato real do EDP varia entre lista pura e {"entries": [...]} (mesma
    robustez de measure_ss_dominance.py._load_entries / adaptador.py)."""
    p = tmp_path / "episodic.json"
    p.write_text(json.dumps({"entries": FIXTURE_MISTA[:2]}), encoding="utf-8")

    entries = _load_entries(p)

    assert entries == FIXTURE_MISTA[:2]
