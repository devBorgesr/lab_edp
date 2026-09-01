"""
Gate de pre-producao: o servico recebe material de terceiros.

Estes testes atacam o proprio servico. Nao verificam que ele funciona —
verificam que ele NAO faz o que nao deve, mesmo quando alguem tenta.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from auditor import jobs as J                                        # noqa: E402
from auditor.cli import PROTOCOLOS                                   # noqa: E402
from auditor.fixtures_cliente import gera_fixtures                   # noqa: E402
from auditor.redacao import Politica, varre_segredos                 # noqa: E402
from auditor.servico import executa, verifica_integracao             # noqa: E402
from auditor.tenancy import NaoAutorizado, raiz_do_cliente           # noqa: E402
from auditor.workspace import ForaDoWorkspace, Workspace             # noqa: E402


@pytest.fixture(scope="module")
def clientes(tmp_path_factory):
    return gera_fixtures(tmp_path_factory.mktemp("fx"))


# ── item 6/7: travessia de caminho e symlink ────────────────────────────────

@pytest.mark.parametrize("cid", [
    "../outro", "..", "a/../../b", "/etc", "a\\b", "%2e%2e", "a b",
    "cliente;rm", "", ".",
])
def test_client_id_hostil_e_recusado(tmp_path, cid):
    """
    O isolamento e por CAMINHO: um client_id que escapa transforma isolamento
    em travessia. A defesa e recusar o id, nao normalizar depois.
    """
    with pytest.raises(NaoAutorizado):
        raiz_do_cliente(tmp_path, cid)


@pytest.mark.parametrize("nome", [
    "../../fuga.json", "../../../etc/passwd", "/etc/passwd",
    "sub/../../../fora.md",
])
def test_escrita_fora_da_raiz_e_recusada(tmp_path, nome):
    w = Workspace.cria(tmp_path / "svc", "aud1")
    with pytest.raises(ForaDoWorkspace):
        w.caminho("reports", nome)


def test_symlink_nao_leva_para_fora(tmp_path):
    """
    `caminho()` resolve o alvo antes de comparar. Um symlink plantado dentro do
    workspace nao pode virar escrita fora dele.
    """
    fora = tmp_path / "fora"; fora.mkdir()
    w = Workspace.cria(tmp_path / "svc", "aud2")
    (w.raiz / "reports" / "escape").symlink_to(fora, target_is_directory=True)
    with pytest.raises(ForaDoWorkspace):
        w.caminho("reports", "escape/vazamento.md")


def test_workspace_recusa_reaproveitar_area_de_outra_auditoria(tmp_path):
    Workspace.cria(tmp_path / "svc", "aud3")
    with pytest.raises(ForaDoWorkspace):
        Workspace.cria(tmp_path / "svc", "aud3")


# ── item 8: caminho local nao vaza para o cliente ───────────────────────────

def test_artefatos_nao_vazam_caminho_do_laboratorio(clientes, tmp_path):
    """
    O cliente recebe manifesto e relatorio. Nenhum deles pode carregar
    /home/<alguem>, /media/<share> ou o caminho do laboratorio.
    """
    r = executa({"snapshot": str(clientes["customer_b"]),
                 "queries": str(clientes["customer_b"] / "queries.json"),
                 "protocol": "DIAGNOSTICO", "adapter": "cliente"},
                tmp_path / "svc", PROTOCOLOS)
    w = Path(r["workspace"])
    proibido = ("/home/", "/media/sf_", "edp_data_todo", "sf_lab_edp_novo")
    for arq in ("manifest.json", "job.json",
                "reports/executive.md", "reports/technical.md",
                "artifacts/checks.json"):
        p = w / arq
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        for pr in proibido:
            assert pr not in txt, f"{arq} vaza caminho do laboratorio: {pr}"


# ── item 9: segredo nao sobrevive em lugar nenhum ───────────────────────────

SEGREDOS = {
    "ANTHROPIC_KEY": "sk-ant-api03-" + "A" * 40,
    "JWT": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefgh",
    "PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----",
    "EMAIL": "fulano.silva@empresa.com.br",
    "CPF": "123.456.789-00",
    "GITHUB_TOKEN": "ghp_" + "x" * 36,
    "AWS_KEY": "AKIAIOSFODNN7EXAMPLE",
}


def test_segredo_em_query_e_em_documento_nao_chega_ao_artefato(tmp_path):
    """Fixture com segredo em TODO campo que o cliente controla."""
    from auditor.adaptadores.referencia import AdaptadorDeReferencia

    corpus = {f"d{i:03d}": f"documento {i} contendo {v}"
              for i, v in enumerate(SEGREDOS.values())}
    corpus.update({f"n{i:03d}": f"documento comum {i}" for i in range(120)})
    ids = list(corpus)
    sis = AdaptadorDeReferencia(
        corpus, lambda q, k: [(ids[(hash(q) + i) % len(ids)], 0.9 - i * 0.01)
                              for i in range(k)])
    qs = [{"id": f"q{i}", "query": f"pergunta com {v}", "dominio": ""}
          for i, v in enumerate(SEGREDOS.values())]
    qs += [{"id": f"n{i}", "query": f"pergunta comum {i}", "dominio": ""}
           for i in range(20)]

    from auditor.pipeline import Auditoria
    m = Auditoria(PROTOCOLOS["DIAGNOSTICO"], sis, qs).roda()
    d = m.salva(tmp_path / "manifest.json", politica=Politica())

    bruto = (tmp_path / "manifest.json").read_text(encoding="utf-8")
    for rot, seg in SEGREDOS.items():
        assert seg not in bruto, f"{rot} vazou no manifesto"
    assert varre_segredos(bruto) == []


def test_gravacao_falha_se_segredo_escapar(tmp_path):
    """A barreira e ANTES de persistir, e falha alto — vazar e irreversivel."""
    from auditor.manifest import Manifesto

    class Cega(Politica):
        def sanitiza(self, obj):
            return obj

    m = Manifesto("x", "P")
    m.configuracao = {"nota": SEGREDOS["ANTHROPIC_KEY"]}
    with pytest.raises(RuntimeError, match="segredo sobreviveu"):
        m.salva(tmp_path / "m.json", politica=Cega())


# ── item 17: `check` e dry-run de verdade ───────────────────────────────────

def test_check_nao_copia_corpus_nem_mede_nem_grava(clientes, tmp_path):
    """
    O `check` anterior rodava o pipeline inteiro e so deixava de gravar os dois
    relatorios — enquanto a doc prometia "sem processar nada". Medido: 1,81 s
    contra 1,74 s do run.
    """
    antes_disco = {p for p in tmp_path.rglob("*")}
    r = verifica_integracao(
        {"snapshot": str(clientes["customer_a"]),
         "queries": str(clientes["customer_a"] / "queries.json"),
         "protocol": "DIAGNOSTICO", "adapter": "cliente"}, PROTOCOLOS)
    assert r["status"] == "READY"
    assert "medicoes" not in r and "resultado" not in r
    assert r["NAO_VERIFICADO"], "o check precisa dizer o que NAO verificou"
    assert {p for p in tmp_path.rglob("*")} == antes_disco


def test_check_e_ordens_de_grandeza_mais_barato(clientes, tmp_path):
    import time
    e = {"snapshot": str(clientes["customer_a"]),
         "queries": str(clientes["customer_a"] / "queries.json"),
         "protocol": "DIAGNOSTICO", "adapter": "cliente"}
    t0 = time.perf_counter(); verifica_integracao(e, PROTOCOLOS)
    tc = time.perf_counter() - t0
    t0 = time.perf_counter(); executa(e, tmp_path / "svc", PROTOCOLOS)
    tr = time.perf_counter() - t0
    assert tr / tc > 10, f"check ({tc:.3f}s) nao e mais barato que run ({tr:.2f}s)"


def test_check_detecta_score_invalido(clientes):
    r = verifica_integracao(
        {"snapshot": str(clientes["customer_c"]),
         "queries": str(clientes["customer_c"] / "queries.json"),
         "protocol": "DIAGNOSTICO", "adapter": "cliente"}, PROTOCOLOS)
    assert r["status"] == "BLOCKED"
    assert "ranking.veio_do_retriever" in r["barreiras"]


# ── item 19: a retencao existe como mecanismo, nao so como promessa ─────────

def test_retencao_tem_mecanismo(tmp_path):
    """
    `PRIVACY.md` prometia prazos e NADA chamava `Workspace.expira`. Uma
    garantia de retencao sem mecanismo e uma garantia que nao existe.
    """
    import os
    import time as _t
    d = tmp_path / "acme" / "aud1" / "input"
    d.mkdir(parents=True)
    (d / "x.json").write_text("{}", encoding="utf-8")
    antigo = _t.time() - 60 * 60 * 24 * 400
    os.utime(d, (antigo, antigo))

    prev = Workspace.expira(tmp_path / "acme", executar=False)
    assert prev and prev[0]["classe"] == "input" and prev[0]["removido"] is False
    assert d.exists(), "modo lista nao pode apagar"

    Workspace.expira(tmp_path / "acme", executar=True)
    assert not d.exists()


def test_cli_expirar_existe_e_lista_por_padrao(tmp_path, capsys):
    from auditor.cli import main
    (tmp_path / "acme" / "aud1").mkdir(parents=True)
    assert main(["expirar", "--output", str(tmp_path)]) == 0
    assert "nada fora do prazo" in capsys.readouterr().out


# ── VULNERABILIDADE REAL, achada e corrigida em 01/09 ───────────────────────

def test_audit_id_hostil_nao_le_job_de_outro_cliente(tmp_path):
    """
    `Registro._arq` montava `<raiz>/<audit_id>/job.json` sem validar o id. Com
    `audit_id="../globex/segredo"`, o registro do cliente `acme` LIA o job do
    `globex`. Reproduzido antes do fix.

    O HTTP nao vazava — mas por ACIDENTE: o roteador do Starlette nao casa
    barra dentro de parametro de caminho. Protecao incidental de biblioteca
    nao e defesa, e o CLI (`status`, `report`) nao tinha nem isso.
    """
    base = tmp_path / "data"
    (base / "acme").mkdir(parents=True)
    J.Registro(base / "globex").grava(J.Job("segredo123", client_id="globex"))

    for hostil in ("../globex/segredo123", "..", "/etc/passwd", "a/b",
                   "../../../../etc", "."):
        assert J.Registro(base / "acme").ver(hostil) is None, \
            f"audit_id {hostil!r} vazou entre clientes"

    # e o id legitimo continua funcionando
    assert J.Registro(base / "globex").ver("segredo123").client_id == "globex"


@pytest.mark.parametrize("hostil", ["../outro/x", "..", "/abs", "a/b", ""])
def test_workspace_recusa_audit_id_hostil(tmp_path, hostil):
    with pytest.raises(NaoAutorizado):
        Workspace.cria(tmp_path / "svc", hostil)


def test_id_invalido_nao_se_distingue_de_inexistente(tmp_path):
    """Dizer "formato invalido" ja informa ao atacante que o formato importa."""
    reg = J.Registro(tmp_path / "acme")
    assert reg.ver("../fuga") is None
    assert reg.ver("naoexiste") is None
