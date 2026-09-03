"""
Transporte HTTP do Agent Runtime — o que estes testes protegem.

Nao e "o endpoint responde 200". E o conjunto de recusas que fazem deste
transporte a opcao `A` assinada, e nao outra coisa parecida:

  * bind so em loopback              — senao a rede inteira dirige o runtime
  * sem CORS                         — senao qualquer pagina aberta fala com ele
  * sem token, sem servidor          — falhar fechado, nao "avisar e subir"
  * teto L0 aplicado na entrada      — a Politica e a segunda trava, nao a unica
  * campo desconhecido e ERRO        — silencio faria rodar diferente do pedido
  * sincrono com teto declarado      — resultado parcial nao pode parecer completo

Cada um destes, se cair, transforma o transporte em algo que a assinatura de
03/09/2026 nao autorizou. Ver `docs/agent_runtime/DECISAO_TRANSPORTE.md`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime import Intencao, Nivel, Politica            # noqa: E402
from agent_runtime.contrato import Observacao, ProvedorDeCapacidade  # noqa: E402
from agent_runtime import transporte as T                      # noqa: E402

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient                       # noqa: E402

TOKEN = "token-de-teste-com-tamanho-suficiente"


class ProvedorFake(ProvedorDeCapacidade):
    nome = "fake"

    def capacidades(self) -> set[str]:
        return {"analyze.json", "observe.network"}

    def executa(self, capacidade, parametros, tarefa_id, iteracao):
        # LISTA, nao uma observacao: o contrato de `ProvedorDeCapacidade` diz
        # `list[Observacao]`, e "nao achei nada" e a lista vazia.
        return [Observacao(capacidade=capacidade, tarefa_id=tarefa_id,
                           iteracao=iteracao, dados={"eco": parametros},
                           fonte="fake")]


def propositor_de_um_passo(tarefa, obs):
    """Uma observacao, depois conclui. Deterministico: nao ha modelo aqui."""
    if not obs:
        return Intencao(capacidade="analyze.json", parametros={"n": 1},
                        porque="primeira e unica observacao")
    return Intencao(capacidade="", concluir=True, porque="objetivo atingido")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_TOKEN", TOKEN)
    return T.cria_app(Politica(nivel_maximo=Nivel.OBSERVAR),
                      [ProvedorFake()], propositor_de_um_passo)


@pytest.fixture
def cli(app):
    return TestClient(app)


def cab(token: str = TOKEN) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── falhar fechado ──────────────────────────────────────────────────────────

def test_sem_token_o_servidor_nao_sobe(monkeypatch):
    """Nao e aviso. Sem token o servidor nao existe."""
    monkeypatch.delenv("AGENT_RUNTIME_TOKEN", raising=False)
    with pytest.raises(T.TransporteMalConfigurado):
        T.cria_app(Politica(), [ProvedorFake()], propositor_de_um_passo)


def test_token_curto_tambem_recusa(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_TOKEN", "curto")
    with pytest.raises(T.TransporteMalConfigurado):
        T.cria_app(Politica(), [ProvedorFake()], propositor_de_um_passo)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.0.10", "", "::"])
def test_bind_fora_de_loopback_e_recusado(app, host):
    """
    A recusa mora no codigo porque `0.0.0.0` e o default de muito exemplo de
    uvicorn — copiar-colar distraido nao pode ser o que expoe o runtime.
    """
    with pytest.raises(T.TransporteMalConfigurado) as e:
        T.roda(app, host=host)
    assert "loopback" in str(e.value)


# ── autenticacao ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("headers", [
    {}, {"Authorization": ""}, {"Authorization": "Bearer errado"},
    {"Authorization": TOKEN},                      # sem o prefixo Bearer
])
def test_endpoints_protegidos_recusam_401(cli, headers):
    assert cli.get("/v1/capacidades", headers=headers).status_code == 401
    assert cli.post("/v1/tarefas", json={}, headers=headers).status_code == 401


def test_health_nao_exige_token_e_declara_os_tetos(cli):
    r = cli.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["streaming"] is False          # a opcao B nao esta assinada
    assert d["teto_nivel"] == int(Nivel.OBSERVAR)
    assert d["teto_segundos"] == T.TETO_SEGUNDOS


# ── CORS: a ausencia e o contrato ───────────────────────────────────────────

@pytest.mark.parametrize("rota,metodo", [
    ("/health", "get"), ("/", "get"),
    ("/v1/capacidades", "get"), ("/v1/tarefas", "post"),
])
def test_nenhuma_resposta_carrega_header_de_cors(cli, rota, metodo):
    """
    Se um `Access-Control-Allow-Origin` aparecer aqui um dia, qualquer pagina
    aberta no navegador passa a poder ler este runtime. A pagina de teste
    dispensa CORS por ser servida pelo proprio servidor.
    """
    fn = getattr(cli, metodo)
    r = fn(rota, headers={**cab(), "Origin": "https://exemplo.invalido"}) \
        if metodo == "get" else fn(rota, json={}, headers={
            **cab(), "Origin": "https://exemplo.invalido"})
    nomes = {k.lower() for k in r.headers}
    assert not any(n.startswith("access-control-") for n in nomes), nomes


def test_preflight_nao_e_atendido(cli):
    r = cli.options("/v1/tarefas", headers={
        "Origin": "https://exemplo.invalido",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


# ── o caminho feliz, fim a fim ──────────────────────────────────────────────

def test_tarefa_valida_roda_e_devolve_observacao(cli):
    r = cli.post("/v1/tarefas", headers=cab(), json={
        "schema": "TarefaRequest v1",
        "objetivo": "provar o transporte fim-a-fim",
        "capacidades": ["analyze.json"],
        "max_iteracoes": 3, "max_segundos": 10, "criada_por": "teste"})
    assert r.status_code == 200
    d = r.json()
    assert d["schema"] == "TarefaResponse v1"
    assert d["estado"] == "CONCLUIDA"
    assert d["concluida"] is True
    assert d["negadas"] == []
    assert len(d["observacoes"]) == 1
    assert d["observacoes"][0]["capacidade"] == "analyze.json"
    assert d["observacoes"][0]["hash"]          # identidade por conteudo
    assert d["task_id"].startswith("T-")


def test_capacidades_mostram_l1_l2_como_recusadas(cli):
    d = cli.get("/v1/capacidades", headers=cab()).json()
    por_nome = {c["nome"]: c for c in d["capacidades"]}
    assert por_nome["analyze.json"]["aceita"] is True
    # L1/L2 aparecem de proposito: o cliente precisa saber que existem e estao
    # recusadas, senao repete o pedido achando que errou o nome.
    assert por_nome["act.click"]["aceita"] is False
    assert por_nome["act.navigate"]["aceita"] is False
    assert "acima do teto" in por_nome["act.navigate"]["motivo"]


# ── as recusas de entrada ───────────────────────────────────────────────────

def test_capacidade_acima_do_teto_e_recusada_na_entrada(cli):
    """
    422 na ENTRADA, nao negacao no meio do loop. Sao duas travas de proposito:
    esta recusa a tarefa inteira antes de existir; a Politica decide por
    chamada. O custo de errar e agir no ambiente de alguem.
    """
    r = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "clicar em coisas", "capacidades": ["act.click"]})
    assert r.status_code == 422
    assert "DECISAO_ATUACAO" in r.json()["detail"]


def test_campo_desconhecido_e_erro_nao_ruido(cli):
    r = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "x", "capacidades": ["analyze.json"], "capacidade": "typo"})
    assert r.status_code == 422
    assert "desconhecidos" in r.json()["detail"]


def test_schema_de_outra_versao_e_recusado(cli):
    r = cli.post("/v1/tarefas", headers=cab(), json={
        "schema": "TarefaRequest v2", "objetivo": "x",
        "capacidades": ["analyze.json"]})
    assert r.status_code == 422


def test_capacidade_inexistente_nao_derruba_o_servidor(cli):
    r = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "x", "capacidades": ["observe.telepatia"]})
    assert r.status_code == 422


def test_corpo_acima_do_teto_e_413(cli):
    gordo = {"objetivo": "x" * (T.TETO_BYTES + 100),
             "capacidades": ["analyze.json"]}
    assert cli.post("/v1/tarefas", headers=cab(), json=gordo).status_code == 413


def test_json_invalido_e_400(cli):
    r = cli.post("/v1/tarefas",
                 headers={**cab(), "Content-Type": "application/json"},
                 content=b"{isto nao e json")
    assert r.status_code == 400


def test_max_segundos_acima_do_teto_e_recusado_antes_de_rodar(cli):
    """
    Recusar na entrada, e nao cortar no meio: uma tarefa cortada devolveria
    resultado parcial com cara de resultado completo.
    """
    r = cli.post("/v1/tarefas", headers=cab(), json={
        "objetivo": "x", "capacidades": ["analyze.json"],
        "max_segundos": T.TETO_SEGUNDOS + 1})
    assert r.status_code == 422
    assert "opcao B" in r.json()["detail"]


# ── a pagina de teste ───────────────────────────────────────────────────────

def test_pagina_e_servida_na_mesma_origem_e_nao_vaza_token(cli):
    r = cli.get("/")
    assert r.status_code == 200
    html = r.text
    assert TOKEN not in html                  # nunca embutido
    assert 'type="password"' in html
    # A pagina MENCIONA localStorage no comentario que explica que nao usa.
    # O teste olha o CODIGO, com os comentarios removidos — senao a regra
    # proibiria documentar a propria decisao.
    codigo = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    for proibido in ("localStorage", "sessionStorage", "indexedDB"):
        assert proibido not in codigo, proibido


def test_pagina_nao_carrega_nada_de_fora(cli):
    """
    Recurso externo numa pagina que manipula token e superficie que nao precisa
    existir. Mesma regra do dashboard do EDP.
    """
    html = cli.get("/").text
    for marca in ("http://", "https://", "//cdn", "src=\"//"):
        assert marca not in html, marca
