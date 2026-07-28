#!/usr/bin/env python3
"""
sujeitos.edp.experimentos.e7_extrai_sequencia — E7, PASSO 1 do §4 apenas.

Espelha docs/preregistro_experimento_e7.md §4, LITERALMENTE. SÓ LEITURA:
abre e lê `episodic.json` com `open`/`json.load` puros — nunca instancia
MemoryStore, nunca chama retrieve, nunca escreve no store. Não mede
repeat_rate, não roda condições (`real`/`shuffled`/`aleatoria`) — isso é
passo separado (a rodada real é do pesquisador, contra a cópia).

A regra congelada (§4), aplicada nesta ordem:
    1. ordena por timestamp crescente
    2. exclui texto que começa com "[session_summary]"
    3. exclui quem não casa FORM_CHECK (`^\\s*Q:\\s*.+\\bA:\\s*`, DOTALL)
    4. query = trecho após "Q:" até o primeiro "A:"
    5. grava e7_sequencia.jsonl + imprime sha256 do arquivo

USO:
    EDP_BASE_DIR=/caminho/para/copia python3 -m \
        sujeitos.edp.experimentos.e7_extrai_sequencia [--out e7_sequencia.jsonl]

    Opcionais (defaults do §4/§8): EDP_SESSION_ID=default, EDP_SCOPE=cognitive.
    EDP_BASE_DIR DEVE apontar para uma CÓPIA (ex.: C:\\edp_data_fase0), nunca
    para a produção — mesma convenção de measure_ss_dominance.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# ── Constantes congeladas relevantes ao §4 (extração da sequência) ───────────
SCOPE = "cognitive"
PREFIXO_EXCLUIDO = "[session_summary]"
FORM_CHECK = re.compile(r"^\s*Q:\s*.+\bA:\s*", re.DOTALL)
MIN_TURNOS = 20


def _die(msg: str, code: int = 2) -> None:
    print(f"\n[ERRO] {msg}\n", file=sys.stderr)
    sys.exit(code)


def _resolve_episodic_path(base_dir: str, session_id: str, scope: str) -> Path:
    """$EDP_BASE_DIR/sessions/<session>_<scope>/episodic.json — mesma convenção
    de measure_ss_dominance.py e sujeitos/edp/adaptador.py._sessions_root()."""
    return Path(base_dir) / "sessions" / f"{session_id}_{scope}" / "episodic.json"


def _load_entries(path: Path) -> list:
    """open + json.load puros. Aceita lista OU {"entries": [...]}. Nunca
    instancia MemoryStore, nunca escreve — só leitura de disco."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("entries", [])
    return data if isinstance(data, list) else []


def extrai_query(texto: str) -> Optional[str]:
    """§4.4: a query é o trecho após 'Q:' até o primeiro 'A:'."""
    m = re.search(r"Q:\s*(.*?)\s*A:", texto, re.DOTALL)
    return m.group(1).strip() if m else None


def constroi_sequencia(entries: list) -> dict:
    """Aplica a regra congelada do §4 (passos 1-4) sobre `entries` (lista de
    dicts com pelo menos 'text'; 'id'/'timestamp' são carregados quando
    presentes, para rastreabilidade). Devolve contagens + sequência final."""
    n_total = len(entries)

    # 1) ordena por timestamp crescente
    ordenadas = sorted(entries, key=lambda e: e.get("timestamp", 0) or 0)

    # 2) exclui quem começa com "[session_summary]"
    n_excluido_summary = 0
    apos_summary = []
    for e in ordenadas:
        texto = e.get("text") or ""
        if texto.startswith(PREFIXO_EXCLUIDO):
            n_excluido_summary += 1
            continue
        apos_summary.append(e)

    # 3) exclui quem não casa o form-check Q:/A:; 4) extrai a query
    n_excluido_forma = 0
    sequencia = []
    for e in apos_summary:
        texto = e.get("text") or ""
        if not FORM_CHECK.match(texto):
            n_excluido_forma += 1
            continue
        query = extrai_query(texto)
        if query is None:
            n_excluido_forma += 1
            continue
        sequencia.append({
            "query": query,
            "id": e.get("id"),
            "timestamp": e.get("timestamp"),
        })

    return {
        "n_total": n_total,
        "n_excluido_summary": n_excluido_summary,
        "n_excluido_forma": n_excluido_forma,
        "n_final": len(sequencia),
        "sequencia": sequencia,
    }


def grava_jsonl(sequencia: list, path: Path) -> str:
    """5) grava e7_sequencia.jsonl (1 objeto por linha, ordem preservada) e
    devolve o sha256 do arquivo escrito."""
    with open(path, "w", encoding="utf-8") as f:
        for row in sequencia:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="E7 - Passo 1 do §4: extrator de sequência (SÓ LEITURA)."
    )
    p.add_argument("--out", default="e7_sequencia.jsonl",
                   help="caminho de saída do jsonl (default: ./e7_sequencia.jsonl)")
    args = p.parse_args(argv)

    base_dir = os.environ.get("EDP_BASE_DIR")
    if not base_dir:
        _die(
            "EDP_BASE_DIR não está setado. Aponte para a CÓPIA read-only "
            "(§4: ex. C:\\edp_data_fase0) — nunca para a produção."
        )
    session_id = os.environ.get("EDP_SESSION_ID", "default")
    scope = os.environ.get("EDP_SCOPE", SCOPE)

    ep_path = _resolve_episodic_path(base_dir, session_id, scope)
    if not ep_path.exists():
        _die(f"episodic.json não encontrado: {ep_path}")

    entries = _load_entries(ep_path)
    resultado = constroi_sequencia(entries)

    out_path = Path(args.out)
    sha = grava_jsonl(resultado["sequencia"], out_path)

    print(f"n_total            : {resultado['n_total']}")
    print(f"n_excluido_summary : {resultado['n_excluido_summary']}")
    print(f"n_excluido_forma   : {resultado['n_excluido_forma']}")
    print(f"n_final            : {resultado['n_final']}")
    print(f"sha256({out_path})  : {sha}")

    if resultado["n_final"] >= MIN_TURNOS:
        print(f"n >= {MIN_TURNOS}: PROSSEGUIR")
    else:
        print(f"n < {MIN_TURNOS}: PARAR (poder insuficiente, §4)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
