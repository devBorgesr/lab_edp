"""
O canal pelos endpoints HTTP reais, e o laco completo ate a tarefa persistida.

ATE ONDE ESTES TESTES VAO, E ONDE PARAM

Eles exercitam tudo do lado do Runtime: os tres endpoints, a correlacao por
`request_id`, o isolamento por cliente, e uma tarefa inteira que so conclui
porque uma observacao de navegador voltou pelo canal.

O que eles NAO provam: `chrome.debugger`. O painel aqui e um cliente Python
que fala os mesmos endpoints. A logica do controller real esta provada
separadamente em `tests/js/test_controller.mjs`, sob um `chrome` simulado. O
smoke com Chrome de verdade continua aberto — ver
`docs/agent_runtime/SMOKE_BROWSER_INSPECT.md`.

Nao chamar isto de "E2E com Chrome" seria a diferenca entre o que foi medido e
o que se gostaria de ter medido.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime import Intencao, Nivel, Politica                      # noqa: E402
from agent_runtime import servico as S                                   # noqa: E402
from agent_runtime import transporte as T                                # noqa: E402
from agent_runtime.canal import CanalMesa, MesaDeSolicitacoes            # noqa: E402
from agent_runtime.propositor import ClienteFake, PropositorLLM          # noqa: E402
from agent_runtime.provedores.browser import (                           # noqa: E402
    PROTOCOLO, ChromeDebuggerProvider, registra_alvo)
from agent_runtime.roteador import RoteadorFixo                          # noqa: E402

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient                                # noqa: E402

TOKEN, TOKEN_B = "token-do-canal-com-tamanho-ok", "outro-token-do-canal-longo"
TAB, ORIGEM = 42, "http://127.0.0.1:8000"


def cab(token=TOKEN, **extra):
    return {"Authorization": f"Bearer {token}", **extra}


def alvo_json(tab_id=TAB, origin=ORIGEM):
    return {"tab_id": tab_id, "origin": origin, "session_id": "S-1",
            "registrado_em": "2026-09-03T00:00:00Z"}


@pytest.fixture
def mesa():
    return MesaDeSolicitacoes()


@pytest.fixture
def cli(monkeypatch, tmp_path, mesa):
    monkeypatch.delenv("AGENT_RUNTIME_TOKEN", raising=False)
    monkeypatch.setenv("AGENT_RUNTIME_TOKENS", f"acme:{TOKEN},globex:{TOKEN_B}")

    def propositor(tarefa, obs):
        if not obs:
            return Intencao(capacidade="browser.inspect", parametros={},
                            porque="ver o dashboard")
        return Intencao(capacidade="", concluir=True, porque="dashboard visto")

    prov = ChromeDebuggerProvider(
        CanalMesa(mesa, "acme"),
        registra_alvo(TAB, ORIGEM, "S-1", "2026-09-03T00:00:00Z"),
        timeout_s=8.0)
    app = T.cria_app(Politica(nivel_maximo=Nivel.OBSERVAR), [prov], propositor,
                     raiz=tmp_path / "tarefas", mesa=mesa,
                     nome_propositor="teste-canal")
    return TestClient(app)


# ── registro do alvo ────────────────────────────────────────────────────────

def test_registro_do_alvo_aceita_loopback(cli):
    r = cli.post("/v1/browser/alvo", headers=cab(), json=alvo_json())
    assert r.status_code == 200
    assert r.json() == {"ok": True, "tab_id": TAB, "origin": ORIGEM}


@pytest.mark.parametrize("origem", [
    "https://example.com", "https://claude.ai", "http://10.0.0.5:8000",
    "https://127.0.0.1:8000", "", "nao-e-url",
])
def test_registro_de_alvo_fora_do_loopback_e_422(cli, origem):
    r = cli.post("/v1/browser/alvo", headers=cab(), json=alvo_json(origin=origem))
    assert r.status_code == 422
    assert "recusado" in r.json()["detail"]


def test_endpoints_do_canal_exigem_token(cli):
    assert cli.get("/v1/browser/solicitacoes").status_code == 401
    assert cli.post("/v1/browser/alvo", json=alvo_json()).status_code == 401
    assert cli.post("/v1/browser/resultados", json={}).status_code == 401


# ── polling ─────────────────────────────────────────────────────────────────

def test_sem_pedido_o_poll_devolve_204(cli):
    """
    204, nao 200 com `{}`. Obrigar o painel a distinguir "vazio" de "erro" pelo
    conteudo faria ele errar uma hora.
    """
    assert cli.get("/v1/browser/solicitacoes", headers=cab()).status_code == 204


def test_resultado_sem_pedido_vivo_e_409(cli):
    """
    409 e nao 404: o pedido pode ter existido e expirado. O painel precisa
    saber que a resposta foi DESCARTADA, e nao presumir que o trabalho contou.
    """
    r = cli.post("/v1/browser/resultados", headers=cab(), json={
        "protocol": PROTOCOLO, "kind": "capability.result",
        "request_id": "R-fantasma", "type": "browser.observation",
        "target": {"tab_id": TAB, "origin": ORIGEM}, "observations": []})
    assert r.status_code == 409
    assert "descartada" in r.json()["detail"]


def test_um_cliente_nao_busca_nem_responde_o_pedido_do_outro(cli, mesa):
    p = mesa.publica({"protocol": PROTOCOLO, "capability": "browser.inspect"}, "acme")
    assert cli.get("/v1/browser/solicitacoes", headers=cab(TOKEN_B)).status_code == 204
    r = cli.post("/v1/browser/resultados", headers=cab(TOKEN_B), json={
        "protocol": PROTOCOLO, "kind": "capability.result",
        "request_id": p.request_id, "type": "browser.observation",
        "target": {"tab_id": TAB, "origin": ORIGEM}, "observations": []})
    assert r.status_code == 409
    # o dono continua conseguindo
    assert cli.get("/v1/browser/solicitacoes", headers=cab()).status_code == 200


# ── o laco completo ─────────────────────────────────────────────────────────

class PainelSimulado(threading.Thread):
    """
    Faz o que o `browser_bridge.js` faz: busca, executa, devolve com o MESMO
    `request_id`. NAO usa chrome.debugger — devolve observacao fixa. O que se
    prova aqui e o canal, nao o navegador.
    """
    daemon = True

    def __init__(self, cli, token=TOKEN, ate=12.0):
        super().__init__()
        self.cli, self.token, self.ate = cli, token, ate
        self.atendidos: list[str] = []
        self.pare = threading.Event()

    def run(self):
        fim = time.time() + self.ate
        while time.time() < fim and not self.pare.is_set():
            r = self.cli.get("/v1/browser/solicitacoes", headers=cab(self.token))
            if r.status_code == 204:
                time.sleep(0.05); continue
            p = r.json()
            self.atendidos.append(p["request_id"])
            self.cli.post("/v1/browser/resultados", headers=cab(self.token), json={
                "protocol": PROTOCOLO, "kind": "capability.result",
                "request_id": p["request_id"],       # nunca inventado
                "type": "browser.observation",
                "target": p["target"],
                "observations": [
                    {"kind": "page", "url": f"{ORIGEM}/dashboard", "title": "EDP Runtime"},
                    {"kind": "dom", "dom_nodes": 318},
                    {"kind": "history", "history_len": 2}]})


def test_tarefa_conclui_porque_a_observacao_voltou_pelo_canal(cli):
    """
    O criterio de aceite, ate onde da sem Chrome:
    Task -> Executor -> browser.inspect -> canal -> painel -> Observacao ->
    tarefa CONCLUIDA e persistida.
    """
    painel = PainelSimulado(cli); painel.start()
    tid = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "inspecionar o dashboard do EDP",
        "capacidades": ["browser.inspect"], "max_iteracoes": 5,
        "criada_por": "teste-canal"}).json()["task_id"]

    fim = time.time() + 12
    while time.time() < fim:
        d = cli.get(f"/v1/tarefas/{tid}", headers=cab()).json()
        if d["terminal"]:
            break
        time.sleep(0.05)
    painel.pare.set()

    assert d["status"] == S.CONCLUIDA, d
    assert d["negadas"] == []
    assert len(d["observacoes"]) == 3
    kinds = sorted(o["dados"]["kind"] for o in d["observacoes"])
    assert kinds == ["dom", "history", "page"]
    pag = next(o for o in d["observacoes"] if o["dados"]["kind"] == "page")
    assert pag["dados"]["url"] == f"{ORIGEM}/dashboard"
    assert f"tab={TAB}" in pag["fonte"]
    assert painel.atendidos, "o painel nunca foi chamado"

    # e o resultado persiste, consultavel pelo mesmo canal
    r = cli.get(f"/v1/tarefas/{tid}/resultado", headers=cab())
    assert r.status_code == 200
    assert r.json()["observacoes"] == d["observacoes"]


def test_duas_tarefas_simultaneas_nao_trocam_observacao(cli):
    """
    Dois `request_id` vivos ao mesmo tempo, um painel so atendendo os dois.
    Se a correlacao falhasse, uma tarefa receberia a observacao da outra.
    """
    painel = PainelSimulado(cli); painel.start()
    ids = [cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": f"inspecionar o dashboard {n}",
        "capacidades": ["browser.inspect"], "max_iteracoes": 5}).json()["task_id"]
        for n in range(2)]

    fim = time.time() + 15
    vistos = {}
    while time.time() < fim and len(vistos) < 2:
        for tid in ids:
            d = cli.get(f"/v1/tarefas/{tid}", headers=cab()).json()
            if d["terminal"]:
                vistos[tid] = d
        time.sleep(0.05)
    painel.pare.set()

    assert len(vistos) == 2, vistos
    assert len(set(painel.atendidos)) == len(painel.atendidos), "request_id repetido"
    for tid, d in vistos.items():
        assert d["status"] == S.CONCLUIDA
        assert d["task_id"] == tid
        assert all(o["tarefa_id"] == tid for o in d["observacoes"])


def test_sem_painel_a_tarefa_falha_por_canal_e_nao_por_pagina_vazia(cli):
    """
    Ninguem buscando: a tarefa nao pode terminar CONCLUIDA com zero
    observacoes, que o modelo leria como "a pagina nao tem nada".
    """
    prov = cli.app.state.servico.provedores[0]
    prov.timeout_s = 1.0
    tid = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "inspecionar sem painel ligado",
        "capacidades": ["browser.inspect"], "max_iteracoes": 2}).json()["task_id"]

    fim = time.time() + 12
    while time.time() < fim:
        d = cli.get(f"/v1/tarefas/{tid}", headers=cab()).json()
        if d["terminal"]:
            break
        time.sleep(0.05)
    assert d["status"] in (S.FALHA, S.ESGOTADA), d
    assert d["status"] != S.CONCLUIDA
    assert d["observacoes"] == []


# ── o arnes do controller real, em node ─────────────────────────────────────

def test_controller_real_sob_chrome_simulado():
    """
    Roda `tests/js/test_controller.mjs`, que carrega o
    `debugger_controller.js` REAL do Exportador num `vm` com um `chrome`
    falso. Cobre os tres negativos obrigatorios: alvo errado, origem mudada e
    debugger desanexado.
    """
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node ausente — o arnes do controller nao pode rodar")
    arq = RAIZ / "tests" / "js" / "test_controller.mjs"
    if not (Path("/media/sf_sf_exportador/claude-exporter-v4.2/copilot/"
                 "debugger_controller.js")).exists():
        pytest.skip("Exportador nao montado neste ambiente")
    r = subprocess.run([node, str(arq)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 falha(s)" in r.stdout
