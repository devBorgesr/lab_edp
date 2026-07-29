#!/usr/bin/env python3
"""
sujeitos.edp.experimentos.exp_e7 — E7, HARNESS: mede retrieval real/shuffled/
neutra e aplica o critério de decisão. Implementa §3, §5, §6 de
docs/preregistro_experimento_e7.md. Constantes espelhadas do §8 LITERALMENTE.

DECISÃO DE DESENHO (registrada também em docs_edp_v5/RELATORIO_E7_HARNESS.md):
como restore() roda ANTES de cada query, o resultado do retrieve depende só
de (store, query) — não da vizinhança. Logo o retrieve roda UMA vez por turno
(n_turnos chamadas, não 2x): a condição `shuffled` é uma PERMUTAÇÃO da MESMA
lista de resultados já coletados, não uma segunda rodada. Fiel ao §3 ("os
MESMOS turnos, ordem embaralhada"), elimina variância entre condições, e é o
mesmo invariante que a matriz do exp017 provou (overlap depende só do PAR DE
CONJUNTOS, nunca de quando foram medidos).

Fluxo (só a partir do passo com sessão isolada toca `edp`; o resto é puro):
    a) lê e7_sequencia.jsonl (PASSO 1), confere sha256
    b) guarda de poder: n < MIN_TURNOS → PARA (não roda com n pequeno)
    c) sessão isolada (bancada/isolamento.py) + SujeitoEDP — restore
       (recarrega snapshot) ANTES de cada query, retrieve REAL via
       SujeitoEDP.consultar(query, k=TOP_K, min_score=MIN_SCORE)
    d) exporta e7_resultados.jsonl (ordem real, formato bancada/auditoria.py)
    e) métricas (§5, reusando bancada/auditoria.analyze_cross_query_repetition)
       + veredito (§6)

USO:
    EDP_BASE_DIR=/caminho/para/copia python3 -m \
        sujeitos.edp.experimentos.exp_e7 [--sequencia e7_sequencia.jsonl] [--out e7_resultados.jsonl]
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from pathlib import Path
from typing import Optional

from bancada.auditoria import analyze_cross_query_repetition
from bancada.scorer import wilson

# ── Constantes congeladas (§8), espelhadas LITERALMENTE ──────────────────────
EXPERIMENTO = "E7"
TOP_K = 5
MIN_SCORE = 0.20
SEED_SHUFFLE = 20260728
MIN_TURNOS = 20
CORTE_H1_PP = 15.0
CORTE_H0_PP = 5.0
PREFIXO_EXCLUIDO = "[session_summary]"  # já aplicado no PASSO 1; espelhado por completude
SCOPE = "cognitive"


def _die(msg: str, code: int = 2) -> None:
    print(f"\n[ERRO] {msg}\n", file=sys.stderr)
    sys.exit(code)


def _sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _ler_sequencia(path: Path) -> list:
    """1 objeto JSON por linha ({"query","id","timestamp"}), ordem preservada
    — a ordem do arquivo É a ordem real (o PASSO 1 já ordenou por timestamp)."""
    sequencia = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                sequencia.append(json.loads(line))
    return sequencia


# ── §5: métricas (reusa bancada/auditoria.py; só o que falta é escrito aqui) ─

def permuta_shuffled(records: list, seed: int = SEED_SHUFFLE) -> list:
    """Controle negativo do §3: OS MESMOS registros (mesmos conjuntos de
    resultados), ordem embaralhada com seed congelada. NÃO refaz o retrieve —
    é uma permutação da lista já coletada (decisão de desenho do topo)."""
    rng = random.Random(seed)
    out = list(records)
    rng.shuffle(out)
    return out


def calcula_condicao(records: list, top_k: int = TOP_K) -> dict:
    """Binário/contínuo observados (pares consecutivos NA ORDEM de `records`)
    + Wilson 95% sobre o binário + referência neutra (matriz completa —
    idêntica independente da ordem, permutation-invariant por construção)."""
    rep = analyze_cross_query_repetition(records, top_k)
    consecutivos = rep.get("consecutive") or []
    n_pares = len(consecutivos)
    k_bin = sum(1 for p in consecutivos if p["binary"])
    ci_low, ci_high = wilson(k_bin, n_pares)
    return {
        "n_pares": n_pares,
        "k_bin": k_bin,
        "binario": rep["cons_binary_rate"],
        "continuo": rep["cons_continuous_mean"],
        "ref_binario": rep["ref_binary_rate"],
        "ref_continuo": rep["ref_continuous_mean"],
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


# ── §6: veredito (critério travado; não decide nada além da tabela) ──────────

def classifica_veredito(gap_pp: float) -> str:
    if gap_pp >= CORTE_H1_PP:
        return "H1 — TOPICALIDADE DOMINA"
    if gap_pp <= CORTE_H0_PP:
        return "H0 — PATOLOGIA"
    return "MISTO"


def instrumento_valido(ref: Optional[float], a: float, b: float) -> Optional[bool]:
    """Critério de validade do instrumento: a referência neutra deve cair
    ENTRE shuffled e real (se H1 for verdadeira). None se ref indisponível."""
    if ref is None:
        return None
    lo, hi = (a, b) if a <= b else (b, a)
    return lo <= ref <= hi


def calcula_veredito(records: list, top_k: int = TOP_K, seed: int = SEED_SHUFFLE) -> dict:
    real = calcula_condicao(records, top_k)
    shuffled = calcula_condicao(permuta_shuffled(records, seed), top_k)
    gap_pp = (real["binario"] - shuffled["binario"]) * 100
    return {
        "real": real,
        "shuffled": shuffled,
        "gap_pp": gap_pp,
        "veredito": classifica_veredito(gap_pp),
        "instrumento_valido": instrumento_valido(
            real["ref_binario"], real["binario"], shuffled["binario"]
        ),
    }


def _fmt_pct(x: Optional[float]) -> str:
    return f"{x * 100:.1f}%" if x is not None else "N/D"


def imprime_relatorio(resultado: dict) -> None:
    r, s = resultado["real"], resultado["shuffled"]
    print("\n" + "=" * 70)
    print("E7 — HARNESS (repeat_rate: topicalidade vs patologia)")
    print("=" * 70)
    print(f"  {'condicao':<12}{'binario':<12}{'IC95%':<20}{'continuo':<12}{'n_pares'}")
    for rot, c in (("real", r), ("shuffled", s)):
        ci = f"[{_fmt_pct(c['ci_low'])}, {_fmt_pct(c['ci_high'])}]"
        print(f"  {rot:<12}{_fmt_pct(c['binario']):<12}{ci:<20}{_fmt_pct(c['continuo']):<12}{c['n_pares']}")
    print(f"  {'neutra':<12}{_fmt_pct(r['ref_binario']):<12}{'—':<20}{_fmt_pct(r['ref_continuo']):<12}(matriz completa)")
    print(f"\n  gap (real - shuffled, binário) : {resultado['gap_pp']:+.1f}pp")
    print(f"  VEREDITO (§6, critério travado): {resultado['veredito']}")
    iv = resultado["instrumento_valido"]
    if iv is None:
        print("  validade do instrumento         : N/D (referência neutra indisponível)")
    elif iv:
        print("  validade do instrumento         : OK (referência neutra caiu entre shuffled e real)")
    else:
        print("  validade do instrumento         : SUSPEITO — referência neutra FORA do intervalo "
              "[shuffled, real]. Achado sobre o INSTRUMENTO, não sobre o fenômeno.")
    print("=" * 70)
    print("  (O veredito final — inclusive em caso MISTO — é do pesquisador, não deste script.)")


# ── main: I/O + orquestração do retrieve REAL ────────────────────────────────

def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="E7 - Harness: mede retrieval real/shuffled/neutra (§3, §5, §6)."
    )
    p.add_argument("--sequencia", default="e7_sequencia.jsonl",
                    help="jsonl produzido pelo PASSO 1 (e7_extrai_sequencia.py)")
    p.add_argument("--out", default="e7_resultados.jsonl",
                    help="export dos resultados do retrieve (ordem real)")
    args = p.parse_args(argv)

    seq_path = Path(args.sequencia)
    if not seq_path.exists():
        _die(f"sequência não encontrada: {seq_path}. Rode e7_extrai_sequencia.py "
             f"(PASSO 1) primeiro.")

    sha_lido = _sha256_arquivo(seq_path)
    sequencia = _ler_sequencia(seq_path)
    n = len(sequencia)
    print(f"sequencia          : {seq_path}")
    print(f"sha256(sequencia)  : {sha_lido}  (confira contra o sha256 impresso pelo PASSO 1)")
    print(f"n_turnos           : {n}")

    if n < MIN_TURNOS:
        print(f"n < {MIN_TURNOS}: PARAR (poder insuficiente, §4) — harness não mede retrieval.")
        return 0

    # ── daqui em diante toca `edp` (isolamento real) ────────────────────────
    from bancada.isolamento import experimental_session, verify_no_leak
    from sujeitos.edp.adaptador import SujeitoEDP

    prod_session = os.environ.get("EDP_SESSION_ID", "default")
    scope = os.environ.get("EDP_SCOPE", SCOPE)
    sujeito = SujeitoEDP(prod_session=prod_session, scope=scope)

    fp_before = sujeito.fingerprint_producao()
    entries = sujeito.exportar_producao()

    records = []
    with experimental_session(sujeito, purge=True) as lab_session_id:
        for turno in sequencia:
            sujeito.carregar_snapshot(lab_session_id, entries)  # restore (§7): antes de CADA query
            resultados = sujeito.consultar(lab_session_id, turno["query"], TOP_K, min_score=MIN_SCORE)
            records.append({
                "query": turno["query"],
                "results": [
                    {"id": item.get("id"), "texto": item.get("texto", ""), "score": item.get("score", 0.0)}
                    for item in resultados
                ],
            })

    fp_after = sujeito.fingerprint_producao()
    if not verify_no_leak(fp_before, fp_after):
        raise RuntimeError(
            "VAZAMENTO DETECTADO (INV-5): fingerprint da produção mudou entre "
            "antes/depois do experimento. Nenhum resultado é reportado."
        )

    out_path = Path(args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"resultados         : {out_path} ({len(records)} queries, ordem real)")

    resultado = calcula_veredito(records)
    imprime_relatorio(resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
