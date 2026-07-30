"""
tests/test_exp018.py — exp018 (promoção tóxica pelo caminho automático): só
lógica pura (o agente não tem `edp`). Cobre T2 (dataset), a parte pura do
harness (`inspeciona_resultado`, guarda de flag) e T4 (veredito §6) via
fixtures sintéticas — nenhum destes toca `edp.consolidation`/`edp.runtime`.
"""
from __future__ import annotations

import pytest

from sujeitos.edp.experimentos.exp018 import (
    condicoes_para_posicao,
    inspeciona_resultado,
    valida_flag,
)
from sujeitos.edp.experimentos.exp018_dataset import (
    CLUSTER_THRESH_ALVO,
    CONDICOES,
    EMBED_DIM,
    build_dataset,
    cosseno_c7,
)
from sujeitos.edp.experimentos.exp018_veredito import calcula_veredito

# ── T2: dataset ───────────────────────────────────────────────────────────────

def test_dataset_contagens_ids_e_classes_por_condicao():
    esperado_n = {"C1": 4, "C2": 4, "C3": 4, "C4": 4, "C5": 2, "C6": 4, "C7": 2}
    todos_ids = []
    for c in CONDICOES:
        ds = build_dataset(c)
        assert len(ds) == esperado_n[c], f"{c}: n={len(ds)}, esperado {esperado_n[c]}"

        ids = [e["id"] for e in ds]
        assert len(set(ids)) == len(ids), f"{c}: ids duplicados dentro da condição"
        todos_ids += ids

        # ids FIXOS: reconstruir a condição de novo dá o MESMO conjunto de ids
        assert [e["id"] for e in build_dataset(c)] == ids

        if c in ("C1", "C2", "C3", "C4", "C6"):
            classes = [e["answer_class"] for e in ds]
            assert classes.count("not_found") == 2, c
            assert classes.count("disqualification") == 2, c
        elif c == "C5":
            for e in ds:
                assert "answer_class" not in e, "C5: chave deve estar AUSENTE, não None"
        elif c == "C7":
            a, b = ds
            assert a["answer_class"] == "not_found"
            assert "answer_class" not in b
            assert a["acessos"] == 2 and b["acessos"] == 2

    assert len(set(todos_ids)) == len(todos_ids), "ids duplicados entre condições diferentes"


def test_textos_distintos_por_condicao():
    c1_textos = {e["text"] for e in build_dataset("C1")}
    c2_textos = {e["text"] for e in build_dataset("C2")}
    assert len(c1_textos) == 4  # os 4 textos de C1 são distintos entre si
    assert c1_textos.isdisjoint(c2_textos)  # C1 e C2 não compartilham texto


def test_cosseno_c7_acima_do_alvo():
    cos = cosseno_c7()
    assert cos > CLUSTER_THRESH_ALVO
    # recalculado a partir dos vetores plantados, não hardcoded — chamar de
    # novo dá o mesmo valor (determinístico)
    assert cos == cosseno_c7()


def test_embeddings_deterministicos_e_dimensao_real():
    ds1 = build_dataset("C1")
    ds2 = build_dataset("C1")
    for e1, e2 in zip(ds1, ds2):
        assert e1["embedding"] == e2["embedding"]
    assert len(ds1[0]["embedding"]) == EMBED_DIM


# ── inspeciona_resultado (parte pura do harness, §9) ─────────────────────────

def test_inspeciona_resultado_conta_promovidas_por_classe():
    dataset = build_dataset("C1")  # 4 tóxicas: 2 not_found + 2 disqualification
    nf_ids = {e["id"] for e in dataset if e["answer_class"] == "not_found"}
    semantic_entries = [dict(e) for e in dataset if e["id"] in nf_ids]

    r = inspeciona_resultado("C1", dataset, semantic_entries)

    assert r["promovidas_total"] == 2
    assert r["promovidas_por_classe"] == {"not_found": 2, "disqualification": 0, "normal": 0}


def test_inspeciona_resultado_c7_distingue_fundiu_de_promovida():
    dataset = build_dataset("C7")
    # forma real de merge_cluster(): dez chaves, SEM answer_class (T1, item c)
    fundida = {"id": "id-novo-do-merge", "merged_from": 2, "acessos": 4}

    # cenário 1: fundiu no episódico E foi promovida (está em semantic também)
    r1 = inspeciona_resultado(
        "C7", dataset, semantic_entries=[dict(fundida)], episodic_entries=[dict(fundida)],
    )
    assert r1["fundiu"] is True
    assert r1["promovida_fundida"] is True
    assert r1["answer_class_presente"] is False

    # cenário 2: fundiu no episódico mas NÃO foi promovida (ausente de semantic)
    # — o caso que classifica_h0 precisa distinguir de "não fundiu" (§6)
    r2 = inspeciona_resultado(
        "C7", dataset, semantic_entries=[], episodic_entries=[dict(fundida)],
    )
    assert r2["fundiu"] is True
    assert r2["promovida_fundida"] is False
    assert r2["answer_class_presente"] is None


# ── guarda de flag (§5) ───────────────────────────────────────────────────────

def test_condicoes_para_posicao_bate_flag_requerida():
    assert set(condicoes_para_posicao(1)) == {"C1", "C3", "C5", "C6", "C7"}
    assert set(condicoes_para_posicao(0)) == {"C2", "C4"}


def test_valida_flag_aborta_quando_posicao_nao_bate(capsys):
    with pytest.raises(SystemExit) as exc:
        valida_flag("C3", posicao_atual=0)  # C3 exige flag=1
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "C3" in err and "EDP_WRITE_PROVENANCE" in err

    valida_flag("C2", posicao_atual=0)  # C2 exige flag=0 — não deve levantar


# ── T4: veredito (§6) — fixtures sintéticas ──────────────────────────────────

def _zero(condicao: str, funcao: str = None) -> dict:
    return {
        "condicao": condicao, "promovidas_total": 0,
        "promovidas_por_classe": {"not_found": 0, "disqualification": 0, "normal": 0},
        "n_semantic_apos": 0,
    }


def _instrumento_valido() -> dict:
    """C5 (ambas) promove >=1, C6 (ambas) promove 0 — instrumento OK."""
    c5 = {
        "condicao": "C5", "promovidas_total": 2,
        "promovidas_por_classe": {"not_found": 0, "disqualification": 0, "normal": 2},
        "n_semantic_apos": 2,
    }
    c6 = _zero("C6")
    return {
        "C5/consolidate": dict(c5), "C5/consolidate_promote_only": dict(c5),
        "C6/consolidate": dict(c6), "C6/consolidate_promote_only": dict(c6),
    }


def test_veredito_h1_confirmada():
    resultados = _instrumento_valido()
    resultados["C1/consolidate"] = {
        "condicao": "C1", "promovidas_total": 4,
        "promovidas_por_classe": {"not_found": 2, "disqualification": 2, "normal": 0},
        "n_semantic_apos": 4,
    }
    resultados["C2/consolidate"] = _zero("C2")
    resultados["C3/consolidate_promote_only"] = _zero("C3")
    resultados["C4/consolidate_promote_only"] = _zero("C4")
    resultados["C7/consolidate"] = {
        **_zero("C7"), "fundiu": True, "merged_from": 2,
        "promovida_fundida": True, "answer_class_presente": True,
    }

    v = calcula_veredito(resultados)

    assert v["veredito"] == "CLASSIFICADO"
    assert v["H1_confirmada"] is True
    assert v["H2_confirmada"] is False
    assert v["H3_confirmada"] is False
    assert v["H0"] is False


def test_veredito_h2_e_h3_confirmadas():
    resultados = _instrumento_valido()
    resultados["C1/consolidate"] = _zero("C1")
    resultados["C2/consolidate"] = _zero("C2")
    resultados["C3/consolidate_promote_only"] = _zero("C3")
    resultados["C4/consolidate_promote_only"] = {
        "condicao": "C4", "promovidas_total": 3,
        "promovidas_por_classe": {"not_found": 2, "disqualification": 1, "normal": 0},
        "n_semantic_apos": 3,
    }
    resultados["C7/consolidate"] = {
        **_zero("C7"), "fundiu": True, "merged_from": 2,
        "promovida_fundida": True, "answer_class_presente": False,
    }

    v = calcula_veredito(resultados)

    assert v["H1_confirmada"] is False
    assert v["H2_confirmada"] is True
    assert v["H3_confirmada"] is True
    assert v["H0"] is False
    # C4 promoveu 2 not_found e 1 disqualification — divergência, achado próprio (§4)
    assert "C4/consolidate_promote_only" in v["divergencia_classes_toxicas"]


def test_veredito_h0():
    resultados = _instrumento_valido()
    resultados["C1/consolidate"] = _zero("C1")
    resultados["C2/consolidate"] = _zero("C2")
    resultados["C3/consolidate_promote_only"] = _zero("C3")
    resultados["C4/consolidate_promote_only"] = _zero("C4")
    resultados["C7/consolidate"] = {
        **_zero("C7"), "fundiu": True, "merged_from": 2,
        "promovida_fundida": False, "answer_class_presente": None,
    }

    v = calcula_veredito(resultados)

    assert v["H1_confirmada"] is False
    assert v["H2_confirmada"] is False
    assert v["H3_confirmada"] is False
    assert v["H0"] is True


def test_veredito_inconclusivo_instrumento_invalido_e_c7_nao_fundiu():
    # cenário A: C6 promoveu (controle− inválido) -> instrumento errado
    resultados_a = _instrumento_valido()
    resultados_a["C6/consolidate"]["promovidas_total"] = 1
    v_a = calcula_veredito(resultados_a)
    assert v_a["veredito"] == "INCONCLUSIVO"
    assert "C6/consolidate" in v_a["motivo"]

    # cenário B: instrumento OK, mas C7 não fundiu
    resultados_b = _instrumento_valido()
    resultados_b["C7/consolidate"] = {
        **_zero("C7"), "fundiu": False, "merged_from": None,
        "promovida_fundida": False, "answer_class_presente": None,
    }
    v_b = calcula_veredito(resultados_b)
    assert v_b["veredito"] == "INCONCLUSIVO"
    assert "fundiu" in v_b["motivo"]
