"""
Transporte HTTP do Agent Runtime — o que estes testes protegem.

Nao e "o endpoint responde 200". E o conjunto de recusas e de garantias que
fazem deste transporte a opcao `A` assinada, e nao outra coisa parecida:

  * bind so em loopback              — senao a rede inteira dirige o runtime
  * sem CORS                         — senao qualquer pagina aberta fala com ele
  * sem token, sem servidor          — falhar fechado, nao "avisar e subir"
  * teto L0 aplicado na entrada      — a Politica e a segunda trava, nao a unica
  * campo desconhecido e ERRO        — silencio faria rodar diferente do pedido
  * tarefa PERSISTIDA e assincrona   — senao nao ha o que consultar
  * cliente so ve a propria tarefa   — `task_id` nao e segredo
  * reenvio nao duplica trabalho     — idempotencia por `X-Request-Id`

Cada um destes, se cair, transforma o transporte em algo que a assinatura de
03/09/2026 nao autorizou. Ver `docs/agent_runtime/DECISAO_TRANSPORTE.md` e
`docs/agent_runtime/CHECKLIST_TRANSPORTE.md`.
"""
from __future__ import annotations

import re
import socket
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime import Intencao, Nivel, Politica                  # noqa: E402
from agent_runtime import servico as S                               # noqa: E402
from agent_runtime import transporte as T                            # noqa: E402
from agent_runtime.contrato import Observacao, ProvedorDeCapacidade  # noqa: E402

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient                            # noqa: E402

TOKEN = "token-de-teste-com-tamanho-suficiente"
TOKEN_B = "outro-token-de-teste-suficientemente-longo"


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


def propositor_lento(tarefa, obs):
    """
    Nunca conclui sozinho e dorme entre iteracoes.

    Existe para que haja uma janela real em que a tarefa esta EXECUTANDO —
    sem ela, cancelamento e `409 ainda nao ha resultado` nao teriam como ser
    observados, e o teste passaria por acidente de corrida.
    """
    time.sleep(0.25)
    return Intencao(capacidade="analyze.json", parametros={"i": len(obs)},
                    porque="lento de proposito")


REQ = {"schema": "TarefaRequest v1", "objetivo": "provar o transporte",
       "capacidades": ["analyze.json"], "max_iteracoes": 3, "criada_por": "teste"}


@pytest.fixture
def monta(monkeypatch, tmp_path):
    def _monta(propositor=propositor_de_um_passo, tokens: str | None = None, **kw):
        monkeypatch.delenv("AGENT_RUNTIME_TOKENS", raising=False)
        monkeypatch.delenv("AGENT_RUNTIME_TOKEN", raising=False)
        if tokens:
            monkeypatch.setenv("AGENT_RUNTIME_TOKENS", tokens)
        else:
            monkeypatch.setenv("AGENT_RUNTIME_TOKEN", TOKEN)
        return T.cria_app(Politica(nivel_maximo=Nivel.OBSERVAR),
                          [ProvedorFake()], propositor,
                          raiz=tmp_path / "tarefas", **kw)
    return _monta


@pytest.fixture
def app(monta):
    return monta()


@pytest.fixture
def cli(app):
    return TestClient(app)


def cab(token: str = TOKEN, **extra) -> dict:
    return {"Authorization": f"Bearer {token}", **extra}


def ate_terminal(cli, task_id, headers, limite=8.0):
    """Poll ate a tarefa terminar. Devolve a ultima visao lida."""
    fim = time.time() + limite
    while time.time() < fim:
        d = cli.get(f"/v1/tarefas/{task_id}", headers=headers).json()
        if d["terminal"]:
            return d
        time.sleep(0.05)
    raise AssertionError(f"tarefa {task_id} nao terminou em {limite}s: {d}")


# ── falhar fechado ──────────────────────────────────────────────────────────

def test_sem_token_o_servidor_nao_sobe(monkeypatch):
    """Nao e aviso. Sem token o servidor nao existe."""
    monkeypatch.delenv("AGENT_RUNTIME_TOKEN", raising=False)
    monkeypatch.delenv("AGENT_RUNTIME_TOKENS", raising=False)
    with pytest.raises(T.TransporteMalConfigurado):
        T.cria_app(Politica(), [ProvedorFake()], propositor_de_um_passo)


def test_token_curto_tambem_recusa(monkeypatch):
    monkeypatch.delenv("AGENT_RUNTIME_TOKENS", raising=False)
    monkeypatch.setenv("AGENT_RUNTIME_TOKEN", "curto")
    with pytest.raises(T.TransporteMalConfigurado):
        T.cria_app(Politica(), [ProvedorFake()], propositor_de_um_passo)


@pytest.mark.parametrize("valor", ["semdoisPontos", "acme:curto", ":tok-longo-o-bastante",
                                   "../fuga:tok-longo-o-bastante"])
def test_tokens_multicliente_mal_formados_recusam(monkeypatch, valor):
    monkeypatch.setenv("AGENT_RUNTIME_TOKENS", valor)
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


# ── autenticacao e identidade ───────────────────────────────────────────────

@pytest.mark.parametrize("headers", [
    {}, {"Authorization": ""}, {"Authorization": "Bearer errado"},
    {"Authorization": TOKEN},                      # sem o prefixo Bearer
])
def test_endpoints_protegidos_recusam_401(cli, headers):
    assert cli.get("/v1/capacidades", headers=headers).status_code == 401
    assert cli.post("/v1/tarefas", json=REQ, headers=headers).status_code == 401
    assert cli.get("/v1/tarefas/T-qualquer", headers=headers).status_code == 401


def test_health_nao_exige_token_e_declara_os_tetos(cli):
    r = cli.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["streaming"] is False          # a opcao B nao esta assinada
    assert d["assincrono"] is True
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
    o = {"Origin": "https://exemplo.invalido"}
    r = (cli.get(rota, headers={**cab(), **o}) if metodo == "get"
         else cli.post(rota, json=REQ, headers={**cab(), **o}))
    nomes = {k.lower() for k in r.headers}
    assert not any(n.startswith("access-control-") for n in nomes), nomes


def test_preflight_nao_e_atendido(cli):
    r = cli.options("/v1/tarefas", headers={
        "Origin": "https://exemplo.invalido",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


# ── caminho feliz, assincrono ───────────────────────────────────────────────

def test_submissao_devolve_202_e_task_id_sem_resultado(cli):
    """
    202, nao 200. A tarefa foi ACEITA; dizer 200 afirmaria que ha resultado, e
    nesse instante nao ha.
    """
    r = cli.post("/v1/tarefas", headers=cab(), json=REQ)
    assert r.status_code == 202
    d = r.json()
    assert d["schema"] == "TarefaResponse v1"
    assert d["task_id"].startswith("T-")
    assert d["status"] in (S.RECEBIDA, S.EXECUTANDO)
    assert d["terminal"] is False
    assert d["observacoes"] == []
    assert r.headers["location"] == f"/v1/tarefas/{d['task_id']}"


def test_consulta_de_estado_ate_terminal(cli):
    tid = cli.post("/v1/tarefas", headers=cab(), json=REQ).json()["task_id"]
    d = ate_terminal(cli, tid, cab())
    assert d["status"] == S.CONCLUIDA
    assert d["iteracoes"] == 1
    assert d["negadas"] == []
    assert len(d["observacoes"]) == 1
    assert d["observacoes"][0]["capacidade"] == "analyze.json"
    assert d["observacoes"][0]["hash"]           # identidade por conteudo
    assert d["started_at"] and d["finished_at"]
    assert d["duracao_ms"] is not None


def test_consulta_de_resultado_e_409_enquanto_roda(monta):
    """
    409 e nao 200-com-corpo-vazio: "ainda nao ha resultado" e um fato diferente
    de "o resultado e vazio", e o cliente precisa distinguir sem adivinhar.
    """
    cli = TestClient(monta(propositor_lento))
    tid = cli.post("/v1/tarefas", headers=cab(),
                   json={**REQ, "max_iteracoes": 50}).json()["task_id"]
    r = cli.get(f"/v1/tarefas/{tid}/resultado", headers=cab())
    assert r.status_code == 409
    assert "ainda nao ha resultado" in r.json()["detail"]
    cli.post(f"/v1/tarefas/{tid}/cancelar", headers=cab())


def test_consulta_de_resultado_quando_terminal(cli):
    tid = cli.post("/v1/tarefas", headers=cab(), json=REQ).json()["task_id"]
    ate_terminal(cli, tid, cab())
    r = cli.get(f"/v1/tarefas/{tid}/resultado", headers=cab())
    assert r.status_code == 200
    assert r.json()["status"] == S.CONCLUIDA


def test_tarefa_desconhecida_e_404(cli):
    assert cli.get("/v1/tarefas/T-naoexiste", headers=cab()).status_code == 404
    assert cli.get("/v1/tarefas/T-naoexiste/resultado",
                   headers=cab()).status_code == 404


# ── cancelamento ────────────────────────────────────────────────────────────

def test_cancelamento_para_a_tarefa_em_execucao(monta):
    cli = TestClient(monta(propositor_lento))
    tid = cli.post("/v1/tarefas", headers=cab(),
                   json={**REQ, "max_iteracoes": 100}).json()["task_id"]
    time.sleep(0.4)                    # deixa entrar em EXECUTANDO
    r = cli.post(f"/v1/tarefas/{tid}/cancelar", headers=cab())
    assert r.status_code == 200
    d = ate_terminal(cli, tid, cab())
    assert d["status"] == S.CANCELADA
    # Uma tarefa que o operador mandou parar NAO concluiu nada.
    assert d["status"] != S.CONCLUIDA


def test_cancelar_tarefa_ja_terminal_nao_e_erro(cli):
    tid = cli.post("/v1/tarefas", headers=cab(), json=REQ).json()["task_id"]
    ate_terminal(cli, tid, cab())
    r = cli.post(f"/v1/tarefas/{tid}/cancelar", headers=cab())
    assert r.status_code == 200
    # Continua CONCLUIDA: terminal nao volta.
    assert r.json()["status"] == S.CONCLUIDA


def test_terminal_nao_volta_para_executando():
    """A garantia que o cancelamento depende: TRANSICOES nao tem caminho de volta."""
    for t in S.TERMINAIS:
        assert S.TRANSICOES[t] == ()


# ── idempotencia ────────────────────────────────────────────────────────────

def test_reenvio_com_mesmo_request_id_nao_duplica(cli):
    h = cab(**{"X-Request-Id": "req-abc-123"})
    a = cli.post("/v1/tarefas", headers=h, json=REQ).json()
    b = cli.post("/v1/tarefas", headers=h, json=REQ).json()
    assert a["task_id"] == b["task_id"]
    assert cli.get("/v1/tarefas/" + a["task_id"], headers=cab()).status_code == 200


def test_sem_request_id_cada_envio_e_uma_tarefa(cli):
    a = cli.post("/v1/tarefas", headers=cab(), json=REQ).json()["task_id"]
    b = cli.post("/v1/tarefas", headers=cab(), json=REQ).json()["task_id"]
    assert a != b


def test_mesmo_request_id_de_clientes_diferentes_nao_colide(monta):
    cli = TestClient(monta(tokens=f"acme:{TOKEN},globex:{TOKEN_B}"))
    ha = cab(TOKEN,   **{"X-Request-Id": "mesmo-id"})
    hb = cab(TOKEN_B, **{"X-Request-Id": "mesmo-id"})
    a = cli.post("/v1/tarefas", headers=ha, json=REQ).json()["task_id"]
    b = cli.post("/v1/tarefas", headers=hb, json=REQ).json()["task_id"]
    assert a != b


# ── correlation id ──────────────────────────────────────────────────────────

def test_correlation_id_volta_em_toda_consulta(cli):
    h = cab(**{"X-Correlation-Id": "corr-xyz-789"})
    tid = cli.post("/v1/tarefas", headers=h, json=REQ).json()["task_id"]
    d = ate_terminal(cli, tid, cab())
    assert d["correlation_id"] == "corr-xyz-789"
    assert d["task_id"] == tid


def test_correlation_id_fica_no_header_e_nao_no_contrato(cli):
    """
    `TarefaRequest v1` recusa campo desconhecido de proposito. Se
    `correlation_id` fosse do corpo, ou o contrato mudava ou o cliente levava
    422 por mandar rastreio — por isso ele viaja em header.
    """
    r = cli.post("/v1/tarefas", headers=cab(),
                 json={**REQ, "correlation_id": "no-corpo"})
    assert r.status_code == 422
    assert "desconhecidos" in r.json()["detail"]


# ── isolamento ──────────────────────────────────────────────────────────────

def test_um_cliente_nao_le_a_tarefa_do_outro(monta):
    """
    404, nao 403. Devolver 403 diria ao cliente que aquele `task_id` existe em
    algum lugar — e `task_id` nao e segredo, e devolvido a quem submeteu.
    """
    cli = TestClient(monta(tokens=f"acme:{TOKEN},globex:{TOKEN_B}"))
    tid = cli.post("/v1/tarefas", headers=cab(TOKEN), json=REQ).json()["task_id"]
    assert cli.get(f"/v1/tarefas/{tid}", headers=cab(TOKEN_B)).status_code == 404
    assert cli.get(f"/v1/tarefas/{tid}/resultado",
                   headers=cab(TOKEN_B)).status_code == 404
    assert cli.post(f"/v1/tarefas/{tid}/cancelar",
                    headers=cab(TOKEN_B)).status_code == 404
    # e o dono continua lendo normalmente
    assert cli.get(f"/v1/tarefas/{tid}", headers=cab(TOKEN)).status_code == 200


def test_duas_tarefas_simultaneas_nao_misturam_estado(cli):
    """
    Objetivos distintos, ids distintos, observacoes distintas. Se o servico
    guardasse estado global em vez de por tarefa, isto acusaria.
    """
    ids = []
    for n in range(4):
        d = cli.post("/v1/tarefas", headers=cab(),
                     json={**REQ, "objetivo": f"tarefa numero {n}"}).json()
        ids.append((n, d["task_id"]))
    assert len({t for _, t in ids}) == 4
    for n, tid in ids:
        d = ate_terminal(cli, tid, cab())
        assert d["objetivo"] == f"tarefa numero {n}"
        assert d["task_id"] == tid
        assert d["status"] == S.CONCLUIDA
        assert len(d["observacoes"]) == 1
        assert d["observacoes"][0]["tarefa_id"] == tid


def test_task_id_hostil_nao_escapa_da_raiz(cli):
    """
    O `task_id` compoe caminho em disco. `../outro/x` leria registro alheio —
    a defesa e recusar o id, nao normalizar o caminho depois.
    """
    for hostil in ("../outro", "..%2Foutro", "a/../../b"):
        r = cli.get(f"/v1/tarefas/{hostil}", headers=cab())
        assert r.status_code in (404, 400), (hostil, r.status_code)


# ── desconexao ──────────────────────────────────────────────────────────────

def test_tarefa_sobrevive_ao_cliente_sumir(app):
    """
    A execucao deixou de morar dentro da requisicao — entao o cliente cair no
    meio nao pode levar a tarefa junto. Um cliente novo le o mesmo registro.
    """
    c1 = TestClient(app)
    tid = c1.post("/v1/tarefas", headers=cab(), json=REQ).json()["task_id"]
    c1.close()                                   # o cliente some
    c2 = TestClient(app)                         # outro chega depois
    d = ate_terminal(c2, tid, cab())
    assert d["status"] == S.CONCLUIDA
    assert len(d["observacoes"]) == 1


def test_registro_sobrevive_em_disco_a_um_servico_novo(tmp_path):
    """
    Persistencia de verdade: outro `TaskService` sobre a MESMA raiz le o que o
    primeiro gravou. Se o registro vivesse em memoria, isto falharia — e era
    exatamente esse o defeito da primeira versao.
    """
    svc = S.TaskService(tmp_path / "t", Politica(nivel_maximo=Nivel.OBSERVAR),
                        [ProvedorFake()], propositor_de_um_passo)
    r = svc.submete(dict(REQ))
    fim = time.time() + 8
    while time.time() < fim and not (svc.estado(r.task_id) or r).terminal:
        time.sleep(0.05)
    svc.encerra()

    outro = S.TaskService(tmp_path / "t", Politica(nivel_maximo=Nivel.OBSERVAR),
                          [ProvedorFake()], propositor_de_um_passo)
    lido = outro.estado(r.task_id)
    assert lido is not None
    assert lido.status == S.CONCLUIDA
    assert lido.task_id == r.task_id
    outro.encerra()


# ── transporte indisponivel ─────────────────────────────────────────────────

def test_transporte_indisponivel_falha_alto_e_nao_em_silencio():
    """
    Porta fechada tem de dar erro de conexao, nao resposta vazia que o cliente
    confunda com "nao ha tarefa". A pagina de teste depende disto: o `catch`
    dela escreve "falha de rede", e so escreve porque o erro chega.
    """
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()                                    # porta agora fechada
    with pytest.raises((ConnectionRefusedError, OSError)):
        with socket.create_connection(("127.0.0.1", porta), timeout=2):
            pass


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


def test_requisicao_recusada_nao_deixa_registro(cli):
    """
    Uma requisicao invalida nao vira tarefa, e nao pode deixar rastro
    consultavel como se tivesse virado.
    """
    antes = cli.post("/v1/tarefas", headers=cab(), json=REQ).json()["task_id"]
    cli.post("/v1/tarefas", headers=cab(),
             json={"objetivo": "x", "capacidades": ["act.click"]})
    ate_terminal(cli, antes, cab())
    svc = cli.app.state.servico
    assert len(svc.registro.lista()) == 1


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
        **REQ, "max_segundos": T.TETO_SEGUNDOS + 1})
    assert r.status_code == 422
    assert "resultado parcial" in r.json()["detail"]


def test_capacidades_mostram_l1_l2_como_recusadas(cli):
    d = cli.get("/v1/capacidades", headers=cab()).json()
    por_nome = {c["nome"]: c for c in d["capacidades"]}
    assert por_nome["analyze.json"]["aceita"] is True
    # L1/L2 aparecem de proposito: o cliente precisa saber que existem e estao
    # recusadas, senao repete o pedido achando que errou o nome.
    assert por_nome["act.click"]["aceita"] is False
    assert por_nome["act.navigate"]["aceita"] is False
    assert "acima do teto" in por_nome["act.navigate"]["motivo"]


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
