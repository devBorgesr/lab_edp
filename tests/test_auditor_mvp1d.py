"""
MVP-1D — integracao e fluxo de cliente.

O criterio: um sistema externo simulado passa por check -> run -> manifesto ->
relatorio, com isolamento por audit_id, sem caminho absoluto e sem depender de
arquivo pessoal do laboratorio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from auditor import jobs as J                                        # noqa: E402
from auditor.cli import EXIT, PROTOCOLOS, main                       # noqa: E402
from auditor.fixtures_cliente import gera_fixtures                   # noqa: E402
from auditor.registro import conhecidos, register_adapter            # noqa: E402
from auditor.servico import executa                                  # noqa: E402


@pytest.fixture(scope="module")
def clientes(tmp_path_factory):
    return gera_fixtures(tmp_path_factory.mktemp("fixtures"))


def roda(cliente: Path, svc: Path, op=None, check=False):
    return executa({"snapshot": str(cliente),
                    "queries": str(cliente / "queries.json"),
                    "protocol": "DIAGNOSTICO", "adapter": "cliente",
                    "options": op or {}}, svc, PROTOCOLOS, so_check=check)


# ── item 4/5: fluxo completo contra sistema externo simulado ────────────────

def test_cliente_normal_completa(clientes, tmp_path):
    r = roda(clientes["customer_a"], tmp_path / "svc")
    assert r["status"] == "COMPLETE" and len(r["medicoes"]) == 5


def test_instrumento_recupera_a_duplicacao_injetada(clientes, tmp_path):
    """
    customer_b nasce com 0,55 de duplicacao, gerado por codigo que nao conhece
    o medidor. Se a medicao nao recuperar isso, ela nao mede o que afirma.
    """
    a = roda(clientes["customer_a"], tmp_path / "sa")
    b = roda(clientes["customer_b"], tmp_path / "sb")

    def val(r, nome):
        return next(m["valor"] for m in r["medicoes"] if m["nome"] == nome)

    assert val(a, "duplicacao_intra_query_por_id") == 0.0
    assert 0.50 <= val(b, "duplicacao_intra_query_por_id") <= 0.60
    assert val(b, "cardinalidade_do_ranking") < val(a, "cardinalidade_do_ranking")


def test_distancia_crua_bloqueia_e_nao_entrega_medicao(clientes, tmp_path):
    """C1 ponta a ponta: score que nao e score nao vira medicao nenhuma."""
    r = roda(clientes["customer_c"], tmp_path / "svc")
    assert r["status"] == "BLOCKED"
    assert "ranking.veio_do_retriever" in r["barreiras"]
    assert r["medicoes"] == [] and r["resultado"] is None


def test_conversao_declarada_destrava(clientes, tmp_path):
    r = roda(clientes["customer_c"], tmp_path / "svc", {"converter_score": True})
    assert r["status"] == "COMPLETE" and len(r["medicoes"]) == 5


def test_servico_nunca_converte_score_sozinho(clientes, tmp_path):
    """Adivinhar a semantica do score do cliente seria inventar dado."""
    sem = roda(clientes["customer_c"], tmp_path / "s1")
    com = roda(clientes["customer_c"], tmp_path / "s2", {"converter_score": True})
    assert sem["status"] == "BLOCKED" and com["status"] == "COMPLETE"


# ── item 1: o job persiste, com identidade completa ─────────────────────────

def test_job_persiste_e_deriva_o_status(clientes, tmp_path):
    svc = tmp_path / "svc"
    r = roda(clientes["customer_b"], svc)
    job = J.Registro(svc).ver(r["audit_id"])
    assert job is not None
    assert job.status == r["status"] == "COMPLETE"
    assert job.protocol == "DIAGNOSTICO" and job.protocol_version == 1
    assert job.adapter == "cliente", "gravou a classe no lugar do adaptador pedido"
    assert job.adapter_class and job.adapter_version
    assert job.snapshot.get("sha256_episodic") and job.dataset.get("sha256_queries")
    assert Path(job.manifest).exists()
    assert set(job.reports) == {"executive", "technical"}


def test_job_bloqueado_nao_diz_complete(clientes, tmp_path):
    svc = tmp_path / "svc"
    r = roda(clientes["customer_c"], svc)
    assert J.Registro(svc).ver(r["audit_id"]).status == "BLOCKED"


def test_idempotencia_sobrevive_a_reinicio(clientes, tmp_path):
    """
    O registro em memoria criaria uma segunda auditoria depois de restart, e o
    cliente pagaria duas vezes por dois manifestos do mesmo sistema.
    """
    svc = tmp_path / "svc"
    r = executa({"snapshot": str(clientes["customer_a"]),
                 "queries": str(clientes["customer_a"] / "queries.json"),
                 "protocol": "DIAGNOSTICO", "adapter": "cliente",
                 "request_id": "req-persistente"}, svc, PROTOCOLOS)
    achado = J.Registro(svc).por_request_id("req-persistente")
    assert achado is not None and achado.audit_id == r["audit_id"]


# ── item 2: CLI e a implementacao de referencia ─────────────────────────────

def test_cli_status_e_report(clientes, tmp_path, capsys):
    svc = str(tmp_path / "svc")
    base = ["--input", str(clientes["customer_b"]),
            "--queries", str(clientes["customer_b"] / "queries.json"),
            "--protocol", "DIAGNOSTICO", "--adaptador", "cliente",
            "--output", svc]
    assert main(["run", *base]) == EXIT["COMPLETE"]
    capsys.readouterr()

    assert main(["status", "--output", svc]) == EXIT["COMPLETE"]
    listagem = capsys.readouterr().out
    assert "DIAGNOSTICO v1" in listagem and "cliente" in listagem

    aid = J.Registro(Path(svc)).lista()[0].audit_id
    assert main(["report", aid, "--output", svc]) == EXIT["COMPLETE"]
    assert "## Status" in capsys.readouterr().out
    assert main(["report", aid, "--tipo", "technical", "--output", svc]) == 0


def test_report_de_auditoria_inexistente_nao_inventa(tmp_path, capsys):
    assert main(["report", "naoexiste", "--output", str(tmp_path)]) == EXIT["INVALID"]


def test_dry_run_nao_tem_relatorio_para_report(clientes, tmp_path, capsys):
    svc = tmp_path / "svc"
    r = roda(clientes["customer_a"], svc, check=True)
    assert main(["report", r["audit_id"], "--output", str(svc)]) == EXIT["BLOCKED"]
    assert "dry-run nao grava" in capsys.readouterr().err


# ── item 12: registro de adaptadores ────────────────────────────────────────

def test_registro_lista_os_adaptadores():
    c = conhecidos()
    assert {"edp", "sintetico", "cliente"} <= set(c)
    assert all(d["versao"] and d["descricao"] for d in c.values())


def test_adaptador_duplicado_e_recusado():
    with pytest.raises(ValueError, match="ja registrado"):
        register_adapter("cliente", lambda e: None)


# ── item 16: sem caminho pessoal, sem dependencia do laboratorio ────────────

def test_fixtures_de_cliente_nao_usam_o_edp():
    """
    O EDP e o nosso sistema. Usa-lo como cliente externo seria medir a
    integracao contra a unica integracao que ja existia.
    """
    t = (RAIZ / "auditor" / "fixtures_cliente.py").read_text(encoding="utf-8")
    assert "import edp" not in t and "EDPAuditavel" not in t


def test_paginas_de_produto_sao_coerentes_com_claims():
    """Se a pagina promete o que o CLAIMS proibe, a pagina esta errada."""
    from auditor import claims
    pag = RAIZ / "docs" / "auditor" / "produto"
    for f in sorted(pag.glob("*.md")):
        txt = f.read_text(encoding="utf-8")
        v = [x for x in claims.verifica(txt, "diagnostico")
             if x["tipo"] != "ressalva_ausente"]
        assert not v, f"{f.name}: {[x['termo'] for x in v]}"


def test_pagina_nao_chama_o_produto_de_auditoria_no_titulo():
    """
    "Auditoria" promete qualidade, conformidade e certificacao. O que a regua
    entrega hoje e diagnostico, e a palavra tem que caber na medicao.
    """
    t = (RAIZ / "docs" / "auditor" / "produto" / "COMO_FUNCIONA.md").read_text()
    assert t.splitlines()[0].strip() == "# Diagnóstico de Retrieval"
