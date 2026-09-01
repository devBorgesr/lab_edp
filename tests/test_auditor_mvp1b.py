"""
MVP-1B — productizacao. O que um terceiro precisa para usar isto.

O criterio (item 20): instalar, fornecer inputs, `check`, READY/BLOCKED, `run`,
manifesto, relatorio, verificar hashes, entender o resultado, e rodar de novo
sem alterar o snapshot.

E o sistema precisa IMPEDIR: ranking fabricado, snapshot trocado, artefato
invalido, dado vazando, metrica sob BLOCKED, contaminacao entre clientes.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from auditor.cli import EXIT, PROTOCOLOS, main                       # noqa: E402
from auditor.esquemas import (CAMPOS_RESULTADO, ENTRADA_VERSAO,      # noqa: E402
                              EntradaInvalida, confere_resultado,
                              valida_entrada)
from auditor.fixtures import queries_cliente                         # noqa: E402
from auditor.servico import executa, status_do_job                   # noqa: E402
from auditor.workspace import ForaDoWorkspace, Workspace             # noqa: E402

ADAPT = {"edp": 1, "sintetico": 1}


@pytest.fixture
def q(tmp_path):
    p = tmp_path / "q.json"
    p.write_text(json.dumps({"queries": queries_cliente(24)}), encoding="utf-8")
    return p


def entrada(tmp_path, q, taxa=0.6, **op):
    return {"snapshot": str(tmp_path / "corpus"), "queries": str(q),
            "protocol": "BASICO", "adapter": "sintetico",
            "options": {"taxa_duplicacao": taxa, **op}}


# ── item 4: AuditInput v1 recusa cedo ───────────────────────────────────────

def test_campo_com_erro_de_digitacao_e_recusado(tmp_path, q):
    """
    `protocolo` no lugar de `protocol` rodaria com a regua errada, em silencio,
    e o cliente so descobriria lendo o manifesto.
    """
    e = entrada(tmp_path, q); e["protocolo"] = e.pop("protocol")
    with pytest.raises(EntradaInvalida, match="faltam campos"):
        valida_entrada(e, PROTOCOLOS, ADAPT)


def test_campo_desconhecido_e_recusado(tmp_path, q):
    e = entrada(tmp_path, q); e["top_k"] = 999
    with pytest.raises(EntradaInvalida, match="desconhecidos"):
        valida_entrada(e, PROTOCOLOS, ADAPT)


def test_schema_de_outra_versao_e_recusado(tmp_path, q):
    e = entrada(tmp_path, q); e["schema"] = "AuditInput v2"
    with pytest.raises(EntradaInvalida, match="nao se adivinha"):
        valida_entrada(e, PROTOCOLOS, ADAPT)


def test_protocolo_inexistente_e_recusado(tmp_path, q):
    e = entrada(tmp_path, q); e["protocol"] = "PREMIUM"
    with pytest.raises(EntradaInvalida, match="desconhecido"):
        valida_entrada(e, PROTOCOLOS, ADAPT)


# ── item 5: AuditResult v1 completo ─────────────────────────────────────────

def test_resultado_cumpre_o_contrato(tmp_path, q):
    r = executa(entrada(tmp_path, q), tmp_path / "svc", PROTOCOLOS)
    assert confere_resultado(r) == [], f"AuditResult v1 incompleto"
    assert r["schema"] == "AuditResult v1"
    assert r["status"] == "BLOCKED" and r["resultado"] is None
    assert len(r["medicoes"]) == 5


def test_identidade_completa_mesmo_no_bloqueio_mais_precoce(tmp_path, q):
    """
    Qualquer BLOCKED nasce identificado. Um bloqueio sem identidade nao e
    contestavel: o cliente nao sabe sobre qual corpus, quais queries nem qual
    regua ele aconteceu.
    """
    r = executa(entrada(tmp_path, q), tmp_path / "svc", PROTOCOLOS)
    assert r["snapshot"]["sha256_episodic"]
    assert r["dataset"]["sha256_queries"] and r["dataset"]["n_queries"] == 24
    assert r["protocolo_spec"]["versao"] and r["protocolo_identidade"]
    assert r["retriever"]["versao_adaptador"]
    assert r["configuracao"]["modo"] and r["privacidade"]


# ── item 7: isolamento entre auditorias ─────────────────────────────────────

def test_cada_auditoria_tem_workspace_proprio(tmp_path, q):
    svc = tmp_path / "svc"
    a = executa(entrada(tmp_path / "a", q), svc, PROTOCOLOS)
    b = executa(entrada(tmp_path / "b", q), svc, PROTOCOLOS)
    assert a["workspace"] != b["workspace"]
    for r in (a, b):
        w = Path(r["workspace"])
        assert {p.name for p in w.iterdir()} == {
            "input", "artifacts", "reports", "manifest.json", "job.json"}


def test_reaproveitar_diretorio_e_recusado(tmp_path):
    Workspace.cria(tmp_path / "svc", "aud1")
    with pytest.raises(ForaDoWorkspace, match="ja abrigou"):
        Workspace.cria(tmp_path / "svc", "aud1")


def test_job_json_previo_nao_conta_como_workspace_ocupado(tmp_path):
    """
    O registro grava `job.json` ANTES da execucao, para haver rastro se o
    processo morrer. Um guard que olhasse so `dir.exists()` transformaria esse
    rastro em colisao e derrubaria toda auditoria vinda da fila — foi o que
    aconteceu.
    """
    d = tmp_path / "svc" / "aud9"
    d.mkdir(parents=True)
    (d / "job.json").write_text("{}", encoding="utf-8")
    w = Workspace.cria(tmp_path / "svc", "aud9")
    assert (w.raiz / "input").is_dir()


def test_nao_se_escreve_fora_do_proprio_workspace(tmp_path):
    """
    A fronteira e a RAIZ da auditoria, nao o subdiretorio: `reports/../input/x`
    continua dentro do mesmo cliente e nao e contaminacao. O que precisa ser
    barrado e o que sai da raiz — foi assim que a primeira versao deste teste
    reprovou um caminho legitimo.
    """
    w = Workspace.cria(tmp_path / "svc", "aud2")
    for fuga in ("../../vizinho.json", "../../../etc/passwd",
                 "../../outra_auditoria/manifest.json"):
        with pytest.raises(ForaDoWorkspace):
            w.caminho("reports", fuga)
    assert w.caminho("reports", "../input/nota.json").is_relative_to(w.raiz)


def test_uma_auditoria_nao_le_artefato_de_outra(tmp_path, q):
    svc = tmp_path / "svc"
    a = executa(entrada(tmp_path / "a", q, taxa=0.6), svc, PROTOCOLOS)
    b = executa(entrada(tmp_path / "b", q, taxa=0.0), svc, PROTOCOLOS)
    ma = json.loads((Path(a["workspace"]) / "manifest.json").read_text())
    mb = json.loads((Path(b["workspace"]) / "manifest.json").read_text())
    assert ma["audit_id"] != mb["audit_id"]
    # nenhum manifesto menciona o outro, e nenhum arquivo e compartilhado
    assert mb["audit_id"] not in json.dumps(ma)
    assert ma["audit_id"] not in json.dumps(mb)
    assert not set(Path(a["workspace"]).rglob("*")) & set(
        Path(b["workspace"]).rglob("*"))
    assert Path(a["workspace"]).name != Path(b["workspace"]).name
    # os dois corpora sinteticos tem o MESMO conteudo, logo o mesmo hash — e
    # isso e correto: a identidade do corpus e o conteudo, nao o caminho.
    assert ma["snapshot"]["sha256_episodic"] == mb["snapshot"]["sha256_episodic"]
    assert ma["snapshot"]["dir"] != mb["snapshot"]["dir"]


# ── item 8: retencao ────────────────────────────────────────────────────────

def test_retencao_declarada_por_classe(tmp_path):
    p = Workspace.cria(tmp_path / "svc", "aud3").politica_de_retencao()
    d = p["dias_por_classe"]
    assert d["input"] < d["artifacts"] < d["reports"] < d["manifest"], \
        "material bruto do cliente precisa expirar antes dos derivados"


def test_expiracao_lista_antes_de_apagar(tmp_path, q):
    svc = tmp_path / "svc"
    executa(entrada(tmp_path, q), svc, PROTOCOLOS)
    futuro = datetime.now(timezone.utc) + timedelta(days=400)
    prev = Workspace.expira(svc, agora=futuro, executar=False)
    assert prev and all(x["removido"] is False for x in prev)
    assert all(p.exists() for p in svc.rglob("manifest.json")), \
        "modo lista nao pode apagar nada"


# ── item 9: redacao como ultima barreira ────────────────────────────────────

def test_manifesto_gravado_nao_carrega_texto_do_cliente(tmp_path, q):
    r = executa(entrada(tmp_path, q), tmp_path / "svc", PROTOCOLOS)
    bruto = (Path(r["workspace"]) / "manifest.json").read_text(encoding="utf-8")
    assert "indexacao postgres" not in bruto
    for rel in ("executive.md", "technical.md"):
        t = (Path(r["workspace"]) / "reports" / rel).read_text(encoding="utf-8")
        assert "como resolver" not in t


def test_gravacao_falha_se_segredo_sobreviver(tmp_path):
    """
    A barreira e ANTES da persistencia, e falha alto: vazamento e irreversivel,
    entao nao gravar e melhor que gravar e corrigir depois.
    """
    from auditor.manifest import Manifesto
    from auditor.redacao import Politica

    class PoliticaCega(Politica):
        def sanitiza(self, obj):
            return obj                      # simula falha da sanitizacao

    m = Manifesto("x", "P")
    m.configuracao = {"nota": "chave sk-ant-api03-" + "A" * 40}
    with pytest.raises(RuntimeError, match="segredo sobreviveu"):
        m.salva(tmp_path / "m.json", politica=PoliticaCega())


# ── itens 10-12: API HTTP ───────────────────────────────────────────────────
#
# Os testes de API que estavam AQUI foram removidos, nao apagados por
# conveniencia: `tests/test_http.py` os substitui como suite CAIXA-PRETA, com
# autenticacao, isolamento entre clientes e reinicializacao — coisas que estes
# nao cobriam porque foram escritos antes de a API ter inquilinos.
#
# Manter as duas versoes daria duas suites testando a mesma coisa sob
# pressupostos diferentes, e a que ficasse desatualizada passaria a mentir.

# ── item 13: log operacional nao e resultado ────────────────────────────────

def test_observabilidade_e_separada_do_resultado(tmp_path, q):
    r = executa(entrada(tmp_path, q), tmp_path / "svc", PROTOCOLOS)
    o = r["observabilidade"]
    assert o["tempo_servico_s"] >= 0 and "tempo_engine" in o
    assert "NAO e resultado" in o["nota"]
    assert "observabilidade" not in {x["nome"] for x in r["medicoes"]}


# ── item 3: instalacao limpa ────────────────────────────────────────────────

def test_nucleo_nao_precisa_de_fastapi():
    """O extra `http` e opcional; o engine e o CLI rodam sem ele."""
    cod = ("import sys; sys.modules['fastapi']=None; sys.modules['uvicorn']=None;"
           f"sys.path.insert(0, {str(RAIZ)!r});"
           "import auditor, auditor.servico, auditor.cli, auditor.workspace;"
           "print('ok')")
    r = subprocess.run([sys.executable, "-c", cod], capture_output=True, text=True)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr[-400:]


def test_pyproject_declara_nucleo_sem_dependencia():
    t = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in t
    assert "auditor = " in t and "optional-dependencies" in t


# ── item 20: criterio de saida, ponta a ponta pelo CLI ──────────────────────

def test_terceiro_consegue_usar_pelo_cli(tmp_path, q, capsys):
    corpus = str(tmp_path / "corpus")
    base = ["--input", corpus, "--queries", str(q), "--protocol", "BASICO",
            "--adaptador", "sintetico", "--taxa-duplicacao", "0.6",
            "--output", str(tmp_path / "svc")]

    assert main(["check", *base]) == EXIT["BLOCKED"]
    saida = capsys.readouterr().out
    assert "BASICO v1" in saida and "dry-run" in saida

    assert main(["run", *base]) == EXIT["BLOCKED"]
    saida = capsys.readouterr().out
    assert "manifest.json" in saida

    # `check` e `run` sao auditorias distintas, cada uma com workspace
    # proprio; a do dry-run nao grava relatorio, de proposito.
    workspaces = [p for p in (tmp_path / "svc").iterdir() if p.is_dir()]
    assert len(workspaces) == 2, "check e run precisam de workspaces separados"
    com_relatorio = [p for p in workspaces
                     if (p / "reports" / "executive.md").exists()]
    assert len(com_relatorio) == 1, "so o `run` grava relatorio"

    w = com_relatorio[0]
    d = json.loads((w / "manifest.json").read_text())
    assert d["resultado"] is None and len(d["sha256_manifesto"]) == 64
    assert (w / "reports" / "technical.md").exists()
    assert (w / "artifacts" / "checks.json").exists()
    assert (w / "input" / "audit_input.json").exists()


def test_rodar_de_novo_nao_altera_o_snapshot(tmp_path, q):
    svc, e = tmp_path / "svc", entrada(tmp_path, q)
    r1 = executa(e, svc, PROTOCOLOS)
    epi = Path(e["snapshot"]) / "sessions" / "default_cognitive" / "episodic.json"
    antes = hashlib.sha256(epi.read_bytes()).hexdigest()
    r2 = executa(e, svc, PROTOCOLOS)
    assert hashlib.sha256(epi.read_bytes()).hexdigest() == antes
    assert (r1["snapshot"]["sha256_episodic"] ==
            r2["snapshot"]["sha256_episodic"])
    assert ([m["valor"] for m in r1["medicoes"]] ==
            [m["valor"] for m in r2["medicoes"]])
