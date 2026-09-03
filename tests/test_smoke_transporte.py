"""
Smoke test do brief: o ciclo inteiro pelo transporte real, com Router no laco
e HAR de verdade.

    POST /v1/tarefas
        -> TaskService persiste
        -> Executor
        -> PropositorLLM
        -> RoteadorFixo            (Router FAKE, como o brief pede primeiro)
        -> ClienteFake             (nao gasta API; modelo real e etapa depois)
        -> Intencao
        -> Politica L0
        -> ProvedorHAR             (arquivo HAR real, no formato do Exportador)
        -> Observacao
    GET /v1/tarefas/{id}/resultado -> pelo MESMO canal

O que estes testes cobrem e que `test_transporte.py` nao cobre: la o
propositor e uma funcao deterministica e o provedor e um fake que ecoa
parametro. Aqui o laco passa por Roteador e por um provedor que le arquivo —
sao as duas pecas que o brief nomeia no smoke test e que a primeira versao
nao exercitou.

NAO usa modelo real. O segundo smoke, com provider configurado, e etapa
separada e continua nao feita — ver `CHECKLIST_TRANSPORTE.md` §5.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime import Nivel, Politica                            # noqa: E402
from agent_runtime import servico as S                               # noqa: E402
from agent_runtime import transporte as T                            # noqa: E402
from agent_runtime.propositor import ClienteFake, PropositorLLM      # noqa: E402
from agent_runtime.provedores.har import ProvedorHAR                 # noqa: E402
from agent_runtime.roteador import RoteadorFixo                      # noqa: E402

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient                            # noqa: E402

TOKEN = "token-do-smoke-com-tamanho-suficiente"


@pytest.fixture
def har(tmp_path) -> Path:
    """HAR no formato que o Exportador grava, COM segredo — para provar que a
    redacao do provedor acontece antes de a observacao chegar ao cliente."""
    doc = {"log": {"version": "1.2",
                   "creator": {"name": "Claude Exporter — Copiloto"},
                   "entries": [
        {"request": {"url": "https://api.exemplo/search?q=x", "method": "POST",
                     "headers": [
                         {"name": "authorization", "value": "Bearer SEGREDO-DO-HAR"},
                         {"name": "content-type", "value": "application/json"}]},
         "response": {"status": 403,
                      "headers": [{"name": "set-cookie", "value": "sess=SEGREDO-DO-HAR"}],
                      "content": {"mimeType": "application/json",
                                  "text": '{"erro":"forbidden"}'}},
         "time": 42.0},
        {"request": {"url": "https://api.exemplo/ok", "method": "GET",
                     "headers": [{"name": "accept", "value": "application/json"}]},
         "response": {"status": 200, "headers": [],
                      "content": {"mimeType": "application/json", "text": '{"ok":1}'}},
         "time": 12.0},
    ]}}
    p = tmp_path / "sessao.har"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


@pytest.fixture
def cli(monkeypatch, tmp_path, har):
    monkeypatch.delenv("AGENT_RUNTIME_TOKENS", raising=False)
    monkeypatch.setenv("AGENT_RUNTIME_TOKEN", TOKEN)
    # Router FAKE e modelo FAKE: o brief manda usar Router fake primeiro, e
    # nao gastar API neste smoke.
    prop = PropositorLLM(
        cliente=ClienteFake([
            '{"capacidade":"observe.network","parametros":{"status":403},'
            ' "porque":"procurar a requisicao que falhou"}',
            '{"concluir":true,"porque":"achei a requisicao 403"}',
        ]),
        roteador=RoteadorFixo("modelo-fake-1", tier=1))
    app = T.cria_app(Politica(nivel_maximo=Nivel.OBSERVAR), [ProvedorHAR(har)],
                     prop, raiz=tmp_path / "tarefas",
                     nome_propositor="llm-fake+roteador-fixo")
    app.state.propositor = prop
    return TestClient(app)


def cab(**extra) -> dict:
    return {"Authorization": f"Bearer {TOKEN}", **extra}


def ate_terminal(cli, tid, limite=10.0):
    fim = time.time() + limite
    while time.time() < fim:
        d = cli.get(f"/v1/tarefas/{tid}", headers=cab()).json()
        if d["terminal"]:
            return d
        time.sleep(0.05)
    raise AssertionError(f"nao terminou em {limite}s: {d}")


def test_ciclo_completo_pelo_transporte_com_router_e_har(cli):
    """O critério do brief, menos o Copiloto — que a assinatura de 03/09 adiou."""
    r = cli.post("/v1/tarefas", headers=cab(**{"X-Correlation-Id": "smoke-1"}),
                 json={"schema": "TarefaRequest v1",
                       "objetivo": "descobrir por que /search devolve 403",
                       "capacidades": ["observe.network"],
                       "max_iteracoes": 5, "criada_por": "smoke"})
    assert r.status_code == 202
    tid = r.json()["task_id"]

    d = ate_terminal(cli, tid)
    assert d["status"] == S.CONCLUIDA
    assert d["correlation_id"] == "smoke-1"
    assert d["motivo_parada"] == "achei a requisicao 403"
    assert d["negadas"] == []
    assert len(d["observacoes"]) == 1

    o = d["observacoes"][0]
    assert o["capacidade"] == "observe.network"
    assert o["tarefa_id"] == tid
    assert o["fonte"]                      # veio de arquivo, nao de fake em memoria

    # ── consulta do RESULTADO pelo mesmo canal ──────────────────────────────
    res = cli.get(f"/v1/tarefas/{tid}/resultado", headers=cab())
    assert res.status_code == 200
    assert res.json()["status"] == S.CONCLUIDA
    assert res.json()["observacoes"] == d["observacoes"]


def test_o_router_esteve_no_laco(cli):
    """
    Sem isto o teste acima passaria com o Router curto-circuitado. A trilha do
    `PropositorLLM` registra qual modelo respondeu cada iteracao — se ela
    estiver vazia, o Router nao participou.
    """
    tid = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "descobrir por que /search devolve 403",
        "capacidades": ["observe.network"], "max_iteracoes": 5}).json()["task_id"]
    ate_terminal(cli, tid)
    trilha = cli.app.state.propositor.trilha
    assert trilha, "o Roteador nao foi consultado"
    assert all(p.get("modelo") == "modelo-fake-1" for p in trilha), trilha


def test_segredo_do_har_nao_chega_ao_cliente(cli):
    """
    O HAR de entrada TEM `authorization: Bearer SEGREDO-DO-HAR` e um
    `set-cookie`. O provedor redige antes de virar `Observacao`; se algum dia
    parar de redigir, o segredo sai por este endpoint HTTP para quem tiver
    token — que e outra pessoa que nao a dona do HAR.
    """
    tid = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "descobrir por que /search devolve 403",
        "capacidades": ["observe.network"], "max_iteracoes": 5}).json()["task_id"]
    ate_terminal(cli, tid)
    corpo = cli.get(f"/v1/tarefas/{tid}/resultado", headers=cab()).text
    assert "SEGREDO-DO-HAR" not in corpo
    assert "REDIGIDO" in corpo


def test_har_ausente_falha_na_montagem_e_nao_no_turno(tmp_path, monkeypatch):
    """
    Provedor que nao consegue ler sua fonte tem de recusar ao ser montado. Se
    o erro so aparecesse durante a tarefa, o cliente receberia FALHA generica
    por um problema de configuracao do servidor.
    """
    monkeypatch.setenv("AGENT_RUNTIME_TOKEN", TOKEN)
    with pytest.raises(FileNotFoundError):
        ProvedorHAR(tmp_path / "nao-existe.har")
