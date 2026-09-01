"""
MVP-1 — criterio de aceitacao (item 16).

Um sistema externo precisa conseguir: enviar snapshot, executar, receber READY
ou BLOCKED, obter manifesto e relatorio, reproduzir hashes, e ver exatamente
quais checks passaram.

E OITO ERROS PRECISAM SER IMPOSSIVEIS DE PASSAR EM SILENCIO:

    ranking fabricado · id duplicado · controle contaminado · snapshot sem hash
    artefato invalido · score invalido · procedencia ausente
    metrica calculada sob BLOCKED

Cada um tem teste nomeado abaixo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from auditor import Auditoria, Protocolo, relatorio                  # noqa: E402
from auditor.checks import procedencia as CP                         # noqa: E402
from auditor.cli import EXIT, carrega_queries, main                  # noqa: E402
from auditor.estados import AuditoriaBloqueada, Estado, StatusAuditoria  # noqa: E402
from auditor.fixtures import (ClienteSintetico, SistemaFalso,        # noqa: E402
                              queries_cliente)
from auditor.redacao import Politica                                 # noqa: E402

BASICO = Protocolo("BASICO", 10, {"topo": 5, "cauda": 3, "controle": 2},
                   (5, 10), 10, min_unidades=10)


def cliente(tmp, taxa=0.0, n=60):
    s = ClienteSintetico(tmp, taxa_duplicacao=taxa)
    s.estatistica = lambda: {"cobertura": 0.71}
    return Auditoria(BASICO, s, queries_cliente(n)).roda()


# ── os oito erros que nao podem passar ──────────────────────────────────────

def test_erro_1_ranking_fabricado(tmp_path):
    m = Auditoria(BASICO, SistemaFalso(tmp_path, defeito="ordem_de_arquivo"),
                  queries_cliente(12)).roda()
    assert "ranking.veio_do_retriever" in [c.nome for c in m.barreiras]


def test_erro_2_id_duplicado(tmp_path):
    m = cliente(tmp_path, taxa=0.6)
    assert m.status is StatusAuditoria.BLOCKED
    assert "ranking.cardinalidade" in [c.nome for c in m.barreiras]


def test_erro_3_controle_contaminado(tmp_path):
    m = Auditoria(BASICO, SistemaFalso(tmp_path, defeito="controle_no_ranking"),
                  queries_cliente(12)).roda()
    assert "estratos.controle_fora_do_ranking" in [c.nome for c in m.barreiras]


def test_erro_4_snapshot_sem_hash(tmp_path):
    m = Auditoria(BASICO, SistemaFalso(tmp_path, defeito="sem_snapshot"),
                  queries_cliente(12)).roda()
    assert "procedencia.snapshot_tem_hash" in [c.nome for c in m.barreiras]


def test_erro_5_artefato_invalido():
    r = CP.artefato_e_auditavel({"INVALIDO": True, "motivo": "x"})
    assert r.estado is Estado.INVALID and r.barra


def test_erro_6_score_invalido(tmp_path):
    m = Auditoria(BASICO, SistemaFalso(tmp_path, defeito="score_constante"),
                  queries_cliente(12)).roda()
    assert "ranking.veio_do_retriever" in [c.nome for c in m.barreiras]


def test_erro_7_procedencia_ausente():
    r = CP.artefato_e_auditavel({"experimento": "x"})
    assert r.estado is Estado.INVALID


@pytest.mark.parametrize("taxa", [0.6, 0.9])
def test_erro_8_metrica_sob_blocked_e_impossivel(tmp_path, taxa):
    m = cliente(tmp_path, taxa=taxa)
    assert m.status is StatusAuditoria.BLOCKED
    with pytest.raises(AuditoriaBloqueada):
        m.resultado
    with pytest.raises(AuditoriaBloqueada):
        m.publica_resultado({"recall_at_5": 0.9})
    d = m.to_dict()
    assert d["resultado"] is None and "NAO_HA_RESULTADO" in d
    # o relatorio CITA Recall@K para dizer que nao foi calculado; o que nao
    # pode existir e um VALOR. Checar a string seria checar a grandeza errada.
    assert not any("recall" in x.to_dict()["nome"].lower() for x in m.medicoes)


# ── medicao descritiva: existe sob BLOCKED, mas nao sobre ranking falso ─────

def test_medicoes_existem_sob_blocked(tmp_path):
    """A entrega comercial do MVP-1 nao depende do protocolo ser satisfeito."""
    m = cliente(tmp_path, taxa=0.6)
    assert m.status is StatusAuditoria.BLOCKED
    assert len(m.medicoes) == 5
    for x in m.medicoes:
        d = x.to_dict()
        assert d["o_que_mede"] and d["N"] > 0 and d["unidade"] and d["snapshot"]


def test_medicao_nunca_sai_de_ranking_fabricado(tmp_path):
    m = Auditoria(BASICO, SistemaFalso(tmp_path, defeito="ordem_de_arquivo"),
                  queries_cliente(12)).roda()
    assert m.medicoes == []
    with pytest.raises(AuditoriaBloqueada, match="procedencia"):
        m.publica_medicoes([1, 2, 3])


def test_medicao_nao_e_apresentada_como_qualidade(tmp_path):
    m = cliente(tmp_path, taxa=0.6)
    md = relatorio.executivo(m)
    assert "qualidade das respostas" in md
    assert "NOTA_MEDICOES" in m.to_dict()


# ── privacidade (item 10) ───────────────────────────────────────────────────

def test_query_e_documento_nao_vazam_por_default():
    p = Politica()
    assert p.query("qual a senha do banco?").startswith("<query:")
    assert "senha" not in p.query("qual a senha do banco?")


def test_segredo_removido_mesmo_com_exemplos_em_claro():
    """O operador autoriza mostrar texto do cliente; nao autoriza vazar chave."""
    p = Politica(exemplos_em_claro=True)
    saida = p.documento("use a chave sk-ant-api03-" + "A" * 30)
    assert "sk-ant" not in saida and "REMOVIDO" in saida


def test_varredura_alcanca_campo_aninhado():
    p = Politica()
    limpo = p.sanitiza({"a": [{"b": "ghp_" + "x" * 36}]})
    assert "ghp_" not in json.dumps(limpo)
    assert "GITHUB_TOKEN" in p.relatorio()["segredos_removidos"]


def test_manifesto_de_auditoria_real_nao_carrega_texto(tmp_path):
    m = cliente(tmp_path, taxa=0.6)
    bruto = json.dumps(m.to_dict(), ensure_ascii=False)
    assert "indexacao postgres" not in bruto, "texto de documento vazou"
    assert "como resolver" not in bruto, "texto de query vazou"


# ── custo (item 12) ─────────────────────────────────────────────────────────

def test_custo_registrado_e_nao_estimado_quando_nao_se_sabe(tmp_path):
    m = cliente(tmp_path, taxa=0.6)
    c = m.custos
    assert c["tempo_total_s"] >= 0 and "tempo_por_etapa_s" in c
    # zero seria mentira; None e a resposta honesta
    assert c["custo_modelo_usd"] is None
    assert "custo_nao_estimado_porque" in c


# ── criterio de aceitacao ponta a ponta (item 16) ───────────────────────────

def test_ponta_a_ponta_cliente_externo(tmp_path):
    """
    snapshot -> auditoria -> READY/BLOCKED -> manifesto -> relatorio -> hashes
    -> quais checks passaram.
    """
    sis = ClienteSintetico(tmp_path / "sis")
    q = tmp_path / "q.json"
    q.write_text(json.dumps({"queries": queries_cliente(60)}), encoding="utf-8")

    m = Auditoria(BASICO, sis, carrega_queries(q)).roda()
    d = m.to_dict()

    assert d["status"] in ("COMPLETE", "BLOCKED", "READY")
    assert len(d["sha256_manifesto"]) == 64
    assert d["snapshot"]["sha256_episodic"]
    assert d["checks"] and all(c["detecta"] for c in d["checks"])
    assert {c["nome"] for c in d["checks"] if c["estado"] == "PASS"}
    assert relatorio.executivo(m) and relatorio.markdown(m)


def test_hash_do_manifesto_e_reproduzivel(tmp_path):
    """O cliente precisa poder recalcular o hash e chegar no mesmo numero."""
    m = cliente(tmp_path, taxa=0.6)
    a, b = m.to_dict(), m.to_dict()
    assert a["sha256_manifesto"] == b["sha256_manifesto"]


def test_cli_exit_codes(tmp_path, monkeypatch):
    """0 COMPLETE · 2 BLOCKED · 3 INVALID · 4 erro operacional."""
    assert EXIT == {"COMPLETE": 0, "BLOCKED": 2, "INVALID": 3, "ERRO": 4}
    # erro operacional nao pode virar veredito
    cod = main(["run", "--input", "/nao/existe", "--protocol", "BASICO",
                "--queries", "/nao/existe", "--output", str(tmp_path)])
    assert cod == EXIT["ERRO"]


def test_dry_run_nao_calcula_metrica_de_protocolo(tmp_path, capsys):
    """
    `check` e o comando que teria barrado o REL-001 antes das 492 chamadas.

    ATUALIZADO 01/09: ate esta data ele rodava o pipeline inteiro e so deixava
    de gravar os relatorios — 1,81 s contra 1,74 s do `run`, enquanto a doc
    prometia "sem processar nada". Agora e dry-run de verdade: nao cria
    workspace, nao mede, nao grava. 0,009 s.
    """
    from auditor.cli import EXIT, main

    q = tmp_path / "q.json"
    q.write_text(json.dumps({"queries": queries_cliente(24)}), encoding="utf-8")
    svc = tmp_path / "svc"
    cod = main(["check", "--input", str(tmp_path / "corpus"),
                "--queries", str(q), "--protocol", "BASICO",
                "--adaptador", "sintetico", "--taxa-duplicacao", "0.6",
                "--output", str(svc)])
    assert cod == EXIT["COMPLETE"]
    out = capsys.readouterr().out
    assert "READY" in out
    assert "NAO verificado por este check" in out, \
        "o check precisa dizer o que NAO verificou"
    assert not svc.exists(), "dry-run nao pode criar workspace"
