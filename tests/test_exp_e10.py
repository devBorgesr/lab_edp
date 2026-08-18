"""
test_exp_e10.py — a cascata do E10 reprova pelo motivo certo? (18/08/2026)

DESVIO DE ORDEM, DECLARADO: no E9b o teste sintetico veio ANTES da coleta,
porque a coleta custava horas. O E10 custa segundos e e deterministico, entao
a rodada real aconteceu primeiro. O risco que a ordem do E9b evitava — gastar
coleta cara para descobrir instrumento errado — nao existe aqui.

O que estes testes cobrem e o que a rodada real NAO exercitou: os caminhos
INSTRUMENTO INVALIDO, ESTRATO CONFUNDIDO e DATASET INCOMPLETO. Na rodada real
os tres cheques de validade passaram, entao nenhum foi observado falhando.
Cheque que nunca falhou e cheque cuja falha e suposicao.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _carrega():
    caminho = RAIZ / "sujeitos" / "edp" / "experimentos" / "exp_e10.py"
    spec = importlib.util.spec_from_file_location("exp_e10", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["exp_e10"] = mod
    spec.loader.exec_module(mod)
    return mod


E = _carrega()


def pares(escores: dict = None):
    """
    Constroi pares com escores JA definidos, por estrato e condicao.

    Bypassa os verificadores de proposito: a cascata e o objeto do teste, nao a
    tokenizacao. E evita depender do `edp` estar no PYTHONPATH.

    O PADRAO espelha o corpus real de 18/08: `negada` pontua ACIMA de
    `suportada` (medido: medianas 0,725 e 0,764, faixas sobrepostas), porque
    inserir uma negacao quase nao move o escore lexico. Um padrao onde `negada`
    ficasse abaixo tornaria H2/H3 falsas por construcao e os testes estariam
    exercitando um mundo que nao existe.
    """
    padrao = {
        ("cego", "suportada"): 0.05, ("cego", "trocada"): 0.05, ("cego", "negada"): 0.05,
        ("lexico", "suportada"): 0.80, ("lexico", "trocada"): 0.10, ("lexico", "negada"): 0.85,
        ("lexico_negacao", "suportada"): 0.80, ("lexico_negacao", "trocada"): 0.10,
        ("lexico_negacao", "negada"): 0.85,
    }
    padrao.update(escores or {})
    out = []
    for est in E.ESTRATOS:
        for i in range(E.N_PARES):
            p = {"estrato": est, "afirmacao": f"a{i}", "texto": f"t{i}",
                 "id_texto": f"id{i}", "gabarito": est == "suportada", "regra": ""}
            for cond in E.CONDICOES:
                p[f"escore_{cond}"] = padrao[(cond, est)]
            out.append(p)
    return out


# ── Os caminhos que a rodada real NAO exercitou ──────────────────────────────

def test_validade_a_pega_vazamento_no_encanamento():
    """
    `suportada` e `trocada` usam as MESMAS afirmacoes. Um verificador que
    ignora o texto nao pode separa-las. Se separar, algo alem do texto esta
    correlacionado ao rotulo.
    """
    v = E.score_e10(pares({("cego", "suportada"): 0.9, ("cego", "trocada"): 0.1}))
    assert v["veredito"] == "INSTRUMENTO INVALIDO"
    assert len(v["checks"]) == 1, "a cascata tem de PARAR no primeiro que falha"


def test_validade_b_pega_estrato_negada_confundido():
    """
    Se `cego` separa `negada`, a negacao mecanica e detectavel pelo TAMANHO da
    afirmacao — sem ler o texto. H2/H3 deixariam de ser sobre contradicao.

    Este e o cheque que a versao original do §5 nao conseguia nem enxergar,
    porque escore constante torna min>max falso por construcao (emenda E10-1).
    """
    # `trocada` fica ALTA junto: senao o cego separa trocada tambem e o
    # VALIDADE-a dispara antes, e o teste exercitaria o degrau errado.
    v = E.score_e10(pares({("cego", "suportada"): 0.9, ("cego", "trocada"): 0.9,
                           ("cego", "negada"): 0.1}))
    assert v["veredito"] == "ESTRATO negada CONFUNDIDO"
    assert [c["ok"] for c in v["checks"]] == [True, False]


def test_dataset_incompleto_e_recusado():
    p = [x for x in pares() if not (x["estrato"] == "negada" and x["afirmacao"] == "a0")]
    v = E.score_e10(p)
    assert v["veredito"] == "DATASET INCOMPLETO"
    assert v["faltando"] == {"negada": 1}


# ── O caminho que a rodada real produziu ─────────────────────────────────────

def test_reproduz_o_veredito_da_rodada_real():
    """
    H1 falha (uma suportada com escore 0 abaixo do max das trocadas), H2 e H3
    passam. E o veredito observado em 18/08 contra o corpus real.
    """
    p = pares()
    for x in p:
        if x["estrato"] == "suportada" and x["afirmacao"] == "a0":
            x["escore_lexico"] = 0.0
            x["escore_lexico_negacao"] = 0.0
    v = E.score_e10(p)
    assert v["veredito"] == "PARCIAL — confirmadas: H2, H3"
    assert (v["H1"], v["H2"], v["H3"]) == (False, True, True)


def test_todas_confirmadas_quando_o_lexico_separa():
    """
    O caminho feliz PRECISA ser alcancavel — senao a cascata seria
    intransponivel por construcao, que foi o defeito do DELTA_EQUIV=0.02.
    """
    v = E.score_e10(pares())
    assert v["veredito"] == "TODAS CONFIRMADAS (H1+H2+H3)", [
        c for c in v["checks"] if not c["ok"]]


def test_h2_refutada_se_o_lexico_separar_contradicao():
    """
    O desfecho mais valioso possivel do E10, e por isso precisa ser
    representavel: se o lexico distinguisse `X` de `X nao`, o critico barato
    voltaria a mesa.
    """
    v = E.score_e10(pares({("lexico", "negada"): 0.01,
                             ("lexico_negacao", "negada"): 0.01}))
    assert v["H1"] is True and v["H2"] is False and v["H3"] is False
    assert "PARCIAL" in v["veredito"]


# ── Componentes ──────────────────────────────────────────────────────────────

def test_cego_ignora_o_texto():
    """A propriedade que o torna controle. Se ler o texto, deixa de ser cego."""
    a = E.escore_cego("uma afirmacao qualquer", "texto completamente diferente")
    b = E.escore_cego("uma afirmacao qualquer", "")
    c = E.escore_cego("uma afirmacao qualquer", "uma afirmacao qualquer")
    assert a == b == c


def test_cego_nao_e_constante():
    """
    Emenda E10-1: escore constante tornaria min>max falso por construcao e o
    controle nunca poderia falhar. Ele tem de variar com a afirmacao.
    """
    curto = E.escore_cego("processo registro", "")
    longo = E.escore_cego("processo registro conjunto medida amostra unidade", "")
    assert longo > curto


def test_tokenizacao_respeita_piso_e_stopwords():
    t = E.tok("O processo de uma medida com que nao")
    assert "processo" in t and "medida" in t
    assert not any(len(x) < E.MIN_TOKEN_LEN for x in t)
    assert not (t & E.STOPWORDS)


def test_negacao_usa_verbo_quando_casa_e_prefixo_quando_nao():
    txt, regra = E.negar("Pergunta requer clarificacao")
    assert regra == "verbo:requer" and " nao " in txt
    txt2, regra2 = E.negar("Oferta de assistencia tecnica")
    assert regra2 == "prefixo" and txt2.startswith(E.PREFIXO_NEGACAO)


def test_separa_e_estritamente_min_maior_que_max():
    p = pares({("lexico", "suportada"): 0.5, ("lexico", "trocada"): 0.5})
    ok, mn, mx = E.separa(p, "lexico", "suportada", "trocada")
    assert ok is False, "empate NAO separa — o criterio e estrito"


# ── Anti-mock: a guarda de proveniencia do proprio experimento ───────────────

def test_kernel_recusa_copia_instalada(monkeypatch):
    """
    Emenda E10-2. Medido em 18/08: a copia instalada tinha 492 linhas contra
    527 do kernel. Importar dela testaria outra build sem aviso nenhum.
    """
    import types
    falso = types.ModuleType("edp")
    falso.__file__ = "/home/x/.local/lib/python3.11/site-packages/edp/__init__.py"
    monkeypatch.setitem(sys.modules, "edp", falso)
    with pytest.raises(RuntimeError, match="copia INSTALADA"):
        E.kernel_resolvido()


def test_kernel_aceita_arvore_de_desenvolvimento(monkeypatch):
    import types
    falso = types.ModuleType("edp")
    falso.__file__ = "/media/sf_edp_v5_main/edp/__init__.py"
    monkeypatch.setitem(sys.modules, "edp", falso)
    monkeypatch.delenv("EDP_KERNEL", raising=False)
    assert E.kernel_resolvido().endswith("edp")
