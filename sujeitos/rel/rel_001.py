"""
rel_001.py — harness do REL-001.

PERGUNTA: o rotulo de relevancia e confiavel o bastante para sustentar Recall@K?

Pre-registro: docs/rel/preregistro_rel_001.md — constantes espelhadas la.

O QUE ESTE ARQUIVO IMPOE, E NAO SO DOCUMENTA

1. O gate roda sobre o estrato `topo` (§3.3). O pool inteiro infla o kappa em
   0.07 — medido, mesmo instrumento, mudando so a mistura. `veredito()` recusa
   calcular sobre o pool completo.

2. O `controle` e PRE-CONDICAO, nao parcela do kappa. Se ele nao atingir
   ACORDO_ESPERADO_CONTROLE, o rubric nao reconhece nem negativo trivial e a
   rodada e declarada INVALIDA — nao ajustada.

3. IC por bootstrap de QUERY. Dez pares da mesma query nao sao independentes;
   trata-los como 500 observacoes estreita o intervalo indevidamente.

4. Veredito sobre o INTERVALO. Um kappa pontual de 0.82 com IC [0.74; 0.89] NAO
   aprova — *caber nao e passar* (E9b).

E O QUE ELE RECUSA FAZER

Nao rotula. Nao chama juiz LLM. O harness monta o pool, calcula e julga; a
rotulacao entra por fora, dos dois caminhos independentes (§7), e so depois de
os dois conjuntos estarem congelados.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Optional, Sequence

# ── Constantes congeladas (espelhadas no §8) ──────────────────────────────────

EXPERIMENTO              = "REL-001"
N_QUERIES                = 50
N_DOCS_POR_QUERY         = 10
N_TOPO                   = 5
N_CAUDA                  = 3
N_CONTROLE               = 2
GATE_APROVA              = 0.80
GATE_REPROVA             = 0.60
ALPHA                    = 0.05
N_BOOTSTRAP              = 20000
SEED                     = 20260830
ACORDO_ESPERADO_CONTROLE = 0.98

# §3.3: fora desta faixa o kappa volta a ser distorcido e a leitura exige AC1
# ao lado, com a prevalencia declarada na mesma linha.
FAIXA_PREVALENCIA_OK = (0.30, 0.70)

ESTRATOS = ("topo", "cauda", "controle")
ESTRATO_DO_GATE = "topo"          # §3.3 — onde o Recall@K de fato decide

# Marcador do artefato congelado v2 (30/08). Documento SEM assunto — saudacao,
# comando, instante datado — nao serve de controle negativo: os dois julgadores
# concordariam que e irrelevante por AUSENCIA DE CONTEUDO, nao por diferenca de
# dominio. Controle que passa sem exercitar o rubric nao verifica nada, e e o
# mesmo furo pelo qual recusei o corpus externo.
MARCADOR_SEM_TEMA = "SEM_TEMA"


# ── Montagem do pool (§3.2, corrigido pelo §3.3) ──────────────────────────────

def normaliza_dominio(d: str) -> str:
    """
    Chave canonica de dominio.

    ACHADO 30/08, no artefato congelado: `PostgreSQL indexing` e
    `postgresql indexing` entraram como dominios DISTINTOS — 6 dos 77
    documentos. Sem normalizar, um doc do segundo contaria como "outro
    dominio" para uma query do primeiro, e o controle negativo receberia um
    documento do MESMO assunto. O controle deixaria de ser negativo.

    Consertado aqui e nao no artefato: congelado nao se reescreve (§4.4). A
    comparacao passa a ser sobre a chave; o rotulo original fica preservado.
    """
    import re, unicodedata
    s = "".join(c for c in unicodedata.normalize("NFD", (d or "").lower())
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def corpus_de_outro_dominio(dominios: dict, dominio_da_query: str) -> list[str]:
    """
    Ids elegiveis para o estrato `controle`: tudo cujo dominio NORMALIZADO
    difere do da query.

    `dominios` e o artefato congelado de verifica_dominio.py — id -> dominio
    verificado. Documento sem dominio verificado NAO entra: nao se sabe a que
    assunto pertence, e adivinhar aqui reintroduziria o rotulo nao-validado que
    a pre-condicao existe para eliminar.

    `SEM_TEMA` tambem fica de fora (v2 do congelado): 13 dos 77 sao saudacao,
    comando ou instante datado. Como controle negativo eles seriam faceis pelo
    motivo errado — falta de conteudo, nao diferenca de assunto.
    """
    alvo = normaliza_dominio(dominio_da_query)
    return [doc_id for doc_id, dom in dominios.items()
            if dom != MARCADOR_SEM_TEMA and normaliza_dominio(dom) != alvo]

def monta_pool(query: str,
               ranking: Sequence[str],
               corpus_outro_dominio: Sequence[str],
               seed: int = SEED) -> list[dict]:
    """
    Os 10 candidatos de uma query, por estrato.

    `ranking` e a saida do retriever REAL, em ordem. `corpus_outro_dominio` sao
    documentos de dominio distinto — o controle negativo do §4.5, cuja previsao
    (irrelevante nos dois julgadores) esta escrita no pre-registro ANTES do dado.

    Falha alto se o ranking nao alcancar a cauda: pool incompleto muda a
    prevalencia e portanto muda o kappa, e isso nao pode acontecer em silencio.
    """
    # DEDUP POR ID ANTES DE FATIAR (achado 30/08).
    # Todos os 61 ids da camada semantica tambem estao na episodica — a
    # consolidacao promove e nao remove, e `_hybrid_index` varre as duas sem
    # deduplicar. Resultado medido: 637 ids repetidos em 2.500 slots (25,5%).
    #
    # Sem isto, `ranking[:5]` pode ter menos de 5 documentos distintos, e o
    # MESMO documento pode cair em `topo` e em `cauda` — julgado duas vezes,
    # entrando duas vezes no kappa.
    #
    # Nao altera o protocolo: o §3.2 diz "top-5 do retriever", e cinco slots
    # com quatro documentos distintos nunca foram cinco.
    vistos, unico = set(), []
    for d in ranking:
        if d not in vistos:
            vistos.add(d); unico.append(d)
    ranking = unico

    if len(ranking) < 50:
        raise RuntimeError(
            f"ranking com {len(ranking)} itens; o estrato `cauda` sai das "
            f"posicoes 20-50 e precisa de 50 DISTINTOS. Pool incompleto altera "
            f"a prevalencia e o kappa — ver §3.3."
        )
    if len(corpus_outro_dominio) < N_CONTROLE:
        raise RuntimeError("corpus de outro dominio insuficiente para o controle")

    rng = random.Random(f"{seed}:{query}")
    pool = []
    for d in ranking[:N_TOPO]:
        pool.append({"query": query, "doc": d, "estrato": "topo"})
    for d in rng.sample(list(ranking[19:50]), N_CAUDA):
        pool.append({"query": query, "doc": d, "estrato": "cauda"})
    for d in rng.sample(list(corpus_outro_dominio), N_CONTROLE):
        pool.append({"query": query, "doc": d, "estrato": "controle"})

    assert len(pool) == N_DOCS_POR_QUERY
    rng.shuffle(pool)                    # julgador nao ve o estrato pela ordem
    return pool


# ── Estatistica ───────────────────────────────────────────────────────────────

def _po_pe(a: Sequence[int], b: Sequence[int]) -> tuple[float, float]:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return po, pe


def kappa(a: Sequence[int], b: Sequence[int]) -> float:
    """Cohen's kappa. NaN quando pe==1 (ambos rotularam tudo igual)."""
    if not a:
        return float("nan")
    po, pe = _po_pe(a, b)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def ac1(a: Sequence[int], b: Sequence[int]) -> float:
    """
    Gwet AC1 — robusto a prevalencia.

    Reportado ao lado do kappa sempre, e OBRIGATORIO quando a prevalencia sai de
    FAIXA_PREVALENCIA_OK (§3.3). Medido: no pool balanceado o AC1 infla 0.15
    contra o estrato operacional, entao ele tambem nao e imune a mistura — e
    checagem de robustez, nao substituto.
    """
    if not a:
        return float("nan")
    n = len(a)
    po, _ = _po_pe(a, b)
    pi = (sum(a) / n + sum(b) / n) / 2
    pe = 2 * pi * (1 - pi)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def kappa_ic(pares: Sequence[dict], a: str = "humano", b: str = "llm",
             n_boot: int = N_BOOTSTRAP, seed: int = SEED
             ) -> tuple[float, float, float]:
    """
    (kappa, lo, hi) com bootstrap de QUERY.

    Reamostra QUERIES, nao pares: dez julgamentos da mesma query sao
    correlacionados, e reamostrar par a par produz IC estreito demais. Mesmo
    motivo do bootstrap por turno na medicao de duplicacao de 19/08.
    """
    import numpy as np
    por_query: dict = {}
    for p in pares:
        por_query.setdefault(p["query"], []).append(p)
    chaves = list(por_query)
    if not chaves:
        return float("nan"), float("nan"), float("nan")

    ponto = kappa([p[a] for p in pares], [p[b] for p in pares])
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        amostra = [x for k in rng.choice(len(chaves), len(chaves))
                   for x in por_query[chaves[k]]]
        k = kappa([p[a] for p in amostra], [p[b] for p in amostra])
        if k == k:
            out.append(k)
    if not out:
        return ponto, float("nan"), float("nan")
    lo, hi = np.percentile(out, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return ponto, float(lo), float(hi)


# ── Veredito (§6, corrigido pelo §3.3) ────────────────────────────────────────

def confere_precondicao(pares: Sequence[dict]) -> dict:
    """
    O `controle` e pre-condicao, nao parcela do kappa (§3.3).

    Se os dois julgadores nao concordam nem sobre documento de OUTRO DOMINIO, o
    rubric nao reconhece negativo trivial. A rodada e declarada invalida — nao
    ajustada, nao reponderada.
    """
    ctrl = [p for p in pares if p["estrato"] == "controle"]
    if not ctrl:
        return {"ok": False, "motivo": "estrato `controle` vazio — sem controle negativo (§4.5)"}
    acordo = sum(p["humano"] == p["llm"] for p in ctrl) / len(ctrl)
    ok = acordo >= ACORDO_ESPERADO_CONTROLE
    return {
        "ok": ok,
        "acordo_controle": round(acordo, 4),
        "exigido": ACORDO_ESPERADO_CONTROLE,
        "n": len(ctrl),
        "motivo": None if ok else (
            f"acordo no controle {acordo:.3f} < {ACORDO_ESPERADO_CONTROLE}: o rubric "
            f"nao reconhece negativo trivial. Rodada INVALIDA (§3.3)."),
    }


def veredito(pares: Sequence[dict]) -> dict:
    """
    Veredito do §6, sobre o INTERVALO e sobre o estrato `topo`.

    Recusa julgar o pool completo: medido em 30/08, a mistura infla o kappa em
    0.07 contra o estrato operacional. Julgar o pool inteiro responderia uma
    pergunta mais facil que a do Recall@K.
    """
    pre = confere_precondicao(pares)
    if not pre["ok"]:
        return {"veredito": "INVALIDO — pre-condicao do controle falhou",
                "precondicao": pre, "nao_diz": "nada sobre o instrumento"}

    topo = [p for p in pares if p["estrato"] == ESTRATO_DO_GATE]
    if not topo:
        return {"veredito": "SEM DADO no estrato do gate", "precondicao": pre}

    k, lo, hi = kappa_ic(topo)
    n = len(topo)
    prev = (sum(p["humano"] for p in topo) / n + sum(p["llm"] for p in topo) / n) / 2
    fora = not (FAIXA_PREVALENCIA_OK[0] <= prev <= FAIXA_PREVALENCIA_OK[1])

    if lo > GATE_APROVA:
        v = "APROVADO para triagem"
    elif hi < GATE_REPROVA:
        v = "REPROVADO — Recall@K nao se constroi sobre este rotulo"
    else:
        v = (f"INCONCLUSIVO com este N — o IC atravessa um dos cortes "
             f"({GATE_REPROVA} / {GATE_APROVA}). NAO e 'os dois sao iguais'.")

    cauda = [p for p in pares if p["estrato"] == "cauda"]
    return {
        "veredito":     v,
        "estrato":      ESTRATO_DO_GATE,
        "n_pares":      n,
        "kappa":        round(k, 4),
        "ic95":         [round(lo, 4), round(hi, 4)],
        "ac1":          round(ac1([p["humano"] for p in topo], [p["llm"] for p in topo]), 4),
        "prevalencia":  round(prev, 4),
        "alerta_prevalencia": (
            f"prevalencia {prev:.2f} fora de {FAIXA_PREVALENCIA_OK} — o kappa esta "
            f"distorcido; leia o AC1 ao lado, com a prevalencia declarada (§3.3)"
            if fora else None),
        "precondicao":  pre,
        "cauda_reportada": {
            "n": len(cauda),
            "acordo": (round(sum(p["humano"] == p["llm"] for p in cauda) / len(cauda), 4)
                       if cauda else None),
            "papel": "especificidade do rubric — reportado, NAO entra no gate (§3.3)",
        },
        "nao_diz": ("nada sobre a VERDADE do rotulo. Concordancia nao e verdade "
                    "(NORTE §4.14): isto mede que o juiz concorda com ESTE "
                    "anotador, sob ESTE rubric, neste estrato."),
    }


def exige_estrato_do_gate(estrato: str) -> None:
    """Recusa rodar o gate fora do `topo`."""
    if estrato != ESTRATO_DO_GATE:
        raise RuntimeError(
            f"gate pedido sobre `{estrato}`. O §3.3 fixa `{ESTRATO_DO_GATE}`: o pool "
            f"completo infla o kappa em 0.07 (medido), e `cauda`/`controle` tem "
            f"papeis proprios — reportado e pre-condicao."
        )
