"""
test_exp_e9b.py — a cascata do §6 morde? (14/08/2026)

O E9 gastou ~2h da maquina do pesquisador para reprovar num cheque de sanidade
mal formulado. O E9b custa ~3h (1440 requisicoes). Antes de gastar isso, vale
provar com dado SINTETICO que cada degrau da cascata reprova pelo motivo certo
— e, principalmente, que um dataset limpo PASSA.

Um harness cuja cascata nunca foi exercitada e um harness cujo veredito e
suposicao.
"""
from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _carrega():
    caminho = RAIZ / "sujeitos" / "edp" / "experimentos" / "exp_e9b.py"
    spec = importlib.util.spec_from_file_location("exp_e9b", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_e9b"] = mod
    spec.loader.exec_module(mod)
    return mod


E = _carrega()

# Ruido calibrado contra o piloto do E9 (ruido_rel ~ 0.28, §11-bis E9b-1).
RUIDO = 0.28

# n POR CONDICAO, igual ao desenho real. Nao e detalhe de performance:
# a largura do IC de R escala com 1/sqrt(n), e o teste de EQUIVALENCIA do §6.1
# so e viavel se essa largura couber em 2*DELTA_EQUIV. A primeira versao deste
# arquivo usou N=90 "para ser rapido" e reprovou ate o dataset limpo — largura
# ~0,187 contra margem 0,14. Recriou, por acidente, a mesma inviabilidade que a
# emenda E9b-1 acabara de corrigir. Encurtar o n aqui nao acelera o teste:
# desliga a hipotese que ele deveria exercitar.
N = E.N_REPETICOES * E.K_PROMPTS
CUSTO_BASE = 55.0     # ms/token
TOK_BASE = 25
LOAD = 250e6          # ns, identico entre condicoes por padrao


@pytest.fixture(autouse=True)
def _bootstrap_barato(monkeypatch):
    """b=10000 x 4 condicoes tornaria a suite inutilmente lenta."""
    monkeypatch.setattr(E, "N_BOOTSTRAP", 300)


def amostras(rng, *, custo=None, tokens=None, load=None, recarga_frac=0.0):
    """
    Gera o dataset das 4 condicoes. Cada kwarg e um dict por condicao que
    SOBRESCREVE o padrao — e assim cada sabotagem fica explicita no teste.
    """
    custo = {**{c: CUSTO_BASE for c in E.CONDICOES},
             **{"meio": CUSTO_BASE * 1.25, "dobro": CUSTO_BASE * 1.5}, **(custo or {})}
    tokens = {**{c: TOK_BASE for c in E.CONDICOES},
              **{"meio": 37, "dobro": 50}, **(tokens or {})}
    load = {**{c: LOAD for c in E.CONDICOES}, **(load or {})}

    out = []
    for cond in E.CONDICOES:
        for i in range(N):
            tok = tokens[cond]
            dur = custo[cond] * 1e6 * tok * max(0.1, 1 + rng.gauss(0, RUIDO))
            ld = load[cond]
            # Recargas DETERMINISTICAS, na mesma taxa em toda condicao. Com
            # sorteio aleatorio a media de load ficava dominada pela cauda e
            # variava entre condicoes, fazendo o 6.2 reprovar antes do 6.3 —
            # o teste passava a exercitar o degrau errado.
            if recarga_frac and (i % max(1, round(1 / recarga_frac)) == 0):
                ld = load[cond] * 20
            out.append({
                "condicao": cond, "dry_run": False, "prompt_idx": i % 12,
                "prompt_eval_count": tok, "prompt_eval_duration": dur,
                "eval_count": 64, "eval_duration": 3.2e9,
                "load_duration": ld, "total_duration": dur + 3.2e9 + ld,
            })
    return out


# ── O caminho feliz PRECISA passar ───────────────────────────────────────────

def test_dataset_limpo_confirma_h1_e_h2():
    """
    Se um dataset limpo nao passar, a cascata e intransponivel e reprovaria a
    coleta real por construcao — que foi exatamente o que aconteceu no E9 com
    o DELTA_EQUIV inatingivel.
    """
    v = E.score_e9b(amostras(random.Random(1)))
    assert v["veredito"] == "H1 E H2 CONFIRMADAS", [c for c in v["checks"] if not c["ok"]]


def test_todos_os_checks_do_caminho_feliz_passam():
    v = E.score_e9b(amostras(random.Random(2)))
    falhos = [c["check"] for c in v["checks"] if not c["ok"]]
    assert falhos == [], falhos


# ── Cada degrau reprova pelo motivo certo ────────────────────────────────────

def test_6_1_controle_negativo_pega_condicoes_desiguais():
    """
    base_B e byte-identica a base_A. Se medir 30% acima, houve artefato — e
    NADA pode ser afirmado sobre meio/dobro, mesmo que eles separem lindamente.
    """
    v = E.score_e9b(amostras(random.Random(3), custo={"base_B": CUSTO_BASE * 1.30}))
    assert v["veredito"] == "INSTRUMENTO INVALIDO"
    assert v["checks"][0]["check"].startswith("6.1")
    assert len(v["checks"]) == 1, "a cascata tem de PARAR no primeiro que falha"


def test_6_2_pega_load_duration_diferente_entre_condicoes():
    """
    Overhead comum nao explica separacao. Overhead que DIFERE entre condicoes
    explica — e vira confundidor de verdade.
    """
    v = E.score_e9b(amostras(random.Random(4), load={"dobro": LOAD * 1.5}))
    assert "load_duration difere" in v["veredito"]


def test_6_3_pega_recarga_real_por_forma():
    """
    Recarga real: cauda alta contra a mediana do proprio load_duration.

    Taxa IGUAL nas quatro condicoes de proposito — assim o 6.2 (overhead comum)
    passa e o 6.3 e de fato exercitado. Recarga que atinge so uma condicao ja e
    pega pelo 6.2, e ai o teste nao provaria nada sobre o 6.3.
    """
    v = E.score_e9b(amostras(random.Random(5), recarga_frac=0.15))
    assert v["veredito"] == "SANIDADE FALHOU (recarga real)"
    assert v["recargas"]["frac"] > E.MAX_DESCARTE_FRAC


def test_6_4_pega_carga_fora_do_alvo():
    v = E.score_e9b(amostras(random.Random(6), tokens={"dobro": 80}))  # 3.2x
    assert v["veredito"] == "SANIDADE FALHOU (carga dobro)"


def test_h0_quando_nao_ha_efeito():
    """Sem diferenca de custo unitario, H1 nao e rejeitada. H0 e resultado."""
    v = E.score_e9b(amostras(random.Random(7),
                             custo={"meio": CUSTO_BASE, "dobro": CUSTO_BASE}))
    assert v["veredito"].startswith("H0 NAO REJEITADA")


def test_h2_falha_sem_dose_resposta_separada():
    """
    H1 pode passar e H2 falhar: `dobro` separa de `base_A`, mas `meio` nao
    separa de `dobro`. Isso desqualifica a regua para cargas intermediarias —
    caso do E10/E12 — e por isso e reportado, nao escondido dentro de H1.
    """
    v = E.score_e9b(amostras(random.Random(8),
                             custo={"meio": CUSTO_BASE * 1.5, "dobro": CUSTO_BASE * 1.5}))
    assert v["veredito"] == "H1 CONFIRMADA, H2 NAO (sem dose-resposta separada)"


# ── Invariantes estruturais ──────────────────────────────────────────────────

def test_a_cascata_para_no_primeiro_que_falha():
    """
    Continuar depois de um cheque reprovado produziria numeros que ninguem
    deveria ler — foi assim que o relatorio do exp008 imprimiu "retrieve REAL
    chamado" depois de abortar antes de chamar.
    """
    v = E.score_e9b(amostras(random.Random(9), load={"dobro": LOAD * 2}))
    # ordem apos a emenda E9b-5: 6.1 -> 6.3 -> 6.2
    assert [c["ok"] for c in v["checks"]] == [True, True, False]
    assert v["checks"][-1]["check"].startswith("6.2")


def test_magnitude_nao_e_criterio():
    """
    R(dobro) e descritivo (§6.8). Um R enorme com controle reprovado continua
    dando INSTRUMENTO INVALIDO — a magnitude nao resgata a validade.
    """
    v = E.score_e9b(amostras(random.Random(10),
                             custo={"base_B": CUSTO_BASE * 1.3,
                                    "dobro": CUSTO_BASE * 5}))
    assert v["veredito"] == "INSTRUMENTO INVALIDO"


def test_referencia_nao_tem_R_contra_si_mesma():
    v = E.score_e9b(amostras(random.Random(11)))
    assert E.REFERENCIA not in v["R"]
    assert set(v["R"]) == set(E.CONDICOES) - {E.REFERENCIA}


def test_preenchimento_de_dobro_estende_o_de_meio():
    """
    GUARDA DE FONTE (emenda E9b-4): `calibrar_escada` faz UM crescimento e
    captura em dois pontos. Se alguem calibrar os degraus independentemente, o
    salto entre `meio` e `dobro` passa a poder vir do TEXTO e nao do tamanho —
    e a dose-resposta do §6.6 deixa de medir comprimento.
    """
    import inspect
    fonte = inspect.getsource(E.calibrar_escada)
    assert fonte.count("_cresce_ate") == 2
    assert "palavras: list = []" in fonte
    # a MESMA lista atravessa os dois degraus
    i1 = fonte.index("_cresce_ate")
    i2 = fonte.index("_cresce_ate", i1 + 1)
    assert "palavras" in fonte[i1:i2 + 120]
