"""
`browser.inspect` — o vertical slice, e as recusas que o tornam aceitavel.

O que estes testes protegem nao e "o provedor devolve observacao". E o
conjunto de fronteiras que fazem `chrome.debugger` um PROVEDOR DE CAPACIDADE
em vez de um canal CDP aberto:

  * o modelo pede capacidade, nunca comando CDP
  * o alvo vem do REGISTRO, nunca dos parametros da intencao
  * o alvo e conferido na ida E na volta
  * objeto Chrome cru nao vira `Observacao`
  * `browser.inspect` e L0 porque so le — e se um dia avaliar expressao do
    modelo, deixa de ser, e este teste tem de falhar

Ver `docs/agent_runtime/DECISAO_ATUACAO.md`, opcao D.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime import (EstadoTarefa, Executor, Intencao, Nivel,  # noqa: E402
                           Orcamento, Politica, Tarefa)
from agent_runtime.capacidades import busca                          # noqa: E402
from agent_runtime.propositor import ClienteFake, PropositorLLM      # noqa: E402
from agent_runtime.provedores.browser import (                       # noqa: E402
    CAMPOS_OBS, COMANDOS_INSPECT, PROTOCOLO, AlvoInvalido,
    CanalIndisponivel, ChromeDebuggerProvider, registra_alvo)
from agent_runtime.roteador import RoteadorFixo                      # noqa: E402

TAB, ORIGEM = 42, "http://127.0.0.1:8000"


def alvo():
    return registra_alvo(TAB, ORIGEM, "sessao-1", "2026-09-03T00:00:00Z")


def resposta_boa(tab_id=TAB, origin=ORIGEM):
    return {
        "protocol": PROTOCOLO, "kind": "capability.result",
        "type": "browser.observation",
        "target": {"tab_id": tab_id, "origin": origin},
        "observations": [
            {"kind": "page", "url": f"{ORIGEM}/dashboard", "title": "EDP Runtime"},
            {"kind": "dom", "dom_nodes": 318},
        ],
        "timestamp": "2026-09-03T00:00:01Z", "redactions": [],
    }


class CanalFake:
    """Guarda o que foi pedido, para que o teste possa afirmar sobre a ida."""

    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta if resposta is not None else resposta_boa()
        self.erro = erro
        self.pedidos: list[dict] = []

    def pede(self, solicitacao, timeout_s):
        self.pedidos.append(solicitacao)
        if self.erro:
            raise self.erro
        return self.resposta


# ── o nivel ─────────────────────────────────────────────────────────────────

def test_browser_inspect_e_L0_porque_so_le():
    """
    Se alguem promover esta capacidade a receber expressao do modelo, ela deixa
    de ser observacao — e este teste tem de falhar junto, no mesmo commit.
    """
    c = busca("browser.inspect")
    assert c.nivel is Nivel.OBSERVAR
    assert c.implementada is True
    assert c.reversivel is True


def test_a_lista_de_comandos_cdp_e_fechada_e_so_de_leitura():
    proibidos = ("Input.", "Page.navigate", "Page.reload", "Network.emulate",
                 "Browser.", "Storage.clear")
    for cmd in COMANDOS_INSPECT:
        assert not any(cmd.startswith(p) for p in proibidos), cmd


# ── o alvo ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("origem", [
    "https://claude.ai", "http://exemplo.invalido", "http://10.0.0.5:8000",
    "https://127.0.0.1:8000", "", None,
])
def test_alvo_fora_do_loopback_e_recusado_no_registro(origem):
    with pytest.raises(AlvoInvalido):
        registra_alvo(1, origem, "s", "t")


def test_o_alvo_nao_vem_dos_parametros_da_intencao(  ):
    """
    O modelo propoe parametros. Se ele mandar outro `tab_id`, isso e recusa —
    nunca substituicao do alvo registrado.
    """
    p = ChromeDebuggerProvider(CanalFake(), alvo())
    with pytest.raises(AlvoInvalido):
        p.executa("browser.inspect", {"tab_id": 999}, "T-1", 0)
    with pytest.raises(AlvoInvalido):
        p.executa("browser.inspect", {"origin": "https://claude.ai"}, "T-1", 0)


def test_alvo_e_conferido_tambem_na_volta():
    """
    A extensao pode ter anexado noutra aba — por defeito, ou por corrida com o
    usuario trocando de aba. Conferir so na ida deixaria isso passar.
    """
    canal = CanalFake(resposta_boa(tab_id=777))
    p = ChromeDebuggerProvider(canal, alvo())
    with pytest.raises(AlvoInvalido):
        p.executa("browser.inspect", {}, "T-1", 0)


def test_solicitacao_leva_alvo_e_lista_de_comandos():
    canal = CanalFake()
    ChromeDebuggerProvider(canal, alvo()).executa("browser.inspect", {}, "T-1", 0)
    s = canal.pedidos[0]
    assert s["protocol"] == PROTOCOLO
    assert s["capability"] == "browser.inspect"
    assert s["kind"] == "capability.request"
    assert s["target"] == {"tab_id": TAB, "origin": ORIGEM, "session_id": "sessao-1"}
    # A lista de comandos NAO viaja: o controller tem a dele. Mandar a lista
    # criaria superficie para influenciar quais comandos rodam.
    assert "comandos" not in s
    # A capacidade nao recebe parametro do modelo: nada dele viaja.
    assert s["parameters"] == {}


# ── a fronteira de dados ────────────────────────────────────────────────────

def test_observacao_normalizada_descarta_campo_desconhecido():
    """
    Objeto Chrome cru nao atravessa. Uma mudanca do lado do navegador nao pode
    virar dado novo dentro da Observacao sem alguem decidir.
    """
    r = resposta_boa()
    r["observations"][0]["cookies"] = "sess=SEGREDO"
    r["observations"][0]["__proto__"] = {"x": 1}
    obs = ChromeDebuggerProvider(CanalFake(r), alvo()).executa(
        "browser.inspect", {}, "T-1", 0)
    todos = {k for o in obs for k in o.dados}
    assert todos <= CAMPOS_OBS, todos
    assert "cookies" not in todos
    assert not any("SEGREDO" in str(o.dados) for o in obs)


def test_observacao_carrega_a_fonte_e_o_hash():
    obs = ChromeDebuggerProvider(CanalFake(), alvo()).executa(
        "browser.inspect", {}, "T-7", 3)
    assert len(obs) == 2
    assert all(o.tarefa_id == "T-7" and o.iteracao == 3 for o in obs)
    assert all(f"tab={TAB}" in o.fonte for o in obs)
    assert all(o.hash() for o in obs)


@pytest.mark.parametrize("ruim", [
    "isto nao e objeto", 42, [],
    {"protocol": "outro", "kind": "capability.result", "type": "browser.observation"},
    {"protocol": PROTOCOLO, "kind": "capability.result", "type": "qualquer.coisa"},
    {"protocol": PROTOCOLO, "kind": "outra.coisa", "type": "browser.observation"},
])
def test_resposta_malformada_e_falha_de_canal_e_nao_observacao(ruim):
    p = ChromeDebuggerProvider(CanalFake(ruim), alvo())
    with pytest.raises((CanalIndisponivel, AlvoInvalido)):
        p.executa("browser.inspect", {}, "T-1", 0)


def test_zero_observacoes_vira_fato_registrado_e_nao_silencio():
    r = resposta_boa(); r["observations"] = []
    obs = ChromeDebuggerProvider(CanalFake(r), alvo()).executa(
        "browser.inspect", {}, "T-1", 0)
    assert len(obs) == 1
    assert "0 observacoes" in obs[0].dados["erro"]


def test_canal_fora_do_ar_nao_vira_veredito_sobre_a_pagina():
    """
    Falha de transporte e falha de transporte. Devolver observacao vazia aqui
    diria ao modelo que a pagina nao tem nada — que e outra coisa.
    """
    p = ChromeDebuggerProvider(CanalFake(erro=TimeoutError("sem resposta")), alvo())
    with pytest.raises(CanalIndisponivel):
        p.executa("browser.inspect", {}, "T-1", 0)


def test_outra_capacidade_e_recusada_por_este_provedor():
    p = ChromeDebuggerProvider(CanalFake(), alvo())
    for cap in ("act.click", "browser.evaluate", "observe.network"):
        with pytest.raises(AlvoInvalido):
            p.executa(cap, {}, "T-1", 0)


# ── o vertical slice, ponta a ponta ─────────────────────────────────────────

def test_slice_completo_ate_concluida():
    """
    ClienteFake -> RoteadorFixo -> Tarefa -> Executor -> browser.inspect
    -> provedor -> Observacao -> CONCLUIDA.
    """
    canal = CanalFake()
    provedor = ChromeDebuggerProvider(canal, alvo())
    propositor = PropositorLLM(
        cliente=ClienteFake([
            '{"capacidade":"browser.inspect","parametros":{},'
            ' "porque":"ver o estado do dashboard"}',
            '{"concluir":true,"porque":"dashboard inspecionado"}']),
        roteador=RoteadorFixo("modelo-fake-1", tier=1))

    tarefa = Tarefa(objetivo="inspecionar o dashboard do EDP",
                    capacidades=["browser.inspect"],
                    orcamento=Orcamento(max_iteracoes=5),
                    criada_por="teste")
    res = Executor(Politica(nivel_maximo=Nivel.OBSERVAR), [provedor]).roda(
        tarefa, propositor)

    assert tarefa.estado is EstadoTarefa.CONCLUIDA
    assert tarefa.motivo_parada == "dashboard inspecionado"
    assert res.negadas == []
    assert len(res.observacoes) == 2
    assert {o.dados.get("kind") for o in res.observacoes} == {"page", "dom"}
    assert canal.pedidos, "o canal nao foi usado — o provedor nao entrou no laco"
    assert propositor.trilha, "o Roteador nao foi consultado"


def test_a_politica_nega_capacidade_L1_mesmo_com_provedor_montado():
    """
    O provedor existir nao autoriza nada acima do teto. Quem decide e a
    Politica, e ela nega antes de o provedor ser chamado.
    """
    canal = CanalFake()
    pol = Politica(nivel_maximo=Nivel.OBSERVAR)
    d = pol.avalia(Tarefa(objetivo="x", capacidades=["browser.inspect"],
                          orcamento=Orcamento(max_iteracoes=3)), "act.click", {})
    assert d.pode_executar is False
    assert canal.pedidos == []
