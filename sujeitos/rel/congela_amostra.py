"""
congela_amostra.py — congela as 50 queries e o snapshot (REL-001 §6 e §7 das
instrucoes de coleta).

O QUE ISTO FECHA

O `§8` do pre-registro fixa `N_QUERIES = 50`, mas **nao diz como escolher as 50**
entre as elegiveis. Lacuna real, fechada aqui ANTES de qualquer rotulo, com a
escolha neutra: amostragem aleatoria deterministica pelo `SEED` ja congelado.

Neutra porque nao seleciona por facilidade, por tema, nem por qualquer coisa
correlacionada com o desfecho — e e reproduzivel por quem auditar.

Isto e ACRESCIMO ao protocolo, nao interpretacao dele. Fica declarado no proprio
artefato, e nao como se ja estivesse la.

ELEGIBILIDADE

So entram queries cujo turno tem dominio VERIFICADO (o congelado v2). Sem
dominio, nao ha como montar o estrato `controle` — e adivinhar reintroduziria o
rotulo nao-validado que a pre-condicao eliminou.

Queries marcadas `SEM_TEMA` **podem** ser sorteadas: elas sao invalidas como
CONTROLE, nao como query. O que se pergunta e se o documento e relevante para
ela, e "oi" e uma query real que o sistema recebeu.

RASTREABILIDADE

O artefato carrega hash do texto de cada query, hash do conjunto, hash do corpus
e o id do snapshot. Um resultado do REL-001 pode ser amarrado exatamente ao
estado que o produziu.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENTO = "REL-001"
N_QUERIES   = 50            # espelhado do §8
SEED        = 20260830      # espelhado do §8

FONTES_DE_PERGUNTA = ("llm_response", "camara_response")


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _normaliza(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().casefold())


def _pergunta(entry: dict) -> str | None:
    if (entry or {}).get("source_type") not in FONTES_DE_PERGUNTA:
        return None
    m = re.match(r"\s*Q:\s*(.+?)(?:\n\s*A:|\Z)", entry.get("text") or "", re.S)
    return m.group(1).strip() if m else None


def elegiveis(store: Path, dominios: dict) -> list[dict]:
    """
    Queries com dominio verificado, deduplicadas por texto normalizado.

    A dedup importa: as 9 copias de "oi" sao a MESMA query. Sortear entre elas
    daria peso 9x a um texto — e o §5 pede bootstrap por query justamente
    porque query e a unidade.
    """
    epi = json.loads((store / "episodic.json").read_text(encoding="utf-8"))
    vistos, out = set(), []
    for e in epi:
        q = _pergunta(e)
        if not q:
            continue
        eid = e.get("id")
        if eid not in dominios:          # sem dominio verificado
            continue
        k = _normaliza(q)
        if k in vistos:
            continue
        vistos.add(k)
        out.append({
            "id_turno":    eid,
            "query":       q,
            "sha256_query": _sha(q),
            "dominio":     dominios[eid],
            "origem":      f"{store.parent.parent.name}/{e.get('source_type')}",
        })
    return out


def congela(store: Path, congelado_dominios: Path, saida: Path,
            n: int = N_QUERIES, seed: int = SEED) -> dict:
    """
    Sorteia as N queries e emite o artefato. RECUSA sobrescrever.

    Sobrescrever um conjunto congelado depois de a coleta comecar permitiria
    trocar query que "deu problema" — e o §6 das instrucoes proibe substituicao
    silenciosa.
    """
    if saida.exists():
        raise RuntimeError(
            f"{saida} ja existe. Conjunto congelado nao se reescreve: trocar "
            f"query depois do inicio permitiria substituir a que 'deu problema'. "
            f"Query invalida se REGISTRA como invalidacao (§6)."
        )

    dom = json.loads(congelado_dominios.read_text(encoding="utf-8"))
    pool = elegiveis(store, dom["dominios"])
    if len(pool) < n:
        raise RuntimeError(
            f"so {len(pool)} queries elegiveis para N_QUERIES={n}. Reduzir o N "
            f"em silencio falsearia o poder do §6 — declare a insuficiencia."
        )

    escolhidas = random.Random(seed).sample(pool, n)
    escolhidas.sort(key=lambda x: x["sha256_query"])      # ordem estavel no artefato

    corpo = json.dumps([q["sha256_query"] for q in escolhidas], sort_keys=True)
    epi_txt = (store / "episodic.json").read_text(encoding="utf-8")

    art = {
        "experimento":       EXPERIMENTO,
        "congelado_em":      datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot": {
            "store":             str(store),
            "sha256_episodic":   _sha(epi_txt),
            "n_documentos":      len(json.loads(epi_txt)),
            "sha256_dominios":   _sha(congelado_dominios.read_text(encoding="utf-8")),
        },
        "amostragem": {
            "metodo":     "aleatoria simples, sem reposicao",
            "seed":       seed,
            "n_elegivel": len(pool),
            "n_sorteado": n,
            "nota": ("o §8 fixa N_QUERIES mas nao fixava COMO escolher. Metodo "
                     "acrescentado em 31/08, antes de qualquer rotulo, com a "
                     "escolha neutra — nao seleciona por facilidade nem por tema."),
        },
        "sha256_conjunto":   _sha(corpo),
        "queries":           escolhidas,
        "nao_diz": ("congelar a amostra nao valida nada. Amarra o resultado ao "
                    "estado exato que o produziu."),
    }
    saida.write_text(json.dumps(art, ensure_ascii=False, indent=2), encoding="utf-8")
    return art


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=f"congela a amostra do {EXPERIMENTO}")
    ap.add_argument("--store", required=True)
    ap.add_argument("--dominios", required=True)
    ap.add_argument("--saida", required=True)
    a = ap.parse_args(argv)
    art = congela(Path(a.store), Path(a.dominios), Path(a.saida))
    print(json.dumps({k: v for k, v in art.items() if k != "queries"},
                     ensure_ascii=False, indent=2))
    print(f"\n{len(art['queries'])} queries congeladas em {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
