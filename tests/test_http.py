"""
A API como CAIXA-PRETA. So HTTP: nada de espiar objeto interno.

O que estes testes protegem nao e "os endpoints respondem". E:

  - nenhum GET executa auditoria;
  - o cliente A nunca alcanca o audit_id do cliente B;
  - entrada ruim vira INVALID, nao ERROR;
  - o mesmo request_id nao cobra duas auditorias;
  - o estado sobrevive ao processo.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient                            # noqa: E402

from auditor.cli import PROTOCOLOS                                   # noqa: E402
from auditor.fixtures_cliente import gera_fixtures                   # noqa: E402
from auditor.tenancy import Clientes                                 # noqa: E402


@pytest.fixture(scope="module")
def clientes_fx(tmp_path_factory):
    return gera_fixtures(tmp_path_factory.mktemp("fx"))


@pytest.fixture
def api(tmp_path):
    from auditor.api import cria_app
    base = tmp_path / "svc"
    cs = Clientes(base / "clientes.json")
    chaves = {"acme": cs.cria("acme"), "globex": cs.cria("globex")}
    app = cria_app(base, PROTOCOLOS, base / "clientes.json")
    return TestClient(app), chaves, base


def hdr(k):
    return {"X-API-Key": k}


def corpo(cliente: Path, **extra):
    return {"schema": "AuditInput v1", "snapshot": str(cliente),
            "queries": str(cliente / "queries.json"),
            "protocol": "DIAGNOSTICO", "adapter": "cliente", **extra}


def espera(c, aid, k, limite=120):
    for _ in range(limite):
        r = c.get(f"/v1/audits/{aid}/status", headers=hdr(k))
        if r.json()["status"] not in ("QUEUED", "RUNNING"):
            return r.json()
        time.sleep(0.25)
    raise AssertionError("job nao terminou")


# ── autenticacao ────────────────────────────────────────────────────────────

def test_sem_chave_401(api, clientes_fx):
    c, _, _ = api
    assert c.post("/v1/audits", json=corpo(clientes_fx["customer_a"])).status_code == 401


def test_chave_invalida_401(api, clientes_fx):
    c, _, _ = api
    r = c.post("/v1/audits", json=corpo(clientes_fx["customer_a"]),
               headers=hdr("ak_naoexiste"))
    assert r.status_code == 401


def test_chave_nao_aparece_no_arquivo_em_claro(api):
    _, chaves, base = api
    txt = (base / "clientes.json").read_text(encoding="utf-8")
    for k in chaves.values():
        assert k not in txt


# ── ciclo feliz ─────────────────────────────────────────────────────────────

def test_post_devolve_202_e_queued(api, clientes_fx):
    c, ch, _ = api
    r = c.post("/v1/audits", json=corpo(clientes_fx["customer_a"]),
               headers=hdr(ch["acme"]))
    assert r.status_code == 202 and r.json()["status"] == "QUEUED"
    assert espera(c, r.json()["audit_id"], ch["acme"])["status"] == "COMPLETE"


def test_status_report_manifest(api, clientes_fx):
    c, ch, _ = api
    aid = c.post("/v1/audits", json=corpo(clientes_fx["customer_b"]),
                 headers=hdr(ch["acme"])).json()["audit_id"]
    espera(c, aid, ch["acme"])

    st = c.get(f"/v1/audits/{aid}/status", headers=hdr(ch["acme"])).json()
    assert st["protocol"] == "DIAGNOSTICO v1" and st["service_version"]

    m = c.get(f"/v1/audits/{aid}/manifest", headers=hdr(ch["acme"])).json()
    assert m["schema"] == "AuditResult v1" and len(m["sha256_manifesto"]) == 64

    for tipo in ("executive", "technical"):
        t = c.get(f"/v1/audits/{aid}/report?tipo={tipo}",
                  headers=hdr(ch["acme"])).text
        assert "DIAGNOSTICO v1" in t


def test_get_nao_recalcula(api, clientes_fx):
    """
    Duas leituras da mesma URL devem devolver byte a byte o mesmo. Um GET que
    recalcula faz o sha256 do manifesto deixar de significar coisa alguma.
    """
    c, ch, _ = api
    aid = c.post("/v1/audits", json=corpo(clientes_fx["customer_b"]),
                 headers=hdr(ch["acme"])).json()["audit_id"]
    espera(c, aid, ch["acme"])
    a = c.get(f"/v1/audits/{aid}/manifest", headers=hdr(ch["acme"])).json()
    b = c.get(f"/v1/audits/{aid}/manifest", headers=hdr(ch["acme"])).json()
    assert a == b and a["sha256_manifesto"] == b["sha256_manifesto"]


# ── isolamento entre clientes ───────────────────────────────────────────────

def test_cliente_A_nao_acessa_auditoria_do_cliente_B(api, clientes_fx):
    c, ch, _ = api
    aid = c.post("/v1/audits", json=corpo(clientes_fx["customer_a"]),
                 headers=hdr(ch["acme"])).json()["audit_id"]
    espera(c, aid, ch["acme"])
    for rota in ("", "/status", "/manifest", "/report"):
        r = c.get(f"/v1/audits/{aid}{rota}", headers=hdr(ch["globex"]))
        assert r.status_code == 404, f"{rota} vazou para outro cliente"


def test_listagem_so_mostra_o_proprio(api, clientes_fx):
    c, ch, _ = api
    c.post("/v1/audits", json=corpo(clientes_fx["customer_a"]),
           headers=hdr(ch["acme"]))
    assert c.get("/v1/audits", headers=hdr(ch["globex"])).json()["audits"] == []
    assert c.get("/v1/audits", headers=hdr(ch["acme"])).json()["audits"]


def test_404_nao_revela_existencia(api, clientes_fx):
    """Dizer "existe mas nao e sua" ja entrega a existencia do id."""
    c, ch, _ = api
    aid = c.post("/v1/audits", json=corpo(clientes_fx["customer_a"]),
                 headers=hdr(ch["acme"])).json()["audit_id"]
    alheia = c.get(f"/v1/audits/{aid}/status", headers=hdr(ch["globex"]))
    inexistente = c.get("/v1/audits/naoexiste0000/status", headers=hdr(ch["globex"]))
    assert alheia.status_code == inexistente.status_code == 404


# ── entrada ruim e limites ──────────────────────────────────────────────────

def test_entrada_invalida_vira_INVALID_nao_ERROR(api):
    c, ch, _ = api
    r = c.post("/v1/audits", json={"snapshot": "/x"}, headers=hdr(ch["acme"]))
    assert r.status_code == 422
    assert r.json()["detail"]["status"] == "INVALID"


def test_campo_desconhecido_recusado(api, clientes_fx):
    c, ch, _ = api
    r = c.post("/v1/audits",
               json={**corpo(clientes_fx["customer_a"]), "top_k": 999},
               headers=hdr(ch["acme"]))
    assert r.status_code == 422 and "desconhecid" in r.json()["detail"]["erro"]


def test_limite_excedido_vira_INVALID(tmp_path, clientes_fx):
    from auditor.api import cria_app
    base = tmp_path / "svc"
    cs = Clientes(base / "clientes.json")
    k = cs.cria("pequeno", {"max_queries": 5})
    c = TestClient(cria_app(base, PROTOCOLOS, base / "clientes.json"))
    r = c.post("/v1/audits", json=corpo(clientes_fx["customer_a"]), headers=hdr(k))
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["status"] == "INVALID" and "limite de 5" in d["erro"]


# ── idempotencia ────────────────────────────────────────────────────────────

def test_mesmo_request_id_nao_cria_duas(api, clientes_fx):
    c, ch, _ = api
    b = corpo(clientes_fx["customer_a"], request_id="req-1")
    a1 = c.post("/v1/audits", json=b, headers=hdr(ch["acme"])).json()
    a2 = c.post("/v1/audits", json=b, headers=hdr(ch["acme"])).json()
    assert a1["audit_id"] == a2["audit_id"] and a2.get("idempotente")
    assert len(c.get("/v1/audits", headers=hdr(ch["acme"])).json()["audits"]) == 1


def test_request_id_e_por_cliente(api, clientes_fx):
    """
    Dois clientes com o mesmo request_id sao duas auditorias — nao ha
    colisao entre inquilinos, e nenhum deles ve a do outro.
    """
    c, ch, _ = api
    b = corpo(clientes_fx["customer_a"], request_id="mesmo-id")
    a = c.post("/v1/audits", json=b, headers=hdr(ch["acme"])).json()
    g = c.post("/v1/audits", json=b, headers=hdr(ch["globex"])).json()
    assert a["audit_id"] != g["audit_id"]


# ── estados nao-terminais e ausentes ────────────────────────────────────────

def test_job_inexistente_404(api):
    c, ch, _ = api
    assert c.get("/v1/audits/naoexiste/status", headers=hdr(ch["acme"])).status_code == 404


def test_bloqueada_nao_tem_relatorio_de_resultado(api, clientes_fx):
    c, ch, _ = api
    aid = c.post("/v1/audits", json=corpo(clientes_fx["customer_c"]),
                 headers=hdr(ch["acme"])).json()["audit_id"]
    assert espera(c, aid, ch["acme"])["status"] == "BLOCKED"
    m = c.get(f"/v1/audits/{aid}/manifest", headers=hdr(ch["acme"])).json()
    assert m["resultado"] is None and m["medicoes"] == []


# ── reguas, saude e privacidade de log ──────────────────────────────────────

def test_protocolos_separados_por_regua(api):
    c, _, _ = api
    nomes = {p["nome"] for p in c.get("/v1/protocols").json()["protocols"]}
    assert "DIAGNOSTICO" in nomes
    d = c.get("/v1/protocols/DIAGNOSTICO").json()
    assert d["escopo"] == "diagnostico" and d["versao"] == 1
    assert c.get("/v1/protocols/REL-002").status_code == 404


def test_health_e_ready(api):
    c, _, _ = api
    assert c.get("/health").json()["status"] == "ok"
    r = c.get("/ready").json()
    assert r["ready"] and r["workspace_gravavel"] and r["protocolos"]


def test_log_nao_carrega_query_nem_chave(api, clientes_fx):
    c, ch, _ = api
    c.post("/v1/audits", json=corpo(clientes_fx["customer_a"]),
           headers=hdr(ch["acme"]))
    bruto = json.dumps(c.app.state.log)
    assert ch["acme"] not in bruto and "como resolver" not in bruto
    assert "acme" in bruto


# ── item 21: o estado sobrevive ao processo ─────────────────────────────────

def test_estado_sobrevive_a_reinicializacao(tmp_path, clientes_fx):
    """
    App 1 cria e executa; app 2 e um objeto novo, sem nada em memoria, e
    precisa responder sobre a auditoria do app 1.
    """
    from auditor.api import cria_app
    base = tmp_path / "svc"
    cs = Clientes(base / "clientes.json")
    k = cs.cria("acme")

    c1 = TestClient(cria_app(base, PROTOCOLOS, base / "clientes.json"))
    aid = c1.post("/v1/audits", json=corpo(clientes_fx["customer_a"], request_id="r9"),
                  headers=hdr(k)).json()["audit_id"]
    espera(c1, aid, k)
    del c1

    c2 = TestClient(cria_app(base, PROTOCOLOS, base / "clientes.json"))
    assert c2.get(f"/v1/audits/{aid}/status", headers=hdr(k)).json()["status"] == "COMPLETE"
    assert c2.get(f"/v1/audits/{aid}/manifest", headers=hdr(k)).status_code == 200
    # idempotencia tambem sobrevive
    de_novo = c2.post("/v1/audits", json=corpo(clientes_fx["customer_a"], request_id="r9"),
                      headers=hdr(k)).json()
    assert de_novo["audit_id"] == aid and de_novo.get("idempotente")


# ── item 24: a API nao muda o significado cientifico ────────────────────────

def test_api_nao_reimplementa_regra_de_auditoria():
    t = (RAIZ / "auditor" / "api.py").read_text(encoding="utf-8")
    for proibido in ("min_distintos", "Medicao", "veio_do_retriever",
                     "publica_resultado", "cardinalidade", "top_k ="):
        assert proibido not in t, f"api.py decide sobre auditoria: {proibido}"


def test_api_nao_aceita_mudar_a_regua_por_parametro(api, clientes_fx):
    """Nenhum endpoint pode mexer em k, protocolo ou ressalva."""
    c, ch, _ = api
    r = c.post("/v1/audits",
               json={**corpo(clientes_fx["customer_a"]), "options": {"top_k": 5}},
               headers=hdr(ch["acme"]))
    aid = r.json()["audit_id"]
    espera(c, aid, ch["acme"])
    m = c.get(f"/v1/audits/{aid}/manifest", headers=hdr(ch["acme"])).json()
    assert m["protocolo_spec"]["top_k"] == 50, "opcao do cliente mudou a regua"


# ── regua experimental nao e oferecida pelo servico ─────────────────────────

def test_rel001_nao_e_exposto_nem_aceito(api):
    """
    O REL-001 esta BLOQUEADO e nenhum resultado seu foi validado. Oferece-lo
    por HTTP deixaria um cliente rodar um experimento e receber um relatorio
    que parece produto.

    A doc afirmava isso antes de o codigo garantir — e o codigo aceitava.
    """
    c, ch, _ = api
    nomes = {p["nome"] for p in c.get("/v1/protocols").json()["protocols"]}
    assert "DIAGNOSTICO" in nomes
    assert "REL-001" not in nomes
    assert c.get("/v1/protocols/REL-001").status_code == 404

    r = c.post("/v1/audits",
               json={"schema": "AuditInput v1", "snapshot": "/x",
                     "queries": "/y", "protocol": "REL-001",
                     "adapter": "cliente"}, headers=hdr(ch["acme"]))
    assert r.status_code == 422
    assert "REL-001" in r.json()["detail"]["erro"]


def test_todo_protocolo_exposto_declara_o_escopo(api):
    c, _, _ = api
    for p in c.get("/v1/protocols").json()["protocols"]:
        assert p["escopo"] in ("diagnostico", "protocolo")
        assert p["tipo"] and p["versao"] and p["descricao"]
        assert p["exposto"] is True
