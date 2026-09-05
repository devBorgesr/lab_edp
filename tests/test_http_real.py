"""
O transporte atravessando a camada HTTP DE VERDADE — uvicorn, socket, sem
TestClient.

POR QUE ESTE ARQUIVO EXISTE

O primeiro smoke em Chrome real (05/09/2026) achou um defeito que 592 testes
nao pegaram: `GET /v1/browser/solicitacoes` devolvia `JSONResponse(None)` com
status 204. O corpo `null` tem 4 bytes; 204 exige corpo vazio. O uvicorn
recusa com

    RuntimeError: Response content longer than Content-Length

e DERRUBA a requisicao. Do lado do painel isso chega como
`ERR_CONNECTION_REFUSED` / `Failed to fetch` — que aponta para o Runtime estar
fora do ar, e nao para um corpo de resposta malformado.

`TestClient` nao pegava porque fala ASGI direto: nao ha protocolo HTTP, nao ha
Content-Length, nao ha uvicorn. Toda a classe de defeito "a resposta e valida
como objeto ASGI mas invalida como HTTP" passava batida.

Estes testes sobem uvicorn num processo real e falam por socket.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

TOKEN = "token-do-http-real-com-tamanho-ok"


def porta_livre() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="module")
def servidor(tmp_path_factory):
    """uvicorn de verdade, em processo proprio."""
    porta = porta_livre()
    raiz = tmp_path_factory.mktemp("http_real")
    env = {**os.environ, "AGENT_RUNTIME_TOKEN": TOKEN,
           "PYTHONPATH": str(RAIZ), "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "agent_runtime", "--propositor", "eco",
         "--porta", str(porta), "--browser", "--raiz", str(raiz)],
        cwd=str(RAIZ), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    base = f"http://127.0.0.1:{porta}"
    fim = time.time() + 25
    while time.time() < fim:
        if proc.poll() is not None:
            pytest.fail("o Runtime morreu ao subir:\n" + proc.stdout.read())
        try:
            with urllib.request.urlopen(base + "/health", timeout=1):
                break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("o Runtime nao subiu em 25s")

    yield base, proc
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


class Headers(dict):
    """
    Header de HTTP e case-insensitive (RFC 9110). `urllib` normaliza para
    minusculas, entao procurar por "Location" devolve None e o teste acusa
    ausencia de um header que esta la.
    """

    def __init__(self, h):
        super().__init__({k.lower(): v for k, v in dict(h).items()})

    def get(self, nome, default=None):
        return super().get(nome.lower(), default)


def pede(base, caminho, metodo="GET", corpo=None, token=TOKEN):
    r = urllib.request.Request(
        base + caminho, method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=10) as f:
            bruto = f.read()
            return f.status, bruto, Headers(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), Headers(e.headers)


# ── o defeito que o smoke achou ─────────────────────────────────────────────

def test_204_do_poll_nao_tem_corpo(servidor):
    """
    O defeito de 05/09/2026, em uma linha.

    Se voltar `JSONResponse(None)`, o uvicorn levanta
    "Response content longer than Content-Length" e derruba a conexao — e o
    cliente ve erro de REDE por um erro de CORPO.
    """
    base, _ = servidor
    st, corpo, headers = pede(base, "/v1/browser/solicitacoes")
    assert st == 204
    assert corpo == b"", f"204 com corpo de {len(corpo)} bytes: {corpo!r}"
    cl = headers.get("Content-Length")
    assert cl in (None, "0"), f"204 com Content-Length={cl!r}"


def test_o_poll_repetido_nao_derruba_o_servidor(servidor):
    """
    O painel busca em laco. Se cada 204 derruba a requisicao, o painel entra em
    recuo e o operador ve "connection refused" para sempre — foi o sintoma no
    Chrome real.
    """
    base, proc = servidor
    for _ in range(15):
        st, corpo, _ = pede(base, "/v1/browser/solicitacoes")
        assert st == 204 and corpo == b""
    assert proc.poll() is None, "o Runtime morreu durante o laco de poll"


# ── o resto do contrato, agora por socket ───────────────────────────────────

def test_health_sem_token(servidor):
    base, _ = servidor
    st, corpo, _ = pede(base, "/health", token="qualquer")
    assert st == 200
    d = json.loads(corpo)
    assert d["ok"] is True and d["assincrono"] is True


def test_sem_token_401_com_corpo_valido(servidor):
    base, _ = servidor
    st, corpo, _ = pede(base, "/v1/browser/alvo", token="errado")
    assert st == 401
    assert json.loads(corpo)["detail"]


def test_ciclo_do_alvo_por_socket(servidor):
    base, _ = servidor
    st, corpo, _ = pede(base, "/v1/browser/alvo", "POST", {
        "tab_id": 4242, "origin": "http://127.0.0.1:8000",
        "session_id": "S-http", "registrado_em": "2026-09-05T00:00:00Z"})
    assert st == 200 and json.loads(corpo)["estado"] == "REGISTRADO"

    for estado in ("ANEXANDO", "ANEXADO"):
        st, corpo, _ = pede(base, "/v1/browser/alvo/estado", "POST",
                            {"estado": estado})
        assert st == 200 and json.loads(corpo)["estado"] == estado

    st, corpo, _ = pede(base, "/v1/browser/alvo")
    assert json.loads(corpo) == {"estado": "ANEXADO", "operacional": True}


def test_tarefa_completa_por_socket(servidor):
    """
    Submete, atende como o painel atenderia, e le o resultado — tudo por HTTP
    real. Nenhum TestClient no caminho.
    """
    base, _ = servidor
    st, corpo, headers = pede(base, "/v1/tarefas", "POST", {
        "objetivo": "inspecionar pelo http real",
        "capacidades": ["browser.inspect"], "max_iteracoes": 3})
    assert st == 202, corpo
    d = json.loads(corpo)
    tid = d["task_id"]
    assert headers.get("Location") == f"/v1/tarefas/{tid}"

    # o "painel": busca e responde com o MESMO request_id
    atendido = False
    fim = time.time() + 15
    while time.time() < fim and not atendido:
        st, corpo, _ = pede(base, "/v1/browser/solicitacoes")
        if st == 204:
            time.sleep(0.05)
            continue
        ped = json.loads(corpo)
        st2, _, _ = pede(base, "/v1/browser/resultados", "POST", {
            "protocol": "edp.browser.v1", "kind": "capability.result",
            "request_id": ped["request_id"], "type": "browser.observation",
            "target": ped["target"],
            "observations": [
                {"kind": "page", "url": "http://127.0.0.1:8000/dashboard",
                 "title": "EDP"},
                {"kind": "dom", "dom_nodes": 318}]})
        assert st2 == 200
        atendido = True
    assert atendido, "o pedido nunca apareceu no poll"

    fim = time.time() + 15
    while time.time() < fim:
        st, corpo, _ = pede(base, f"/v1/tarefas/{tid}")
        d = json.loads(corpo)
        if d["terminal"]:
            break
        time.sleep(0.05)
    assert d["status"] == "CONCLUIDA", d
    assert len(d["observacoes"]) == 2
    assert all("tab=4242" in o["fonte"] for o in d["observacoes"])

    st, corpo, _ = pede(base, f"/v1/tarefas/{tid}/resultado")
    assert st == 200 and json.loads(corpo)["status"] == "CONCLUIDA"


def test_nenhuma_resposta_carrega_cors_por_socket(servidor):
    base, _ = servidor
    for caminho in ("/health", "/", "/v1/capacidades", "/v1/browser/alvo"):
        _, _, headers = pede(base, caminho)
        nomes = {k.lower() for k in headers}
        assert not any(n.startswith("access-control-") for n in nomes), \
            (caminho, nomes)


# ── CORS para o painel: uma origem exata, ou nenhuma ────────────────────────
#
# `DECISAO_TRANSPORTE.md` previu que, quando o painel virasse cliente, a origem
# passaria a ser `chrome-extension://<id>` e isso teria de ser decisao com nome
# e escopo. Estes testes sao o escopo.

EXT = "chrome-extension://" + "n" * 32


@pytest.fixture(scope="module")
def servidor_cors(tmp_path_factory):
    porta = porta_livre()
    raiz = tmp_path_factory.mktemp("http_cors")
    env = {**os.environ, "AGENT_RUNTIME_TOKEN": TOKEN,
           "PYTHONPATH": str(RAIZ), "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "agent_runtime", "--propositor", "eco",
         "--porta", str(porta), "--browser", "--raiz", str(raiz),
         "--origem-extensao", EXT],
        cwd=str(RAIZ), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{porta}"
    fim = time.time() + 25
    while time.time() < fim:
        if proc.poll() is not None:
            pytest.fail("o Runtime morreu ao subir:\n" + proc.stdout.read())
        try:
            with urllib.request.urlopen(base + "/health", timeout=1):
                break
        except Exception:
            time.sleep(0.2)
    yield base, proc
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def preflight(base, origem, caminho="/v1/browser/solicitacoes"):
    r = urllib.request.Request(base + caminho, method="OPTIONS", headers={
        "Origin": origem, "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type"})
    try:
        with urllib.request.urlopen(r, timeout=10) as f:
            return f.status, Headers(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, Headers(e.headers)


def test_preflight_do_painel_passa_sem_token(servidor_cors):
    """
    O navegador NUNCA manda credencial no preflight. Exigir token no OPTIONS
    garante 401 em todo preflight — foi o que o smoke mostrou, sete seguidos.
    Responder o preflight nao autoriza nada: a requisicao real que vem depois
    passa pela autenticacao normalmente (o teste seguinte prova).
    """
    base, _ = servidor_cors
    st, h = preflight(base, EXT)
    assert st in (200, 204), st
    assert h.get("Access-Control-Allow-Origin") == EXT
    assert "authorization" in h.get("Access-Control-Allow-Headers", "").lower()
    assert h.get("Access-Control-Max-Age")     # corta OPTIONS a cada poll


def test_preflight_respondido_nao_dispensa_token_na_requisicao_real(servidor_cors):
    base, _ = servidor_cors
    st, _, _ = pede(base, "/v1/browser/solicitacoes", token="errado")
    assert st == 401


def test_cors_so_para_a_origem_exata(servidor_cors):
    """Nao ha padrao, nao ha lista, nao ha `*`."""
    base, _ = servidor_cors
    for outra in ("chrome-extension://" + "b" * 32, "https://claude.ai",
                  "http://127.0.0.1:8000", "null"):
        st, h = preflight(base, outra)
        assert h.get("Access-Control-Allow-Origin") is None, (outra, st)


def test_nunca_curinga(servidor_cors):
    base, _ = servidor_cors
    for caminho in ("/health", "/v1/capacidades", "/v1/browser/alvo"):
        _, _, h = pede(base, caminho)
        assert h.get("Access-Control-Allow-Origin") != "*"
    _, h = preflight(base, EXT)
    assert h.get("Access-Control-Allow-Origin") != "*"


def test_sem_a_flag_nao_ha_cors_nenhum(servidor):
    """
    O servidor do resto do arquivo sobe SEM --origem-extensao. Nele, nem
    preflight nem resposta carregam CORS — o comportamento de antes,
    preservado.
    """
    base, _ = servidor
    st, h = preflight(base, EXT)
    assert h.get("Access-Control-Allow-Origin") is None
    _, _, h2 = pede(base, "/v1/capacidades")
    assert h2.get("Access-Control-Allow-Origin") is None
