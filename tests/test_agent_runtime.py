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


# ═══════════════════════════════════════════════════════════════════════════
# CICLO COMPLETO — Copiloto -> Kernel -> Router -> Modelo -> Politica ->
#                  Capability -> Observacao -> Kernel
#
# Nenhum destes gasta API: o modelo e `ClienteFake` com respostas
# roteirizadas. Testar o loop com modelo real mediria o modelo, nao o loop.
# ═══════════════════════════════════════════════════════════════════════════

from agent_runtime.propositor import (ClienteFake, PropositorLLM)   # noqa: E402
from agent_runtime.requisicao import (EXEMPLO, RequisicaoInvalida,   # noqa: E402
                                      de_arquivo, para_tarefa)
from agent_runtime.roteador import (Escolha, RoteadorEDP,            # noqa: E402
                                    RoteadorFixo)


# ── o contrato de entrada (onde o Copiloto entraria) ────────────────────────

def test_requisicao_vira_tarefa():
    t = para_tarefa(dict(EXEMPLO))
    assert t.capacidades == ["observe.network", "analyze.json"]
    assert t.criada_por == "copiloto" and t.orcamento.max_iteracoes == 8


def test_requisicao_recusa_L1_na_entrada():
    """
    Trava redundante com a Politica, de proposito: a politica decide por
    chamada, isto recusa a tarefa inteira antes de existir.
    """
    d = dict(EXEMPLO); d["capacidades"] = ["act.click"]
    with pytest.raises(RequisicaoInvalida, match="DECISAO_ATUACAO"):
        para_tarefa(d)


@pytest.mark.parametrize("mutacao,padrao", [
    ({"capacidade": "x"}, "desconhecidos"),
    ({"schema": "TarefaRequest v2"}, "desconhecido"),
    ({"objetivo": "  "}, "nao-vazio"),
    ({"capacidades": []}, "nao-vazia"),
])
def test_requisicao_recusa_cedo(mutacao, padrao):
    d = dict(EXEMPLO); d.update(mutacao)
    with pytest.raises(RequisicaoInvalida, match=padrao):
        para_tarefa(d)


def test_transporte_hoje_e_um_arquivo(tmp_path):
    """
    Nao ha transporte Copiloto->runtime: o sandbox e IndexedDB e o manifest
    so tem host_permission de claude.ai. O contrato e um arquivo JSON, e quem
    o escreve (botao novo, HTTP, ou pessoa) nao muda nada aqui.
    """
    p = tmp_path / "pedido.json"
    p.write_text(json.dumps(EXEMPLO), encoding="utf-8")
    assert de_arquivo(p).objetivo.startswith("descobrir por que")


# ── o Router escolhe, e o modelo vira recurso substituivel ──────────────────

def test_roteador_edp_real_roteia_por_complexidade():
    r = RoteadorEDP()
    if not r.disponivel:
        pytest.skip(f"kernel edp_v5 indisponivel: {r.motivo_indisponivel}")
    curta = r.escolhe("continue")
    complexa = r.escolhe("por que a API devolve 403 e como o retry interage "
                         "com o cache distribuido sob concorrencia?")
    assert curta.modelo and complexa.modelo
    assert complexa.tier >= curta.tier, "pergunta complexa nao subiu de tier"
    assert curta.porque and complexa.porque


def test_roteador_indisponivel_levanta_em_vez_de_cair_num_default(tmp_path):
    """
    Cair num modelo default faria a tarefa inteira rodar no modelo errado sem
    ninguem notar.
    """
    r = RoteadorEDP(caminho_edp=tmp_path / "nao_existe")
    assert not r.disponivel
    with pytest.raises(RuntimeError, match="nao caio num modelo default|"
                                           "Nao caio num modelo default"):
        r.escolhe("x")


def test_modelo_pode_mudar_no_meio_da_tarefa(har):
    """
    A propriedade mais interessante do desenho: a TAREFA continua a mesma
    enquanto o modelo troca. O estado vive na Tarefa e nas Observacoes.
    """
    class RoteadorAlternado(RoteadorFixo):
        def __init__(self): self.n = 0
        def escolhe(self, texto, modelo_anterior=None, contexto=None):
            self.n += 1
            return Escolha(f"modelo-{self.n}", self.n, "alternado")

    cliente = ClienteFake([
        '{"capacidade":"observe.network","parametros":{"status":403}}',
        '{"capacidade":"analyze.json","parametros":{"corpo":"{}"}}',
        '{"concluir":true,"porque":"consegui com dois modelos"}',
    ])
    prop = PropositorLLM(cliente=cliente, roteador=RoteadorAlternado())
    t = Tarefa(objetivo="x", capacidades=["observe.network", "analyze.json"],
               orcamento=Orcamento(max_iteracoes=6))
    r = Executor(Politica(), [ProvedorHAR(har)]).roda(t, prop)

    assert r.concluida
    modelos = [p["modelo"] for p in prop.trilha]
    assert modelos == ["modelo-1", "modelo-2", "modelo-3"]
    assert len({p["iteracao"] for p in prop.trilha}) == 3


def test_trilha_registra_modelo_tier_e_custo(har):
    cliente = ClienteFake(['{"concluir":true,"porque":"ok"}'])
    prop = PropositorLLM(cliente=cliente, roteador=RoteadorFixo("m", tier=2))
    t = Tarefa(objetivo="x", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=2))
    Executor(Politica(), [ProvedorHAR(har)]).roda(t, prop)
    assert prop.trilha[0]["modelo"] == "m" and prop.trilha[0]["tier"] == 2


# ── o parse estrito ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("bruto", ["", "desculpe, nao consigo", "{",
                                   '{"porque":"esqueci a capacidade"}',
                                   '["lista"]', "texto sem json nenhum"])
def test_saida_ilegivel_nunca_vira_concluir(bruto):
    """
    Se ilegivel virasse `concluir`, um modelo com problema de formatacao
    encerraria a tarefa dizendo que atingiu o objetivo.
    """
    t = Tarefa(objetivo="x", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=2))
    assert PropositorLLM.parse(bruto, t) is None


def test_json_no_meio_de_texto_e_aceito():
    t = Tarefa(objetivo="x", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=2))
    i = PropositorLLM.parse('claro! {"capacidade":"observe.network"} pronto', t)
    assert i is not None and i.capacidade == "observe.network"


def test_ilegivel_repetido_termina_em_bloqueada_nao_concluida(har):
    """
    Tres respostas ilegiveis nao podem virar CONCLUIDA por desistencia. A
    proposta vai para uma capacidade inexistente, a politica nega, e a tarefa
    para em BLOQUEADA com motivo.
    """
    cliente = ClienteFake(["lixo", "mais lixo", "ainda lixo", "lixo final"])
    prop = PropositorLLM(cliente=cliente, roteador=RoteadorFixo())
    t = Tarefa(objetivo="x", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=4))
    r = Executor(Politica(), [ProvedorHAR(har)]).roda(t, prop)

    assert t.estado is EstadoTarefa.BLOQUEADA
    assert t.estado is not EstadoTarefa.CONCLUIDA
    assert all(p["ilegivel"] for p in prop.trilha)


# ── o ciclo inteiro, ponta a ponta ──────────────────────────────────────────

def test_ciclo_completo_copiloto_ate_observacao(tmp_path, har):
    """
    Copiloto escreve a requisicao -> kernel valida -> router escolhe modelo ->
    modelo propoe -> politica autoriza -> provedor le o HAR -> observacao
    volta ao kernel -> modelo conclui.

    Tudo L0. A fronteira do debugger_capturer.js continua intacta.
    """
    pedido = tmp_path / "do_copiloto.json"
    pedido.write_text(json.dumps({
        "schema": "TarefaRequest v1",
        "objetivo": "descobrir por que /search devolve 403",
        "capacidades": ["observe.network"],
        "max_iteracoes": 5,
        "criada_por": "copiloto",
    }), encoding="utf-8")

    tarefa = de_arquivo(pedido)
    assert tarefa.criada_por == "copiloto"

    cliente = ClienteFake([
        '{"capacidade":"observe.network","parametros":{"status":403},'
        '"porque":"procurar a falha"}',
        '{"concluir":true,"porque":"403 vem com header authorization"}',
    ])
    politica = Politica()
    prop = PropositorLLM(cliente=cliente, roteador=RoteadorFixo("haiku", 1))

    r = Executor(politica, [ProvedorHAR(har)]).roda(tarefa, prop)

    assert r.concluida
    assert "authorization" in tarefa.motivo_parada
    assert any(o.dados.get("status") == 403 for o in r.observacoes)
    # o modelo viu o prompt com as capacidades declaradas, e so elas
    _, primeiro_prompt = cliente.chamadas[0]
    assert "observe.network" in primeiro_prompt
    assert "act.click" not in primeiro_prompt
    # e a politica registrou cada decisao
    assert politica.trilha and all(
        d["veredito"] == "PERMITE" for d in politica.trilha)


def test_o_modelo_nunca_recebe_o_provedor(har):
    """
    Garantia estrutural: o `propositor` recebe Tarefa e Observacoes. Nao
    recebe provedor, executor nem politica — nao ha como ele executar.
    """
    import inspect
    sig = inspect.signature(Executor.roda)
    assert list(sig.parameters) == ["self", "tarefa", "propositor"]

    visto = {}
    def espiao(tarefa, obs):
        visto["args"] = (type(tarefa).__name__, type(obs).__name__)
        return Intencao("", {}, "fim", concluir=True)

    Executor(Politica(), [ProvedorHAR(har)]).roda(
        Tarefa(objetivo="x", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=2)), espiao)
    assert visto["args"] == ("Tarefa", "list")


# ── regressao: os dois defeitos achados ao ligar o ciclo (03/09) ────────────

def test_capacidade_alucinada_e_negada_e_nao_derruba_o_loop(har):
    """
    Modelos alucinam nome de capacidade. Antes isto levantava
    CapacidadeDesconhecida de dentro da politica e MATAVA o loop — uma tarefa
    de 20 iteracoes morreria na primeira palavra inventada.

    Negar e a resposta certa; o modelo propoe outra coisa na iteracao
    seguinte.
    """
    cliente = ClienteFake([
        '{"capacidade":"observe.telepatia","porque":"inventei"}',
        '{"capacidade":"observe.network","parametros":{"status":403}}',
        '{"concluir":true,"porque":"achei mesmo com o erro no meio"}',
    ])
    prop = PropositorLLM(cliente=cliente, roteador=RoteadorFixo())
    t = Tarefa(objetivo="x", capacidades=["observe.network"],
               orcamento=Orcamento(max_iteracoes=6))
    politica = Politica()
    r = Executor(politica, [ProvedorHAR(har)]).roda(t, prop)

    assert r.concluida, "a alucinacao nao pode matar a tarefa"
    assert "observe.telepatia" in r.negadas
    negada = [d for d in politica.trilha if d["capacidade"] == "observe.telepatia"]
    assert negada and "inexistente" in negada[0]["motivo"]


def test_declarar_capacidade_inexistente_na_tarefa_ainda_levanta():
    """
    A distincao que a correcao preserva: DECLARAR inexistente e erro de
    contrato do cliente e falha alto; PROPOR no meio do loop e alucinacao e e
    negada. Se as duas virassem negacao, um cliente escreveria a tarefa
    errada e so descobriria pelo resultado vazio.
    """
    with pytest.raises(CapacidadeDesconhecida):
        Tarefa(objetivo="x", capacidades=["observe.telepatia"],
               orcamento=Orcamento(max_iteracoes=2))


def test_roteador_confere_o_caminho_e_nao_o_cache_de_import(tmp_path):
    """
    `edp` fica em sys.modules depois do primeiro import. Antes disto,
    QUALQUER caminho passava a "funcionar" — `disponivel` dizia True
    apontando para lugar nenhum, e o kernel usado nao era o do caminho
    pedido.
    """
    RoteadorEDP()                                   # popula sys.modules
    r = RoteadorEDP(caminho_edp=tmp_path / "vazio")
    assert not r.disponivel
    assert "nao existe" in r.motivo_indisponivel
