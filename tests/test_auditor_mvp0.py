"""
MVP-0 do servico de auditoria.

A propriedade que estes testes protegem nao e "o pipeline roda". E:

    quando uma pre-condicao de validade quebra, NENHUMA metrica existe.

Nao "nao e impressa" — nao e calculada. Cada cenario abaixo e um defeito que
JA ACONTECEU no REL-001; a fixture congela o defeito para que a proxima vez
falhe no pipeline em vez de falhar depois de 492 chamadas de API.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "sujeitos" / "rel"))

from auditor import Auditoria, Protocolo, relatorio          # noqa: E402
from auditor.checks import procedencia as CP, ranking as CR  # noqa: E402
from auditor.checks.base import Resultado                    # noqa: E402
from auditor.estados import AuditoriaBloqueada, Estado, StatusAuditoria  # noqa: E402
from auditor.fixtures import SistemaFalso, SistemaSaudavel, queries      # noqa: E402

# min_unidades=3 porque as fixtures rodam 3 queries; o protocolo REAL do
# REL-001 usa 50. O check em si e exercitado nos testes de estatistica abaixo.
PROT = Protocolo("REL-001", 50, {"topo": 5, "cauda": 3, "controle": 2},
                 (19, 50), 50, min_unidades=3)


def roda(sis):
    return Auditoria(PROT, sis, queries()).roda()


# ── item 8: as tres classes de cenario ──────────────────────────────────────

def test_caso_A_saudavel_completa(tmp_path):
    m = roda(SistemaSaudavel(tmp_path / "a"))
    assert m.status is StatusAuditoria.COMPLETE
    assert m.resultado["recall_at_5"] == 0.62
    assert not m.barreiras


@pytest.mark.parametrize("defeito,check_esperado", [
    ("ordem_de_arquivo",      "ranking.veio_do_retriever"),
    ("score_constante",       "ranking.veio_do_retriever"),
    ("fora_de_ordem",         "ranking.veio_do_retriever"),
    ("duplicacao_de_camada",  "ranking.cardinalidade"),
    ("corpus_pequeno",        "ranking.cardinalidade"),
    ("controle_no_ranking",   "estratos.controle_fora_do_ranking"),
    ("sem_snapshot",          "procedencia.snapshot_tem_hash"),
])
def test_cada_defeito_bloqueia_pelo_check_certo(tmp_path, defeito, check_esperado):
    m = roda(SistemaFalso(tmp_path / defeito, defeito=defeito))
    assert m.status is StatusAuditoria.BLOCKED
    assert check_esperado in [c.nome for c in m.barreiras], \
        f"{defeito} barrou por {[c.nome for c in m.barreiras]}"


# ── a propriedade central: nao existe metrica sob bloqueio ──────────────────

@pytest.mark.parametrize("defeito", [
    "ordem_de_arquivo", "score_constante", "duplicacao_de_camada",
    "corpus_pequeno", "controle_no_ranking", "sem_snapshot",
])
def test_bloqueada_nao_tem_resultado_de_forma_alguma(tmp_path, defeito):
    m = roda(SistemaFalso(tmp_path / defeito, defeito=defeito))

    with pytest.raises(AuditoriaBloqueada):
        m.resultado
    with pytest.raises(AuditoriaBloqueada):
        m.publica_resultado({"recall_at_5": 0.99})

    d = m.to_dict()
    assert d["resultado"] is None
    assert "NAO_HA_RESULTADO" in d
    assert d["status"] == "BLOCKED"


def test_pipeline_para_e_etapas_seguintes_ficam_pending(tmp_path):
    """
    O numero nao deixa de ser impresso — ele nao chega a ser calculado.
    """
    m = roda(SistemaFalso(tmp_path / "x", defeito="corpus_pequeno"))
    est = {e["etapa"]: e["estado"] for e in m.etapas}
    assert est["estatistica"] == "PENDING"
    assert est["julgadores"] == "PENDING"


def test_relatorio_bloqueado_nao_carrega_metrica(tmp_path):
    m = roda(SistemaFalso(tmp_path / "y", defeito="duplicacao_de_camada"))
    md = relatorio.markdown(m)
    assert "Status: BLOCKED" in md
    assert "O que NÃO foi concluído" in md
    assert "recall" not in md.lower() and "kappa" not in md.lower()


def test_auditoria_nao_toca_o_sistema_auditado(tmp_path):
    """
    Auditar nao pode alterar o auditado: `retrieve` incrementa acessos e salva.
    O adaptador do EDP trabalha em copia; aqui garantimos que o arquivo de
    origem nao muda.
    """
    sis = SistemaFalso(tmp_path / "z")
    epi = sis.snapshot_dir / "episodic.json"
    antes = epi.read_bytes()
    roda(sis)
    assert epi.read_bytes() == antes


# ── item 9: regressao de cada defeito ja cometido ───────────────────────────

def test_regressao_artefato_invalido_nao_entra():
    r = CP.artefato_e_auditavel(
        {"INVALIDO": True, "motivo": "ordem de arquivo", "invalidado_em": "2026-08-31"})
    assert r.estado is Estado.INVALID and r.barra


def test_regressao_numero_sem_procedencia_nao_entra():
    r = CP.artefato_e_auditavel({"experimento": "REL-001"})
    assert r.estado is Estado.INVALID
    assert "faltando" in r.evidencia


def test_regressao_none_do_juiz_nunca_vira_zero():
    """
    Converter ilegivel em 0 esconde a taxa de falha do juiz dentro da taxa de
    irrelevancia — e o §11 deixa de conseguir parar a rodada.
    """
    import juiz_llm as J
    assert J.parse_resposta("desculpe, nao consigo") is None
    assert J.parse_resposta("") is None
    assert J.parse_resposta('{"relevant": false}') == 0
    assert J.parse_resposta('{"relevant": true}') == 1


def test_regressao_sem_tema_nao_vira_controle(tmp_path):
    """
    `SEM_TEMA` sao as saudacoes e timestamps. Usa-los como controle negativo
    de outro dominio nao mede dominio, mede vazio.
    """
    from auditor.adaptadores.edp import EDPAuditavel
    d = tmp_path / "sessions" / "default_cognitive"
    d.mkdir(parents=True)
    (d / "episodic.json").write_text(json.dumps(
        [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]), encoding="utf-8")
    (d / "semantic.json").write_text("[]", encoding="utf-8")
    dom = tmp_path / "dom.json"
    dom.write_text(json.dumps({"dominios": {"a": "SEM_TEMA", "b": "postgres"}}),
                   encoding="utf-8")
    sis = EDPAuditavel.__new__(EDPAuditavel)
    sis._dom = {"a": "SEM_TEMA", "b": "postgres"}
    assert sis.controle_para({"dominio": "java"}) == ["b"]


# ── NORTE §4.15 como propriedade do codigo ──────────────────────────────────

def test_check_sem_declarar_o_que_detecta_e_recusado():
    """
    §4.15 vira campo obrigatorio: quem escreve um check diz qual defeito aquele
    numero moveria. Nao saber responder e sinal de que o check nao mede nada.
    """
    with pytest.raises(ValueError, match="4.15"):
        Resultado("x", Estado.PASS, detecta="   ")


def test_todo_check_do_pipeline_declara_o_que_detecta(tmp_path):
    m = roda(SistemaFalso(tmp_path / "w", defeito="corpus_pequeno"))
    assert all(c.detecta.strip() for c in m.checks)


def test_cardinalidade_conta_distintos_e_nao_slots():
    """
    O erro que custou a rodada: 50 slots passam, 30 distintos nao.
    """
    rk = [(f"d{i % 30}", 0.02 - i * 0.0001) for i in range(50)]
    r = CR.cardinalidade(rk, 50)
    assert r.evidencia["slots"] == 50
    assert r.evidencia["ids_distintos"] == 30
    assert r.estado is Estado.BLOCKED


def test_manifesto_tem_hash_e_procedencia(tmp_path):
    m = roda(SistemaSaudavel(tmp_path / "h"))
    d = m.to_dict()
    assert len(d["sha256_manifesto"]) == 64
    assert d["snapshot"]["sha256_episodic"]
    assert d["retriever"]["top_k"] == 50


# ── pre-condicoes estatisticas: metrica calculavel != metrica interpretavel ──

def test_poucos_clusters_bloqueiam_antes_do_calculo(tmp_path):
    """
    500 pares parecem muitos e sao 50 queries. Contar itens nao move; contar
    unidades independentes move.
    """
    prot = Protocolo("REL-001", 50, {"topo": 5, "cauda": 3, "controle": 2},
                     (19, 50), 50, min_unidades=30)
    m = Auditoria(prot, SistemaSaudavel(tmp_path / "p"), queries(3)).roda()
    assert m.status is StatusAuditoria.BLOCKED
    assert "estatistica.unidades_suficientes" in [c.nome for c in m.barreiras]
    with pytest.raises(AuditoriaBloqueada):
        m.resultado


def test_prevalencia_extrema_bloqueia_indice_de_acordo(tmp_path):
    """
    NORTE §4.14: um kappa alto sob prevalencia de 97% mede o desbalanceamento.
    O servico nao publica esse numero.
    """
    sis = SistemaSaudavel(tmp_path / "q")
    sis.rotulos_do_gate = [1] * 97 + [0] * 3
    m = Auditoria(PROT, sis, queries(3)).roda()
    assert m.status is StatusAuditoria.BLOCKED
    assert "estatistica.prevalencia_permite_acordo" in [c.nome for c in m.barreiras]


def test_prevalencia_equilibrada_passa(tmp_path):
    from auditor.checks import estatistica as CS
    r = CS.prevalencia_permite_acordo([1] * 40 + [0] * 60, "gate")
    assert r.estado is Estado.PASS
    assert r.evidencia["prevalencia_positiva"] == 0.4
