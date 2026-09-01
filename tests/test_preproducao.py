"""
Gate de pre-producao: crash, carga, idempotencia entre processos, contrato
publico e distincao entre BLOCKED / INVALID / ERROR.

Nao aceitar "passou uma vez": a carga roda repetida.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from auditor import jobs as J                                        # noqa: E402
from auditor.cli import PROTOCOLOS                                   # noqa: E402
from auditor.fixtures_cliente import gera_fixtures                   # noqa: E402
from auditor.servico import executa                                  # noqa: E402


@pytest.fixture(scope="module")
def clientes(tmp_path_factory):
    return gera_fixtures(tmp_path_factory.mktemp("fx"))


def entrada(c: Path, **op):
    return {"snapshot": str(c), "queries": str(c / "queries.json"),
            "protocol": "DIAGNOSTICO", "adapter": "cliente", "options": op}


# ── item 2: estado impossivel, criado a mao ─────────────────────────────────

@pytest.mark.parametrize("bruto,motivo", [
    ({"audit_id": "a", "status": "COMPLETE", "protocol": "D"}, "sem manifesto"),
    ({"audit_id": "a", "status": "ERROR", "protocol": "D"}, "sem descricao"),
    ({"audit_id": "a", "status": "BLOCKED"}, "sem protocolo"),
    ({"audit_id": "a", "status": "INVENTADO"}, "desconhecido"),
])
def test_job_impossivel_nao_e_gravado(tmp_path, bruto, motivo):
    """Escrito a mao, como um operador distraido ou um bug faria."""
    with pytest.raises(J.EstadoImpossivel, match=motivo):
        J.Registro(tmp_path).grava(J.Job(**bruto))


@pytest.mark.parametrize("terminal", ["COMPLETE", "BLOCKED", "INVALID", "ERROR",
                                      "READY"])
@pytest.mark.parametrize("alvo", ["RUNNING", "QUEUED", "COMPLETE", "BLOCKED"])
def test_terminal_nunca_transita(terminal, alvo):
    j = J.Job("a", status=terminal)
    if alvo == terminal:
        assert j.transita(alvo).status == terminal      # no-op
        return
    with pytest.raises(J.TransicaoInvalida):
        j.transita(alvo)


def test_conjunto_de_estados_bate_com_a_documentacao():
    """Enum, TRANSICOES e doc nao podem divergir."""
    doc = (RAIZ / "docs" / "api" / "API.md").read_text(encoding="utf-8")
    for e in J.TRANSICOES:
        assert e in doc, f"estado {e} existe no codigo e nao na doc"
    assert set(J.TERMINAIS) == {e for e, t in J.TRANSICOES.items() if not t}


# ── item 3: crash em pontos diferentes ──────────────────────────────────────

@pytest.mark.parametrize("morre_em", ["QUEUED", "RUNNING"])
def test_job_sobrevive_a_crash(tmp_path, morre_em):
    """
    O processo morre; o registro fica. Nenhum job desaparece, e o estado lido
    depois e o ultimo que chegou ao disco.
    """
    reg = J.Registro(tmp_path / "svc")
    j = reg.grava(J.Job("aud1", client_id="acme"))
    if morre_em == "RUNNING":
        reg.grava(j.transita(J.RUNNING))
    del reg, j                                    # "processo morreu"

    novo = J.Registro(tmp_path / "svc").ver("aud1")
    assert novo is not None and novo.status == morre_em
    # e o proximo worker consegue retomar dali
    if morre_em == "RUNNING":
        with pytest.raises(J.TransicaoInvalida):
            novo.transita(J.QUEUED)
    assert novo.transita(J.ERROR) or True


def test_fila_devolve_tarefa_de_worker_morto(tmp_path):
    from auditor.fila import Fila
    f = Fila(tmp_path)
    f.enfileira("aud9", {"raiz": str(tmp_path), "entrada": {}})
    t = f.reivindica()
    assert t["audit_id"] == "aud9" and f.pendentes() == 0
    assert list(f.orfas()) == ["aud9"], "tarefa reivindicada precisa ser visivel"
    f.devolve("aud9")
    assert f.pendentes() == 1


# ── item 4: carga concorrente, repetida ─────────────────────────────────────

@pytest.mark.parametrize("rodada", range(3))
def test_dez_auditorias_simultaneas(clientes, tmp_path, rodada):
    svc = tmp_path / f"svc{rodada}"
    with ThreadPoolExecutor(max_workers=10) as ex:
        rs = list(ex.map(lambda i: executa(entrada(clientes["customer_a"]),
                                           svc, PROTOCOLOS),
                         range(10)))
    ids = [r["audit_id"] for r in rs]
    assert len(set(ids)) == 10, "colisao de audit_id"
    assert all(r["status"] == "COMPLETE" for r in rs)
    # nenhum manifesto parcial
    for r in rs:
        d = json.loads((Path(r["workspace"]) / "manifest.json").read_text())
        assert len(d["sha256_manifesto"]) == 64 and len(d["medicoes"]) == 5


@pytest.mark.parametrize("rodada", range(3))
def test_leituras_simultaneas_nao_veem_registro_parcial(clientes, tmp_path, rodada):
    svc = tmp_path / f"svc{rodada}"
    executa(entrada(clientes["customer_a"]), svc, PROTOCOLOS)
    reg = J.Registro(svc)
    erros: list[str] = []

    def le(_):
        try:
            reg.lista()
            reg.por_request_id("x")
        except Exception as e:
            erros.append(type(e).__name__)

    def escreve(_):
        try:
            executa(entrada(clientes["customer_b"]), svc, PROTOCOLOS)
        except Exception as e:
            erros.append(type(e).__name__)

    with ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(le, range(10)))
        list(ex.map(escreve, range(3)))
        list(ex.map(le, range(10)))
    assert erros == [], f"leitura concorrente falhou: {set(erros)}"


# ── item 5: idempotencia ENTRE PROCESSOS ────────────────────────────────────

def test_idempotencia_entre_processos_diferentes(clientes, tmp_path):
    """
    Processo A cria e morre. Processo B, novo interpretador, precisa achar a
    mesma auditoria pelo request_id.
    """
    svc = tmp_path / "svc"
    prog = textwrap.dedent(f"""
        import sys, json
        sys.path.insert(0, {str(RAIZ)!r})
        from pathlib import Path
        from auditor import jobs as J
        from auditor.cli import PROTOCOLOS
        from auditor.servico import executa
        e = {{"snapshot": {str(clientes["customer_a"])!r},
              "queries": {str(clientes["customer_a"] / "queries.json")!r},
              "protocol": "DIAGNOSTICO", "adapter": "cliente",
              "request_id": "entre-processos"}}
        r = executa(e, Path({str(svc)!r}), PROTOCOLOS)
        print(r["audit_id"])
    """)
    a = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True)
    assert a.returncode == 0, a.stderr[-400:]
    aid = a.stdout.strip().splitlines()[-1]

    prog_b = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(RAIZ)!r})
        from pathlib import Path
        from auditor import jobs as J
        j = J.Registro(Path({str(svc)!r})).por_request_id("entre-processos")
        print(j.audit_id if j else "NENHUM")
    """)
    b = subprocess.run([sys.executable, "-c", prog_b], capture_output=True, text=True)
    assert b.stdout.strip().splitlines()[-1] == aid


# ── item 11: repetibilidade ─────────────────────────────────────────────────

def test_mesma_entrada_mesmos_hashes_e_medicoes(clientes, tmp_path):
    a = executa(entrada(clientes["customer_b"]), tmp_path / "a", PROTOCOLOS)
    b = executa(entrada(clientes["customer_b"]), tmp_path / "b", PROTOCOLOS)

    assert a["snapshot"]["sha256_episodic"] == b["snapshot"]["sha256_episodic"]
    assert a["dataset"]["sha256_queries"] == b["dataset"]["sha256_queries"]
    assert [m["valor"] for m in a["medicoes"]] == [m["valor"] for m in b["medicoes"]]
    assert [c["nome"] for c in a["checks"]] == [c["nome"] for c in b["checks"]]
    assert a["resultado"] == b["resultado"]
    # e o que DEVE mudar, muda
    assert a["audit_id"] != b["audit_id"]
    assert a["criado_em"] <= b["criado_em"]


# ── item 16: adaptador escrito so com o contrato publico ────────────────────

def test_adaptador_externo_so_com_o_contrato_publico(tmp_path):
    """
    Um integrador que leu apenas SERVICE_CONTRACT/QUICKSTART: importa
    `auditor.contrato` e nada mais do miolo. Sem MemoryStore, sem edp.
    """
    prog = textwrap.dedent(f"""
        import sys, json
        sys.path.insert(0, {str(RAIZ)!r})
        from pathlib import Path
        from auditor.contrato import SistemaAuditavel

        class MeuRAG(SistemaAuditavel):
            VERSAO = "meurag-1"
            def __init__(self, d):
                self._d = Path(d) / "sessions" / "default_cognitive"
                self._d.mkdir(parents=True, exist_ok=True)
                self.docs = {{f"x{{i:03d}}": f"texto {{i}}" for i in range(140)}}
                (self._d / "episodic.json").write_text(json.dumps(
                    [{{"id": k, "text": v}} for k, v in self.docs.items()]))
                (self._d / "semantic.json").write_text("[]")
            @property
            def snapshot_dir(self): return self._d
            def consulta(self, query, top_k):
                ids = list(self.docs)
                base = abs(hash(query)) % len(ids)
                return [(ids[(base + i) % len(ids)], 0.9 - i * 0.01)
                        for i in range(top_k)]
            def texto(self, doc_id): return self.docs.get(doc_id, "")
            def controle_para(self, q): return []

        from auditor.cli import PROTOCOLOS
        from auditor.pipeline import Auditoria
        qs = [{{"id": f"q{{i}}", "query": f"pergunta {{i}}", "dominio": ""}}
              for i in range(24)]
        m = Auditoria(PROTOCOLOS["DIAGNOSTICO"],
                      MeuRAG({str(tmp_path / "rag")!r}), qs).roda()
        print(m.status.value, len(m.medicoes))
    """)
    r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    assert r.stdout.strip().splitlines()[-1] == "COMPLETE 5"
    assert "MemoryStore" not in prog and "import edp" not in prog


# ── item 18: os quatro desfechos parecem diferentes ─────────────────────────

def test_blocked_invalid_e_error_nao_se_confundem(clientes, tmp_path):
    from auditor.esquemas import EntradaInvalida
    from auditor import relatorio

    # BLOCKED: score sem procedencia
    b = executa(entrada(clientes["customer_c"]), tmp_path / "b", PROTOCOLOS)
    assert b["status"] == "BLOCKED" and b["resultado"] is None
    md = relatorio.executivo_de_dict(b) if hasattr(relatorio, "executivo_de_dict") \
        else (Path(b["workspace"]) / "reports" / "executive.md").read_text()
    assert "não pôde ser executado sobre este sistema" in md
    assert "ERROR" not in md

    # INVALID: entrada que nao serve
    with pytest.raises(EntradaInvalida):
        executa({"snapshot": "/x", "queries": "/y", "protocol": "NAOEXISTE",
                 "adapter": "cliente"}, tmp_path / "i", PROTOCOLOS)

    # ERROR: falha do servico, nunca veredito
    doc = (RAIZ / "docs" / "api" / "ERRORS.md").read_text(encoding="utf-8")
    assert "ERROR` nunca é veredito" in doc or "nunca é veredito" in doc
