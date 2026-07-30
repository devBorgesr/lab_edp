#!/usr/bin/env python3
"""
sujeitos.edp.experimentos.exp018_veredito — lê o JSON acumulado por
sujeitos/edp/experimentos/exp018.py e aplica o §6 de
docs/preregistro_experimento_018.md. Script separado, lógica pura sobre o
dict de resultados (nenhum import de `edp`).

Ordem de leitura OBRIGATÓRIA (§6): valida C5/C6 (instrumento) ANTES de
interpretar qualquer H1/H2/H3. Se a validação falhar, ou se C7 não tiver
fundido, imprime INCONCLUSIVO e PARA — não decide nada além da tabela do §6.
O veredito final é do pesquisador.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def valida_instrumento(resultados: dict) -> tuple:
    """C5 (ambas as funções) deve promover >=1; C6 (ambas) deve promover 0.
    Retorna (valido, motivos) — motivos vazio se valido."""
    motivos = []
    for funcao in ("consolidate", "consolidate_promote_only"):
        c5 = resultados.get(f"C5/{funcao}")
        if c5 is None:
            motivos.append(f"C5/{funcao} ausente")
        elif c5["promovidas_total"] < 1:
            motivos.append(f"C5/{funcao} promoveu 0 (esperado >=1 — controle+ inválido)")
        c6 = resultados.get(f"C6/{funcao}")
        if c6 is None:
            motivos.append(f"C6/{funcao} ausente")
        elif c6["promovidas_total"] >= 1:
            motivos.append(f"C6/{funcao} promoveu {c6['promovidas_total']} (esperado 0 — controle− inválido)")
    return (len(motivos) == 0, motivos)


def classifica_h1(resultados: dict) -> Optional[bool]:
    """H1: qualquer entry tóxica aparece em semantic após C1 OU C2."""
    c1 = resultados.get("C1/consolidate")
    c2 = resultados.get("C2/consolidate")
    if c1 is None or c2 is None:
        return None
    return (c1["promovidas_total"] > 0) or (c2["promovidas_total"] > 0)


def classifica_h2(resultados: dict) -> Optional[bool]:
    """H2: C3 promove 0 E C4 promove >=1 (guarda acoplada à flag)."""
    c3 = resultados.get("C3/consolidate_promote_only")
    c4 = resultados.get("C4/consolidate_promote_only")
    if c3 is None or c4 is None:
        return None
    return (c3["promovidas_total"] == 0) and (c4["promovidas_total"] >= 1)


def classifica_h3(resultados: dict) -> Optional[bool]:
    """H3: C7 promove a fundida e ela vem SEM answer_class."""
    c7 = resultados.get("C7/consolidate")
    if c7 is None or not c7.get("fundiu"):
        return None
    return c7.get("answer_class_presente") is False


def classifica_h0(resultados: dict) -> Optional[bool]:
    """H0: C1..C4 e C7 promovem 0, C5 (consolidate) promove >=1.

    "C7 promove 0" usa `promovida_fundida` (não `n_semantic_apos`): esta
    função só é chamada depois que `calcula_veredito` já confirmou que C7
    FUNDIU (§6, gate anterior a este) — o caso relevante aqui é fundiu-mas-
    não-promoveu, que só `promovida_fundida=False` representa sem
    contradição (ver docstring de `inspeciona_resultado` em exp018.py)."""
    chaves_zero = (
        "C1/consolidate", "C2/consolidate",
        "C3/consolidate_promote_only", "C4/consolidate_promote_only",
    )
    c7 = resultados.get("C7/consolidate")
    c5 = resultados.get("C5/consolidate")
    if any(resultados.get(k) is None for k in chaves_zero) or c7 is None or c5 is None:
        return None
    zero_c1_c4 = all(resultados[k]["promovidas_total"] == 0 for k in chaves_zero)
    zero_c7 = not c7.get("promovida_fundida", False)
    c5_promoveu = c5["promovidas_total"] >= 1
    return zero_c1_c4 and zero_c7 and c5_promoveu


def divergencia_classes(resultados: dict) -> dict:
    """§4 (predição pré-dado): as duas classes tóxicas deveriam se comportar
    de forma idêntica. Reporta as condições onde not_found != disqualification."""
    divergiu = {}
    for chave in (
        "C1/consolidate", "C2/consolidate",
        "C3/consolidate_promote_only", "C4/consolidate_promote_only",
    ):
        r = resultados.get(chave)
        if r is None:
            continue
        classes = r.get("promovidas_por_classe", {})
        nf, dq = classes.get("not_found", 0), classes.get("disqualification", 0)
        if nf != dq:
            divergiu[chave] = {"not_found": nf, "disqualification": dq}
    return divergiu


def calcula_veredito(resultados: dict) -> dict:
    """Aplica o §6 na ORDEM OBRIGATÓRIA: instrumento (C5/C6) -> C7 fundiu? ->
    só então H1/H2/H3/H0. NÃO decide nada além da tabela."""
    instrumento_ok, motivos = valida_instrumento(resultados)
    if not instrumento_ok:
        return {
            "veredito": "INCONCLUSIVO",
            "motivo": "instrumento inválido: " + "; ".join(motivos),
        }

    c7 = resultados.get("C7/consolidate")
    if c7 is not None and not c7.get("fundiu"):
        return {
            "veredito": "INCONCLUSIVO",
            "motivo": (
                "C7 não fundiu (merged_from != 2) — o cluster não fundiu; "
                "ajustar a similaridade dos embeddings plantados, NUNCA o "
                "threshold do EDP (§5)."
            ),
        }

    return {
        "veredito": "CLASSIFICADO",
        "H1_confirmada": classifica_h1(resultados),
        "H2_confirmada": classifica_h2(resultados),
        "H3_confirmada": classifica_h3(resultados),
        "H0": classifica_h0(resultados),
        "divergencia_classes_toxicas": divergencia_classes(resultados),
    }


def _fmt(v) -> str:
    return "N/D (dados insuficientes)" if v is None else str(v)


def imprime_veredito(veredito: dict) -> None:
    print("\n" + "=" * 70)
    print("exp018 — VEREDITO (§6, critério travado)")
    print("=" * 70)
    if veredito["veredito"] == "INCONCLUSIVO":
        print("VEREDITO: INCONCLUSIVO")
        print(f"  motivo: {veredito['motivo']}")
        print("  (instrumento errado — nada se conclui sobre toxicidade)")
    else:
        print(f"H1 (vazamento sem guarda, C1/C2)   : {_fmt(veredito['H1_confirmada'])}")
        print(f"H2 (guarda acoplada à flag, C3/C4)  : {_fmt(veredito['H2_confirmada'])}")
        print(f"H3 (fix ingênuo insuficiente, C7)   : {_fmt(veredito['H3_confirmada'])}")
        print(f"H0 (nenhum caminho promove tóxico)  : {_fmt(veredito['H0'])}")
        div = veredito["divergencia_classes_toxicas"]
        if div:
            print(f"  DIVERGÊNCIA entre classes tóxicas (achado próprio): {div}")
        else:
            print("  classes tóxicas (not_found vs disqualification): comportamento idêntico onde medido")
    print("=" * 70)
    print("  (O veredito final — inclusive em caso MISTO/INCONCLUSIVO — é do pesquisador.)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="exp018 - Veredito: aplica o §6 sobre o JSON acumulado de exp018.py"
    )
    p.add_argument("--resultados", default="exp018_resultados.json",
                    help="JSON acumulado gravado por exp018.py")
    args = p.parse_args(argv)

    path = Path(args.resultados)
    if not path.exists():
        print(f"\n[ERRO] resultados não encontrados: {path}. Rode exp018.py primeiro.\n",
              file=sys.stderr)
        return 2

    resultados = json.loads(path.read_text(encoding="utf-8"))
    veredito = calcula_veredito(resultados)
    imprime_veredito(veredito)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
