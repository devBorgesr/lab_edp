"""
O que a invalidacao 01 custou, e o que impede que se repita.

A primeira versao do `congela_pares.py` passou os documentos em ORDEM DE
INSERCAO DO ARQUIVO como se fossem ranking do retriever. Nada reclamou: uma
lista de ids e uma lista de ids. Custou 500 pares e 492 rotulos.

Estes testes existem para que a proxima vez falhe ANTES da rotulagem.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sujeitos" / "rel"))
import rel_001 as R  # noqa: E402


def _ranking_real(n=60):
    """Como o retriever devolve: RRF positivo, nao-crescente, distinto."""
    return [(f"doc{i}", 0.0164 - i * 0.0001) for i in range(n)]


# ── o defeito exato da invalidacao 01 ────────────────────────────────────────

def test_ordem_de_arquivo_e_recusada():
    """Ids nus — o que o congela_pares passava. Nao prova procedencia."""
    with pytest.raises(RuntimeError, match="doc_id, score"):
        R.exige_ranking_do_retriever([f"doc{i}" for i in range(60)])


def test_score_constante_e_recusado():
    """Ordem de arquivo com um numero colado nao vira ranking."""
    with pytest.raises(RuntimeError, match="identicos"):
        R.exige_ranking_do_retriever([(f"doc{i}", 0.5) for i in range(60)])


def test_ordem_embaralhada_e_recusada():
    r = _ranking_real()
    r[3], r[40] = r[40], r[3]
    with pytest.raises(RuntimeError, match="nao-crescentes"):
        R.exige_ranking_do_retriever(r)


def test_score_zero_e_recusado():
    with pytest.raises(RuntimeError, match="nao-positivo"):
        R.exige_ranking_do_retriever([(f"doc{i}", 0.0) for i in range(60)])


def test_ranking_real_passa():
    ids = R.exige_ranking_do_retriever(_ranking_real())
    assert ids[0] == "doc0" and len(ids) == 60


# ── o bloqueio estrutural: <50 distintos falha ALTO, nao silencioso ──────────

def test_menos_de_50_distintos_falha_antes_de_rotular():
    """
    Medido em 31/08: o top-50 colapsa para 29-40 distintos neste corpus. O
    harness precisa PARAR aqui — nunca inventar os que faltam.
    """
    with pytest.raises(RuntimeError, match="50 DISTINTOS"):
        R.monta_pool("q", _ranking_real(40), [f"c{i}" for i in range(20)])


def test_dedup_nao_fabrica_ranking():
    """
    50 slots com 36 distintos sao 36, e 36 < 50 reprova. O dedup impede julgar
    o mesmo documento duas vezes; ele NAO pode virar desculpa para completar o
    ranking com documento inventado.
    """
    rank = [(f"doc{i % 36}", 0.02 - i * 0.0001) for i in range(50)]
    with pytest.raises(RuntimeError, match="50 DISTINTOS"):
        R.monta_pool("q", rank, [f"c{i}" for i in range(20)])


# ── item 1: artefato invalido nao vira dado ─────────────────────────────────

def test_artefato_marcado_invalido_e_recusado(tmp_path):
    p = tmp_path / "pares.json"
    p.write_text(json.dumps({"INVALIDO": True, "invalidado_em": "2026-08-31",
                             "motivo": "m", "documento": "d", "pares": []}),
                 encoding="utf-8")
    with pytest.raises(RuntimeError, match="INVALIDO"):
        R.carrega_pares(p)


def test_artefato_sem_procedencia_e_recusado(tmp_path):
    p = tmp_path / "pares.json"
    p.write_text(json.dumps({"experimento": "REL-001", "pares": []}),
                 encoding="utf-8")
    with pytest.raises(RuntimeError, match="procedencia"):
        R.carrega_pares(p)


def test_artefato_com_procedencia_passa(tmp_path):
    p = tmp_path / "pares.json"
    p.write_text(json.dumps({
        "experimento": "REL-001", "pares": [],
        "procedencia": {"store": "/x", "sha256_episodic": "a",
                        "ranking_origem": "MemoryStore.retrieve", "top_k": 50},
    }), encoding="utf-8")
    assert R.carrega_pares(p)["procedencia"]["ranking_origem"] == "MemoryStore.retrieve"


# ── os artefatos reais desta rodada ─────────────────────────────────────────

@pytest.mark.parametrize("nome", ["pares_congelados.json", "rotulos_llm.json"])
def test_os_artefatos_da_rodada_invalida_seguem_marcados(nome):
    """
    Nao sao apagados (§4.4) — mas nenhum pipeline os aceita. Se a marca sumir,
    este teste cai.
    """
    p = Path("/media/sf_edp_v5_main/data/_rel") / nome
    if not p.exists():
        pytest.skip(f"{nome} ausente nesta maquina")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("INVALIDO") is True, f"{nome} perdeu a marca de invalidacao"
    with pytest.raises(RuntimeError, match="INVALIDO"):
        R.carrega_pares(p)
