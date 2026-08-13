#!/usr/bin/env python3
"""
monitora_coleta.py — acompanha a janela de coleta da Fase 2 SEM olhar a razão.

O pré-registro congelado (`docs/preregistro_fase2_calibracao_tokens.md`) permite
olhar N acumulado — é a regra de parada — e proíbe olhar a razão, porque parada
por resultado observado invalidaria o critério.

**Este script existe porque a primeira versão do comando de verificação violava
isso.** Ela imprimia `text_chars -> input_tokens` de amostras de exemplo, que é
a razão em duas colunas. Nenhum agregado é calculado aqui, e os campos que
compõem a razão nunca são impressos — nem individualmente, porque duas colunas
lado a lado são um convite a dividir.

O que sai daqui: contagens. Cascata de exclusão (§10 do contrato), n por
estrato contra `n_min`, e progresso contra a regra de parada.

USO:  python3 sujeitos/edp/monitora_coleta.py [--jsonl CAMINHO]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

# Constantes congeladas no pré-registro — não são ajustáveis por flag aqui de
# propósito: mudá-las é mudar a regra de parada, e isso exige Fase 2b.
N_ALVO = 300
N_MIN_ESTRATO = 30
CLASSES = ("acentuado", "codigo", "ascii")

_CAMPOS_PROIBIDOS = ("text_chars", "payload_bytes", "usage")


def carrega(caminho: Path) -> list[dict]:
    if not caminho.exists():
        print(f"sem arquivo em {caminho} — a coleta já rodou?")
        return []
    evs = []
    for i, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        if not linha.strip():
            continue
        try:
            evs.append(json.loads(linha))
        except json.JSONDecodeError:
            print(f"  linha {i} malformada, pulada")
    return evs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    base = os.environ.get("EDP_BASE_DIR", "data")
    ap.add_argument("--jsonl", type=Path,
                    default=Path(base) / "pareto" / "events.jsonl")
    args = ap.parse_args()

    # O import precisa do edp no path — este script é do SUJEITO, não da
    # bancada, justamente por conhecer o schema token_usage.
    try:
        from edp.runtime.pareto_store import amostra_valida_fase2
    except ImportError:
        print("edp não importável — rode com o edp_v5 no PYTHONPATH")
        return 1

    evs = carrega(args.jsonl)
    if not evs:
        return 0

    tok = [e for e in evs if e.get("event") == "token_usage"]

    # Cascata do §10 — toda redução explicável, nunca um N solto
    com_provider = [e for e in tok if e.get("provider") == "anthropic"]
    com_regime = [e for e in com_provider if e.get("format_state") is not None]
    u = lambda e: e.get("usage") or {}
    com_tokens = [e for e in com_regime
                  if u(e).get("input_tokens") is not None
                  and u(e).get("output_tokens") is not None]
    populacao = [e for e in tok if amostra_valida_fase2(e)]

    print(f"jsonl: {args.jsonl}\n")
    print("CASCATA (§10 do contrato — toda redução explicável)")
    print(f"  eventos no arquivo                {len(evs):5d}")
    print(f"  token_usage                       {len(tok):5d}")
    print(f"  ├─ provider anthropic             {len(com_provider):5d}"
          f"   (-{len(tok)-len(com_provider)})")
    print(f"  ├─ com format_state               {len(com_regime):5d}"
          f"   (-{len(com_provider)-len(com_regime)}  câmara / cognitive_decisions)")
    print(f"  ├─ com tokens completos           {len(com_tokens):5d}"
          f"   (-{len(com_regime)-len(com_tokens)})")
    print(f"  └─ POPULAÇÃO Fase 2               {len(populacao):5d}")

    if len(populacao) != len(com_tokens):
        print("  !! divergência entre a cascata manual e amostra_valida_fase2 —"
              " o predicado mudou sem este script saber")

    print("\nESTRATO PRIMÁRIO (classe) — critério exige n >= "
          f"{N_MIN_ESTRATO}")
    por_classe = Counter(e.get("classe") for e in populacao)
    for c in CLASSES:
        n = por_classe.get(c, 0)
        marca = "ok" if n >= N_MIN_ESTRATO else f"faltam {N_MIN_ESTRATO - n}"
        print(f"  {c:<12} {n:5d}   {marca}")
    extras = set(por_classe) - set(CLASSES)
    for c in sorted(extras):
        print(f"  {str(c):<12} {por_classe[c]:5d}   (fora dos 3 estratos)")

    print("\nREGIME DE FORMATO (secundário, descritivo)")
    for h, n in Counter(e.get("format_hash") for e in populacao).most_common():
        modo = next((e["format_state"].get("mode") for e in populacao
                     if e.get("format_hash") == h), "?")
        print(f"  {h}  modo={modo:<10} {n:5d}")

    print(f"\nREGRA DE PARADA: {len(populacao)}/{N_ALVO} amostras válidas"
          f"   ({100*len(populacao)/N_ALVO:.0f}%)")
    faltando = [c for c in CLASSES if por_classe.get(c, 0) < N_MIN_ESTRATO]
    if faltando:
        print(f"  classes abaixo de n_min: {', '.join(faltando)}")
        print("  (estrato que não atingir n_min sai INDETERMINADO por falta de"
              " dado, não por incerteza — são coisas diferentes no relatório)")

    print("\nA razão NÃO é calculada aqui, e os campos que a compõem"
          f" ({', '.join(_CAMPOS_PROIBIDOS)}) não são impressos.")
    print("Olhar N é a regra de parada. Olhar a razão invalidaria o critério"
          " congelado em 4289c9c.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
