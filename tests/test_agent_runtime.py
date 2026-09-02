"""
Agent Runtime — o que estes testes protegem nao e "o loop roda".

E a INVERSAO DE AUTORIDADE: o modelo propoe, o kernel decide. Se um dia
alguem simplificar o executor e deixar a intencao virar acao direta, o
sistema continua funcionando — e vira exatamente o agente com ferramentas
que este desenho existe para nao ser. Os testes abaixo falham nesse dia.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime import (EstadoTarefa, Executor, Intencao, Nivel,  # noqa: E402
                           Orcamento, Politica, Tarefa, Veredito, deriva)
from agent_runtime.capacidades import (CapacidadeDesconhecida,       # noqa: E402
                                       CapacidadeNaoImplementada,
                                       exige_implementada)
from agent_runtime.contrato import Observacao, ProvedorDeCapacidade  # noqa: E402
from agent_runtime.provedores.har import ProvedorHAR                 # noqa: E402


# ── um HAR de verdade, no formato que o Exportador grava ────────────────────

@pytest.fixture
def har(tmp_path) -> Path:
    doc = {"log": {"version": "1.2",
                   "creator": {"name": "Claude Exporter — Copiloto (Fase 4)"},
                   "entries": [
        {"request": {"url": "https://api.exemplo/search?q=x", "method": "POST",
                     "headers": [{"name": "authorization", "value": "Bearer SEGREDO"},
                                 {"name": "content-type", "value": "application/json"}]},
         "response": {"status": 403,
                      "headers": [{"name": "set-cookie", "value": "sess=SEGREDO"}],
                      "content": {"mimeType": "application/json", "size": 91}}},
        {"request": {"url": "https://api.exemplo/health", "method": "GET",
                     "headers": []},
         "response": {"status": 200, "headers": [],
                      "content": {"mimeType": "application/json", "size": 12}}},
    ]}}
    p = tmp_path / "sessao.har"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


# ── a inversao de autoridade ────────────────────────────────────────────────

def test_modelo_nao_executa_capacidade_nao_declarada(har):
    """
    O modelo propoe algo fora do que a tarefa declarou. A politica NEGA — e o
    loop continua, porque negar nao e falhar: o modelo pode contornar dentro
    do que ele PODE fazer.
    """
    t = Tarefa(objetivo="ver rede", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=3))
    ex = Executor(Politica(), [ProvedorHAR(har)])

    def propoe(tarefa, obs):
        if tarefa.iteracao == 0:
            return Intencao("analyze.json", {"corpo": "{}"}, "fora do escopo")
        return Intencao("observe.network", {"status": 403}, "dentro do escopo")

    r = ex.roda(t, propoe)
    assert "analyze.json" in r.negadas
    assert any(o.capacidade == "observe.network" for o in r.observacoes)


def test_capacidade_L1_nao_roda_sem_aprovacao(har):
    """
    L1 altera a pagina do usuario. Sem aprovador, a tarefa nem e admitida —
    e a parada e BLOQUEADA, nao FALHA: nada quebrou, a autoridade recusou.
    """
    t = Tarefa(objetivo="clicar", capacidades=["act.click"],
               orcamento=Orcamento(max_iteracoes=5))
    r = Executor(Politica(), [ProvedorHAR(har)]).roda(
        t, lambda tarefa, obs: Intencao("act.click", {}))
    assert t.estado is EstadoTarefa.BLOQUEADA
    assert "admissao" in t.motivo_parada


def test_aprovador_explicito_e_o_unico_caminho_para_L1():
    p_sem = Politica()
    p_com = Politica(aprovador=lambda c, par: True)
    t = Tarefa(objetivo="x", capacidades=["act.click"],
               orcamento=Orcamento(max_iteracoes=1))
    assert p_sem.admite_tarefa(t).veredito is Veredito.EXIGE_APROVACAO
    assert p_com.admite_tarefa(t).veredito is Veredito.PERMITE


def test_politica_default_so_observa():
    """Uma politica criada por acidente ainda so observa."""
    assert Politica().nivel_maximo is Nivel.OBSERVAR


def test_toda_decisao_fica_na_trilha(har):
    t = Tarefa(objetivo="ver", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=2))
    p = Politica()
    Executor(p, [ProvedorHAR(har)]).roda(
        t, lambda tarefa, obs: Intencao("observe.network", {}))
    assert p.trilha and all(
        {"tarefa", "capacidade", "veredito", "motivo"} <= set(d) for d in p.trilha)


# ── a fronteira de seguranca do Exportador, como codigo ─────────────────────

@pytest.mark.parametrize("cap", ["act.click", "act.fill", "act.javascript",
                                 "act.reload", "act.navigate", "act.download",
                                 "act.network"])
def test_atuacao_declarada_e_nao_implementada(cap):
    """
    `debugger_capturer.js` diz, no proprio codigo: nunca Input.*,
    Page.navigate, Page.reload ou qualquer comando que ALTERE a aba.
    Implementar qualquer uma destas rompe essa fronteira — e isso e decisao
    do pesquisador, nao consequencia de alguem ter escrito codigo.
    """
    with pytest.raises(CapacidadeNaoImplementada, match="DECISAO_ATUACAO"):
        exige_implementada(cap)


def test_provedor_nao_inventa_capacidade():
    with pytest.raises(CapacidadeDesconhecida):
        Tarefa(objetivo="x", capacidades=["act.telepatia"],
               orcamento=Orcamento(max_iteracoes=1))


# ── orcamento: um loop sem teto nao e autonomo ──────────────────────────────

def test_loop_para_no_teto_de_iteracoes(har):
    t = Tarefa(objetivo="loop infinito", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=4))
    r = Executor(Politica(), [ProvedorHAR(har)]).roda(
        t, lambda tarefa, obs: Intencao("observe.network", {}))
    assert t.estado is EstadoTarefa.ESGOTADA
    assert t.iteracao == 4 and "orcamento" in t.motivo_parada


def test_teto_duro_de_iteracoes():
    with pytest.raises(ValueError, match="teto duro"):
        Orcamento(max_iteracoes=101)


def test_toda_parada_tem_motivo(har):
    for prop, esperado in [
        (lambda t, o: Intencao("observe.network", {}, concluir=False), EstadoTarefa.ESGOTADA),
        (lambda t, o: Intencao("", {}, "achei", concluir=True), EstadoTarefa.CONCLUIDA),
    ]:
        t = Tarefa(objetivo="x", capacidades=["observe.network"],
                   orcamento=Orcamento(max_iteracoes=2))
        Executor(Politica(), [ProvedorHAR(har)]).roda(t, prop)
        assert t.estado is esperado and t.motivo_parada


# ── o provedor HAR: a uniao que ja existe ───────────────────────────────────

def test_le_o_har_do_exportador_e_filtra(har):
    obs = ProvedorHAR(har).executa("observe.network", {"status": 403}, "T-1", 0)
    assert len(obs) == 1
    assert obs[0].dados["url"].endswith("/search?q=x")
    assert obs[0].dados["status"] == 403


def test_redige_de_novo_mesmo_que_a_origem_ja_tenha_redigido(har):
    """
    Um HAR salvo pelo DevTools do usuario ("Save all as HAR") vem COM cookie e
    authorization. Confiar na origem seria confiar num arquivo que qualquer
    um pode ter produzido de outro jeito.
    """
    obs = ProvedorHAR(har).executa("observe.network", {}, "T-1", 0)
    bruto = json.dumps([o.to_dict() for o in obs], ensure_ascii=False)
    assert "SEGREDO" not in bruto
    assert "[REDIGIDO]" in bruto


def test_nada_encontrado_e_observacao_nao_silencio(har):
    obs = ProvedorHAR(har).executa("observe.network", {"status": 999}, "T-1", 0)
    assert len(obs) == 1 and obs[0].dados["vazio"] is True
    assert obs[0].dados["total_no_har"] == 2


def test_console_declara_indisponibilidade_em_vez_de_vazio_mudo(har):
    obs = ProvedorHAR(har).executa("observe.console", {}, "T-1", 0)
    assert obs[0].dados["indisponivel"] is True and obs[0].dados["porque"]


# ── proveniencia ────────────────────────────────────────────────────────────

def test_observacao_e_imutavel_e_tem_hash_por_conteudo(har):
    o = ProvedorHAR(har).executa("observe.network", {"status": 403}, "T-1", 0)[0]
    with pytest.raises(Exception):
        o.dados = {}
    assert len(o.hash()) == 16
    assert o.to_dict()["capacidade"] == "observe.network"


def test_tarefa_filha_nao_herda_capacidade():
    """
    Herdar em silencio seria a forma mais facil de uma tarefa L0 virar L2 em
    tres saltos.
    """
    pai = Tarefa(objetivo="p", capacidades=["observe.network"],
                 orcamento=Orcamento(max_iteracoes=5))
    filha = deriva(pai, "f", ["analyze.json"])
    assert filha.capacidades == ["analyze.json"] and filha.pai == pai.id


# ── o cenario do desenho: diagnosticar 403 ──────────────────────────────────

def test_investigacao_403_ponta_a_ponta(har):
    """
    O exemplo do proprio desenho: descobrir por que a API devolve 403,
    usando so L0, com o loop governado pelo kernel.
    """
    t = Tarefa(objetivo="descobrir por que /search devolve 403",
               capacidades=["observe.network", "analyze.json"],
               orcamento=Orcamento(max_iteracoes=6), criada_por="teste")

    def propoe(tarefa, obs):
        if not obs:
            return Intencao("observe.network", {"status": 403}, "achar a falha")
        achou = [o for o in obs if o.dados.get("status") == 403]
        if achou:
            cabecalhos = {h["name"] for h in achou[0].dados["req_headers"]}
            return Intencao("", {}, f"403 com headers {sorted(cabecalhos)}",
                            concluir=True)
        return Intencao("observe.network", {}, "ampliar")

    r = Executor(Politica(), [ProvedorHAR(har)]).roda(t, propoe)
    assert r.concluida
    assert "authorization" in t.motivo_parada
    assert t.iteracao == 1        # achou na primeira, nao gastou o orcamento
