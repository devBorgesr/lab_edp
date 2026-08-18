"""
exp_e10 — Encarnacao em CODIGO do Experimento E10 (verificador de proveniencia).

Espelha docs/preregistro_experimento_e10.md. CONGELADO apos o 1o disparo real.
Mudou a regua -> e o E10b.

A PERGUNTA: um verificador puramente LEXICO separa "a afirmacao esta na
memoria citada" de "nao esta"?

POR QUE IMPORTA: num laco autonomo nao ha usuario para corrigir. O unico
critico do EDP e a Camara de Eco, que dispara por regex sobre a admissao do
proprio modelo — recompensa com conjunto vazio alcancavel em uma jogada. A
alternativa e ancorar em algo que o operador NAO consegue emitir: a afirmacao
cita entry_id, e o verificador ABRE a entrada.

NAO FAZ INFERENCIA. Nenhuma chamada a modelo. Leitura pura de episodic.json —
nao chama retrieve() (que muta acessos/ultimo_acesso e persiste), nao escreve
em data/sessions/.

ANTI-MOCK: `negation_asymmetry` e a funcao DE PRODUCAO do
edp.runtime.contradiction_flagger, nao reimplementada. Exige o edp_v5 no
PYTHONPATH, como monitora_coleta.py ja faz.

CRITERIO LIVRE DE LIMIAR (§6): com 16 pares por estrato, escolher limiar seria
sobreajuste — e seria a QUARTA constante Tier A deste arco, depois de
LOAD_DURATION_MAX_FRAC e dos dois DELTA_EQUIV. A hipotese e de separacao
completa: min(A) > max(B).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from pathlib import Path
from typing import Optional

_RAIZ = Path(__file__).resolve().parents[3]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from bancada.scorer import wilson  # noqa: E402


# ── Constantes CONGELADAS (§11 do pre-registro) ──────────────────────────────
EXPERIMENTO   = "E10"
N_PARES       = 16
MIN_TOKEN_LEN = 3
STOPWORDS     = frozenset({'para', 'com', 'que', 'uma', 'dos', 'das', 'nao',
                           'por', 'como', 'mas', 'seu', 'sua', 'aos', 'nas',
                           'nos', 'ele', 'ela', 'isso', 'esta', 'este'})
TROCA_OFFSET  = 1
Z_WILSON      = 1.96
SEED          = 20260818
DIVISOR_CEGO  = 100.0          # E10-1
CONDICOES     = ("cego", "lexico", "lexico_negacao")
ESTRATOS      = ("suportada", "trocada", "negada")

# §4 — negacao mecanica, congelada. Verbo reconhecido -> insere " nao " depois;
# nenhum casa -> prefixa. A lista e impressa na prova-no-espelho.
VERBOS = ("requer", "requerem", "passaram", "passou", "existe", "existem",
          "deve", "devem", "pode", "podem", "tem", "têm", "usa", "usam",
          "precisa", "precisam", "gera", "geram", "causa", "causam",
          "permite", "permitem", "é", "e", "sao", "são", "foi", "foram",
          "esta", "está", "estao", "estão")
PREFIXO_NEGACAO = "Nao e verdade que "

BASE = Path(os.environ.get("EDP_BASE_DIR", "data"))
STORE = BASE / "sessions" / "default_cognitive" / "episodic.json"


def kernel_resolvido() -> str:
    """
    De ONDE o `edp` importou (emenda E10-2). Nao e diagnostico opcional.

    Medido em 18/08: sem PYTHONPATH, `edp` resolve para
    ~/.local/lib/python3.11/site-packages/edp/ — copia INSTALADA de 492 linhas,
    anterior a telemetria de contradicao de 13/08, contra 527 do kernel vivo.
    O E10 importaria `negation_asymmetry` de outra build e NADA avisaria.

    Anti-mock (§10) exige a funcao DE PRODUCAO. Uma copia instalada nao e
    producao — e um retrato dela, de data desconhecida. Por isso isto RECUSA
    em vez de avisar, e o caminho resolvido vai para o registro bruto: um
    experimento sobre proveniencia registrando a propria proveniencia.
    """
    import edp
    caminho = str(pathlib.Path(edp.__file__).resolve().parent)
    if "site-packages" in caminho or "dist-packages" in caminho:
        raise RuntimeError(
            f"edp resolveu para copia INSTALADA: {caminho}\n"
            "  O E10 exige a funcao de producao, nao um retrato dela.\n"
            "  Rode com o kernel no PYTHONPATH:\n"
            "    PYTHONPATH=/media/sf_edp_v5_main python sujeitos/edp/experimentos/exp_e10.py"
        )
    esperado = os.environ.get("EDP_KERNEL")
    if esperado and not caminho.startswith(str(pathlib.Path(esperado).resolve())):
        raise RuntimeError(f"edp em {caminho}, mas EDP_KERNEL aponta {esperado}")
    return caminho


def _negacao_asimetrica(a: str, b: str) -> bool:
    """Funcao DE PRODUCAO. Import tardio para a mensagem de erro ser util."""
    try:
        kernel_resolvido()
        from edp.runtime.contradiction_flagger import negation_asymmetry
    except ImportError as e:
        raise RuntimeError(
            "edp.runtime.contradiction_flagger nao importavel. O E10 usa a "
            "funcao DE PRODUCAO (anti-mock, §10). Rode com o edp_v5 no "
            "PYTHONPATH:  PYTHONPATH=/caminho/edp_v5 python ..."
        ) from e
    return negation_asymmetry(a, b)


# ── Tokenizacao (§5) ─────────────────────────────────────────────────────────

def tok(s: str) -> set:
    bruto = re.split(r"[^0-9A-Za-zÀ-ÿ]+", (s or "").lower())
    return {t for t in bruto if len(t) >= MIN_TOKEN_LEN and t not in STOPWORDS}


# ── Negacao mecanica (§4) ────────────────────────────────────────────────────

def negar(afirmacao: str) -> tuple:
    """Devolve (texto_negado, regra_aplicada) — a regra vai no registro bruto."""
    palavras = (afirmacao or "").split()
    for i, p in enumerate(palavras):
        limpo = re.sub(r"[^0-9A-Za-zÀ-ÿ]", "", p).lower()
        if limpo in VERBOS:
            return " ".join(palavras[:i + 1] + ["nao"] + palavras[i + 1:]), f"verbo:{limpo}"
    return PREFIXO_NEGACAO + (afirmacao or ""), "prefixo"


# ── Verificadores (§5) ───────────────────────────────────────────────────────

def escore_cego(afirmacao: str, texto: str) -> float:
    """
    IGNORA `texto` (E10-1). Escore so do tamanho da afirmacao.

    Nao e constante de proposito: constante tornaria min(A) > max(B) falso por
    construcao e o controle nao poderia falhar. Assim ele tem dois
    comportamentos, e ambos informam — ver §5 do pre-registro.
    """
    return len(tok(afirmacao)) / DIVISOR_CEGO


def escore_lexico(afirmacao: str, texto: str) -> float:
    ta = tok(afirmacao)
    if not ta:
        return 0.0
    return len(ta & tok(texto)) / len(ta)


def escore_lexico_negacao(afirmacao: str, texto: str) -> float:
    if _negacao_asimetrica(afirmacao, texto):
        return 0.0
    return escore_lexico(afirmacao, texto)


VERIFICADORES = {
    "cego":           escore_cego,
    "lexico":         escore_lexico,
    "lexico_negacao": escore_lexico_negacao,
}


# ── Dataset (§4) — gabarito por construcao ───────────────────────────────────

def carregar_universo(caminho: Path = None) -> list:
    """
    Entradas com key_assertion nao-vazio. LEITURA PURA — nao instancia store,
    nao chama retrieve, nao persiste nada.

    Ordenado por `id` para o dataset ser reproduzivel independente da ordem do
    arquivo. `N_PARES` e o tamanho do universo medido, nao uma escolha (§11).
    """
    p = Path(caminho or STORE)
    d = json.loads(p.read_text(encoding="utf-8"))
    ents = d if isinstance(d, list) else (d.get("entries") or [])
    universo = []
    for e in ents:
        ka = ((e.get("cognitive_decisions") or {}).get("key_assertion") or "").strip()
        txt = (e.get("text") or "").strip()
        if ka and txt and (e.get("id") or "").strip():
            universo.append({"id": e["id"], "afirmacao": ka, "texto": txt})
    return sorted(universo, key=lambda x: x["id"])


def montar_pares(universo: list) -> list:
    """Tres estratos, gabarito por construcao. Troca deterministica (§4)."""
    n = len(universo)
    pares = []
    for i, u in enumerate(universo):
        viz = universo[(i + TROCA_OFFSET) % n]
        negada, regra = negar(u["afirmacao"])
        pares += [
            {"estrato": "suportada", "afirmacao": u["afirmacao"],
             "texto": u["texto"], "id_texto": u["id"], "gabarito": True,
             "regra": ""},
            {"estrato": "trocada", "afirmacao": u["afirmacao"],
             "texto": viz["texto"], "id_texto": viz["id"], "gabarito": False,
             "regra": ""},
            {"estrato": "negada", "afirmacao": negada,
             "texto": u["texto"], "id_texto": u["id"], "gabarito": False,
             "regra": regra},
        ]
    return pares


def pontuar(pares: list) -> list:
    for p in pares:
        for nome, fn in VERIFICADORES.items():
            p[f"escore_{nome}"] = round(fn(p["afirmacao"], p["texto"]), 6)
    return pares


# ── Criterio (§6) — separacao completa, sem limiar ───────────────────────────

def _escores(pares: list, cond: str, estrato: str) -> list:
    return [p[f"escore_{cond}"] for p in pares if p["estrato"] == estrato]


def separa(pares: list, cond: str, a: str, b: str) -> tuple:
    """SEPARA(A,B) <=> min(A) > max(B). Devolve (bool, min_a, max_b)."""
    ea, eb = _escores(pares, cond, a), _escores(pares, cond, b)
    if not ea or not eb:
        return (False, None, None)
    return (min(ea) > max(eb), min(ea), max(eb))


def score_e10(pares: list) -> dict:
    out = {"n_por_estrato": {e: len(_escores(pares, "lexico", e)) for e in ESTRATOS},
           "checks": [], "separacoes": {}}

    for cond in CONDICOES:
        for a, b in (("suportada", "trocada"), ("suportada", "negada")):
            ok, mn, mx = separa(pares, cond, a, b)
            out["separacoes"][f"{cond}:{a}>{b}"] = {
                "separa": ok, "min_a": mn, "max_b": mx,
                "margem": None if mn is None else round(mn - mx, 6)}

    def _reg(nome, ok, det):
        out["checks"].append({"check": nome, "ok": ok, "detalhe": det})
        return ok

    s = out["separacoes"]

    # 1. VALIDADE-a — cego nao pode separar suportada de trocada
    v = s["cego:suportada>trocada"]
    if not _reg("1 VALIDADE-a (cego nao separa trocada)", not v["separa"],
                f"min={v['min_a']} max={v['max_b']} separa={v['separa']}"):
        out["veredito"] = "INSTRUMENTO INVALIDO"
        out["motivo"] = ("suportada e trocada usam as MESMAS afirmacoes; um "
                         "verificador que ignora o texto nao pode separa-las. "
                         "Separou -> vazamento no encanamento.")
        return out

    # 2. VALIDADE-b — cego nao pode separar suportada de negada
    v = s["cego:suportada>negada"]
    if not _reg("2 VALIDADE-b (cego nao separa negada)", not v["separa"],
                f"min={v['min_a']} max={v['max_b']} separa={v['separa']}"):
        out["veredito"] = "ESTRATO negada CONFUNDIDO"
        out["motivo"] = ("a negacao mecanica e detectavel pelo TAMANHO da "
                         "afirmacao, sem ler o texto. H2/H3 deixariam de ser "
                         "sobre contradicao.")
        return out

    # 3. SANIDADE — estratos completos
    faltando = {e: N_PARES - n for e, n in out["n_por_estrato"].items() if n != N_PARES}
    if not _reg("3 SANIDADE (estratos completos)", not faltando,
                f"n={out['n_por_estrato']} esperado={N_PARES}"):
        out["veredito"] = "DATASET INCOMPLETO"
        out["faltando"] = faltando
        return out

    # 4/5/6 — confirmatorios
    h1 = s["lexico:suportada>trocada"]["separa"]
    _reg("4 H1 (lexico separa trocada)", h1,
         f"margem={s['lexico:suportada>trocada']['margem']}")
    h2 = not s["lexico:suportada>negada"]["separa"]
    _reg("5 H2 (lexico FALHA em negada)", h2,
         f"separa={s['lexico:suportada>negada']['separa']}")
    h3 = not s["lexico_negacao:suportada>negada"]["separa"]
    _reg("6 H3 (lexico_negacao TAMBEM falha)", h3,
         f"separa={s['lexico_negacao:suportada>negada']['separa']}")

    out["H1"], out["H2"], out["H3"] = h1, h2, h3
    confirmadas = [n for n, v in (("H1", h1), ("H2", h2), ("H3", h3)) if v]
    out["veredito"] = ("TODAS CONFIRMADAS (H1+H2+H3)" if len(confirmadas) == 3
                       else f"PARCIAL — confirmadas: {', '.join(confirmadas) or 'nenhuma'}")
    return out


def descritivos(pares: list) -> dict:
    """
    Acuracia por estrato ao melhor limiar observado, com Wilson 95%.

    DESCRITIVO, explicitamente NAO criterio (§6). Serve para dimensionar o
    E10b. Escolher limiar apos ver o dado e exatamente o que o §6 evita — por
    isso este numero nao decide nada.
    """
    out = {}
    for cond in CONDICOES:
        todos = sorted({p[f"escore_{cond}"] for p in pares})
        melhor, corte = -1.0, None
        for c in todos:
            acertos = sum(1 for p in pares
                          if (p[f"escore_{cond}"] >= c) == p["gabarito"])
            if acertos > melhor:
                melhor, corte = acertos, c
        lo, hi = wilson(int(melhor), len(pares), Z_WILSON)
        out[cond] = {"acuracia": round(melhor / len(pares), 4),
                     "ic95": (round(lo, 4), round(hi, 4)), "corte": corte}
    return out


# ── Saida ────────────────────────────────────────────────────────────────────

def _imprimir(pares: list, v: dict, desc: dict, mostrar_dataset: bool) -> None:
    print("\n" + "=" * 74)
    print(f"E10 — verificador de proveniencia  ({'PROVA-NO-ESPELHO' if mostrar_dataset else 'REAL'})")
    print("=" * 74)
    print(f"  store    : {STORE}")
    try:
        print(f"  kernel   : {kernel_resolvido()}")
    except RuntimeError as e:
        print(f"  kernel   : RECUSADO — {str(e).splitlines()[0]}")
    print(f"  pares    : {len(pares)}  ({v['n_por_estrato']})")

    if mostrar_dataset:
        print(f"\n  regra de negacao (§4) — VERBOS={len(VERBOS)}, senao prefixa "
              f"{PREFIXO_NEGACAO!r}:")
        for p in pares:
            if p["estrato"] == "negada":
                print(f"    [{p['regra']:<12}] {p['afirmacao'][:88]}")

    print("\n  separacoes  min(A) > max(B):")
    for k, s in v["separacoes"].items():
        marca = "SEPARA" if s["separa"] else "  --  "
        print(f"    [{marca}] {k:<42} min={s['min_a']:.4f} max={s['max_b']:.4f} "
              f"margem={s['margem']:+.4f}")

    print()
    for c in v["checks"]:
        print(f"    [{'ok ' if c['ok'] else 'FALHA'}] {c['check']:<38} {c['detalhe']}")

    print(f"\n    VEREDITO : {v['veredito']}")
    if v.get("motivo"):
        print(f"    motivo   : {v['motivo']}")

    print("\n  descritivo (NAO e criterio, §6) — acuracia ao melhor limiar observado:")
    for cond, d in desc.items():
        print(f"    {cond:<16} acc={d['acuracia']:.3f}  IC95=[{d['ic95'][0]:.3f}, "
              f"{d['ic95'][1]:.3f}]  corte={d['corte']:.4f}")
    print("=" * 74)


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Experimento E10")
    p.add_argument("--dry-run", action="store_true",
                   help="prova-no-espelho: imprime o dataset e a regra de negacao")
    p.add_argument("--store", default=None, help="caminho do episodic.json")
    p.add_argument("--saida", default="e10_pares.jsonl")
    args = p.parse_args(argv)

    try:
        universo = carregar_universo(Path(args.store) if args.store else None)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"\n[RECUSADO] store ilegivel em {args.store or STORE}: {e}")
        return 1
    if not universo:
        print(f"\n[RECUSADO] nenhuma entrada com key_assertion em {args.store or STORE}")
        return 1

    try:
        pares = pontuar(montar_pares(universo))
    except RuntimeError as e:
        print(f"\n[RECUSADO] {e}")
        return 1

    v, desc = score_e10(pares), descritivos(pares)
    if not args.dry_run:
        Path(args.saida).write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in pares),
            encoding="utf-8")
    _imprimir(pares, v, desc, mostrar_dataset=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
