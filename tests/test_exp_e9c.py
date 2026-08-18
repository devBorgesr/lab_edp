"""
test_exp_e9c.py — a copia difere SO onde foi declarado? (18/08/2026)

O E9c e copia deliberada do E9b com duas constantes trocadas. Copiar 500
linhas e o tipo de operacao que produz divergencia silenciosa: alguem ajusta
um limiar numa das copias, o build continua verde, e dois experimentos que se
apresentam como "o mesmo desenho" deixam de ser.

Este arquivo torna isso mecanico. Ele NAO reexecuta a cascata (o
test_exp_e9b.py ja faz, e a fonte e a mesma): ele prova que a fonte E a mesma.
"""
from __future__ import annotations

import importlib.util
import inspect
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

HARN = RAIZ / "sujeitos" / "edp" / "experimentos"

# A unica diferenca ADMITIDA, declarada no §1 do preregistro_experimento_e9c.
DIFERENCA_DECLARADA = {"EXPERIMENTO", "NUM_PREDICT"}


def _carrega(nome: str):
    spec = importlib.util.spec_from_file_location(nome, HARN / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


B = _carrega("exp_e9b")
C = _carrega("exp_e9c")


def _constantes(mod) -> dict:
    return {k: v for k, v in vars(mod).items()
            if k.isupper() and not k.startswith("_")
            and isinstance(v, (int, float, str, tuple, bool))}


def test_as_constantes_diferem_exatamente_no_par_declarado():
    """
    Toda constante fora de EXPERIMENTO e NUM_PREDICT tem de ser identica.

    Uma margem, tolerancia ou nivel de IC que divergisse aqui faria os dois
    experimentos medirem coisas diferentes enquanto ambos os documentos
    afirmam herdar o mesmo desenho.
    """
    cb, cc = _constantes(B), _constantes(C)
    assert set(cb) == set(cc), f"conjunto de constantes divergiu: {set(cb) ^ set(cc)}"
    divergentes = {k for k in cb if cb[k] != cc[k]}
    assert divergentes == DIFERENCA_DECLARADA, (
        f"diferenca nao declarada: {divergentes - DIFERENCA_DECLARADA} | "
        f"declarada e ausente: {DIFERENCA_DECLARADA - divergentes}"
    )


def test_o_par_declarado_tem_os_valores_do_preregistro():
    assert (B.EXPERIMENTO, C.EXPERIMENTO) == ("E9b", "E9c")
    assert (B.NUM_PREDICT, C.NUM_PREDICT) == (64, 1)


def _fonte_normalizada(fn) -> str:
    """Fonte com o sufixo do experimento neutralizado, para comparar logica."""
    return inspect.getsource(fn).replace("e9b", "@").replace("e9c", "@") \
                                .replace("E9b", "@").replace("E9c", "@")


def test_a_cascata_de_pontuacao_nao_derivou():
    """
    Guarda contra o modo de falha classico da copia: alguem conserta um
    degrau num arquivo e esquece o outro.
    """
    assert _fonte_normalizada(B.score_e9b) == _fonte_normalizada(C.score_e9c)


def test_as_funcoes_que_alimentam_o_criterio_nao_derivaram():
    for nome in ("_pares_custo", "_pares_load", "_dentro",
                 "calibrar_escada", "_cresce_ate", "plano_de_execucao"):
        fb, fc = getattr(B, nome), getattr(C, nome)
        assert _fonte_normalizada(fb) == _fonte_normalizada(fc), f"{nome} derivou"


def test_num_predict_nao_entra_em_nenhuma_regra_de_decisao():
    """
    O §3 do pre-registro do E9c afirma que NUM_PREDICT nao aparece em regra de
    decisao alguma — e e essa afirmacao que sustenta "isto nao e escolher a
    regua com o dado na mao".

    Afirmacao em prosa nao vale; aqui ela vira verificacao. Se alguem passar a
    usar NUM_PREDICT dentro da pontuacao, a justificativa do E9c cai junto.
    """
    fonte = inspect.getsource(C.score_e9c)
    assert "NUM_PREDICT" not in fonte, (
        "NUM_PREDICT passou a aparecer na cascata — a justificativa do §3 "
        "do E9c deixa de valer e a mudanca vira alteracao de criterio."
    )


def test_a_metrica_primaria_nao_usa_campo_de_geracao():
    """
    Corolario: com NUM_PREDICT=1, `eval_count`/`eval_duration` descrevem um
    unico token. Se a metrica primaria os tocasse, o E9c mediria ruido.

    Com fronteira de palavra, nao substring: `prompt_eval_count` CONTEM
    `eval_count`, e a primeira versao deste teste reprovou por isso. E o mesmo
    casamento frouxo que apodreceu o catalogo de codigo morto do edp_v5 —
    `\bretrieval\b` nao separando `from .retrieval import` de mencao em
    docstring. Repeti o erro em escala menor, no mesmo dia.
    """
    fonte = inspect.getsource(C._pares_custo)
    for campo in ("eval_count", "eval_duration"):
        achou = re.search(rf"\b{campo}\b", fonte)
        assert achou is None, f"_pares_custo passou a usar {campo}"
