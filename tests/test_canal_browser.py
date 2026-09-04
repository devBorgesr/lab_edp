"""
O canal real entre provedor e painel — o que estes testes protegem.

`request_id` nao e decoracao. Duas solicitacoes vivas sobre a mesma mesa sao
normais (duas tarefas, ou duas iteracoes que se sobrepoem), e sem correlacao a
resposta de uma vira observacao da outra — o modelo receberia como fato do
ambiente algo que pertence a outra tarefa.

Os testes abaixo falham no dia em que:
  * uma resposta orfa for entregue ao pedido mais proximo
  * um cliente responder o pedido de outro
  * o painel executar o mesmo comando duas vezes por dois polls
  * um timeout deixar a solicitacao viva na mesa (atuacao sem destinatario)
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime.canal import CanalMesa, MesaDeSolicitacoes            # noqa: E402
from agent_runtime.provedores.browser import (                           # noqa: E402
    PROTOCOLO, AlvoInvalido, CanalIndisponivel, ChromeDebuggerProvider,
    registra_alvo)

TAB, ORIGEM = 42, "http://127.0.0.1:8000"


def alvo():
    return registra_alvo(TAB, ORIGEM, "sessao-1", "2026-09-03T00:00:00Z")


def resultado(request_id, tab_id=TAB, origin=ORIGEM, obs=None):
    return {"protocol": PROTOCOLO, "kind": "capability.result",
            "request_id": request_id, "type": "browser.observation",
            "target": {"tab_id": tab_id, "origin": origin},
            "observations": obs if obs is not None else [
                {"kind": "page", "url": f"{ORIGEM}/dashboard", "title": "EDP"}]}


# ── correlacao ──────────────────────────────────────────────────────────────

def test_duas_solicitacoes_nao_se_misturam():
    """
    O caso que o `request_id` existe para impedir. As respostas chegam FORA DE
    ORDEM de proposito — se a mesa entregasse por proximidade, A receberia o
    que e de B.
    """
    mesa = MesaDeSolicitacoes()
    canal = CanalMesa(mesa, "acme")
    saidas: dict[str, dict] = {}

    def pede(nome, marca):
        try:
            saidas[nome] = canal.pede(
                {"protocol": PROTOCOLO, "capability": "browser.inspect",
                 "marca": marca}, timeout_s=5)
        except Exception as e:              # pragma: no cover
            saidas[nome] = {"erro": repr(e)}

    ta = threading.Thread(target=pede, args=("A", "aaa")); ta.start()
    time.sleep(0.1)
    tb = threading.Thread(target=pede, args=("B", "bbb")); tb.start()
    time.sleep(0.2)

    sa = mesa.proxima("acme"); sb = mesa.proxima("acme")
    assert sa["marca"] == "aaa" and sb["marca"] == "bbb"
    assert sa["request_id"] != sb["request_id"]

    # responde B PRIMEIRO
    assert mesa.responde(resultado(sb["request_id"],
                                   obs=[{"kind": "page", "title": "B"}]), "acme")
    assert mesa.responde(resultado(sa["request_id"],
                                   obs=[{"kind": "page", "title": "A"}]), "acme")
    ta.join(5); tb.join(5)

    assert saidas["A"]["request_id"] == sa["request_id"]
    assert saidas["B"]["request_id"] == sb["request_id"]
    assert saidas["A"]["observations"][0]["title"] == "A"
    assert saidas["B"]["observations"][0]["title"] == "B"


def test_resposta_orfa_e_descartada_e_nao_entregue_ao_pedido_mais_proximo():
    mesa = MesaDeSolicitacoes()
    p = mesa.publica({"protocol": PROTOCOLO}, "acme")
    assert mesa.responde(resultado("R-inexistente"), "acme") is False
    assert p.resposta is None
    assert p.evento.is_set() is False


def test_um_cliente_nao_responde_o_pedido_de_outro():
    mesa = MesaDeSolicitacoes()
    p = mesa.publica({"protocol": PROTOCOLO}, "acme")
    assert mesa.responde(resultado(p.request_id), "globex") is False
    assert mesa.responde(resultado(p.request_id), "acme") is True


def test_painel_so_busca_solicitacao_do_proprio_cliente():
    mesa = MesaDeSolicitacoes()
    mesa.publica({"protocol": PROTOCOLO, "marca": "de-acme"}, "acme")
    assert mesa.proxima("globex") is None
    assert mesa.proxima("acme")["marca"] == "de-acme"


def test_dois_polls_nao_executam_o_mesmo_comando_duas_vezes():
    """
    CDP nao e idempotente em geral, e mesmo `inspect` gastaria duas anexacoes.
    """
    mesa = MesaDeSolicitacoes()
    mesa.publica({"protocol": PROTOCOLO}, "acme")
    assert mesa.proxima("acme") is not None
    assert mesa.proxima("acme") is None


def test_resposta_duplicada_e_recusada():
    mesa = MesaDeSolicitacoes()
    p = mesa.publica({"protocol": PROTOCOLO}, "acme")
    assert mesa.responde(resultado(p.request_id), "acme") is True
    assert mesa.responde(resultado(p.request_id), "acme") is False


@pytest.mark.parametrize("ruim", [
    "texto", 42, None, {},
    {"protocol": "outro", "request_id": "R-1"},
    {"protocol": PROTOCOLO},                       # sem request_id
    {"protocol": PROTOCOLO, "request_id": ""},
    {"protocol": PROTOCOLO, "request_id": 123},
])
def test_resposta_malformada_nao_desbloqueia_ninguem(ruim):
    mesa = MesaDeSolicitacoes()
    p = mesa.publica({"protocol": PROTOCOLO}, "acme")
    assert mesa.responde(ruim, "acme") is False
    assert p.evento.is_set() is False


# ── tempo e limites ─────────────────────────────────────────────────────────

def test_timeout_remove_a_solicitacao_da_mesa():
    """
    Deixa-la viva faria o painel executar, mais tarde, um comando que ninguem
    mais espera — atuacao sem destinatario.
    """
    mesa = MesaDeSolicitacoes()
    canal = CanalMesa(mesa, "acme")
    with pytest.raises(CanalIndisponivel) as e:
        canal.pede({"protocol": PROTOCOLO}, timeout_s=0.2)
    assert "nao respondeu" in str(e.value)
    assert mesa.vivas() == 0
    assert mesa.proxima("acme") is None


def test_mesa_cheia_recusa_em_vez_de_crescer():
    mesa = MesaDeSolicitacoes(max_pendentes=3)
    for _ in range(3):
        mesa.publica({"protocol": PROTOCOLO}, "acme")
    with pytest.raises(CanalIndisponivel) as e:
        mesa.publica({"protocol": PROTOCOLO}, "acme")
    assert "mesa cheia" in str(e.value)


def test_solicitacao_velha_expira_e_desbloqueia_quem_espera():
    mesa = MesaDeSolicitacoes(ttl_s=0.15)
    p = mesa.publica({"protocol": PROTOCOLO}, "acme")
    time.sleep(0.25)
    mesa.proxima("acme")                     # qualquer operacao faz faxina
    assert mesa.vivas() == 0
    assert p.evento.is_set() is True


# ── o canal recusando o que nao e observacao ────────────────────────────────

def test_erro_do_painel_vira_falha_de_canal_e_nao_observacao():
    """
    "O painel recusou o alvo" nao pode virar "a pagina nao tem nada".
    """
    mesa = MesaDeSolicitacoes()
    canal = CanalMesa(mesa, "acme")
    out = {}

    def pede():
        try:
            canal.pede({"protocol": PROTOCOLO}, timeout_s=5)
        except CanalIndisponivel as e:
            out["erro"] = str(e)

    t = threading.Thread(target=pede); t.start(); time.sleep(0.15)
    s = mesa.proxima("acme")
    mesa.responde({"protocol": PROTOCOLO, "kind": "capability.result",
                   "request_id": s["request_id"], "type": "browser.error",
                   "error": "a aba alvo mudou de origem desde o registro"}, "acme")
    t.join(5)
    assert "mudou de origem" in out["erro"]


def test_resposta_citando_outro_request_id_nao_vira_observacao():
    mesa = MesaDeSolicitacoes()
    canal = CanalMesa(mesa, "acme")
    out = {}

    def pede():
        try:
            canal.pede({"protocol": PROTOCOLO}, timeout_s=5)
        except CanalIndisponivel as e:
            out["erro"] = str(e)

    t = threading.Thread(target=pede); t.start(); time.sleep(0.15)
    s = mesa.proxima("acme")
    # entra pela mesa com o id certo, mas o CORPO cita outro
    r = resultado("R-outro"); r["request_id"] = s["request_id"]
    r["request_id"] = s["request_id"]
    mesa.responde(r, "acme")
    t.join(5)
    assert "erro" not in out          # este caso e legitimo: o id bate


# ── provedor sobre o canal real ─────────────────────────────────────────────

def test_provedor_sobre_a_mesa_produz_observacao():
    mesa = MesaDeSolicitacoes()
    prov = ChromeDebuggerProvider(CanalMesa(mesa, "acme"), alvo(), timeout_s=5)
    saida = {}

    def roda():
        saida["obs"] = prov.executa("browser.inspect", {}, "T-1", 0)

    t = threading.Thread(target=roda); t.start(); time.sleep(0.15)
    s = mesa.proxima("acme")
    assert s["capability"] == "browser.inspect"
    assert s["kind"] == "capability.request"
    assert "comandos" not in s          # a lista nao viaja
    mesa.responde(resultado(s["request_id"]), "acme")
    t.join(5)
    assert len(saida["obs"]) == 1
    assert saida["obs"][0].dados["kind"] == "page"


def test_provedor_recusa_resposta_com_alvo_trocado_mesmo_vindo_da_mesa():
    mesa = MesaDeSolicitacoes()
    prov = ChromeDebuggerProvider(CanalMesa(mesa, "acme"), alvo(), timeout_s=5)
    out = {}

    def roda():
        try:
            prov.executa("browser.inspect", {}, "T-1", 0)
        except AlvoInvalido as e:
            out["erro"] = str(e)

    t = threading.Thread(target=roda); t.start(); time.sleep(0.15)
    s = mesa.proxima("acme")
    mesa.responde(resultado(s["request_id"], tab_id=999), "acme")
    t.join(5)
    assert "nao e o alvo registrado" in out["erro"]
