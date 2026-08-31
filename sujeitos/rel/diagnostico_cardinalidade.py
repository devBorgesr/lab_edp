"""
diagnostico_cardinalidade.py — por que o corpus nao entrega 50 distintos.

NAO E O EXPERIMENTO. Nao produz kappa, nem rotulo, nem ground truth. Mede a
CARDINALIDADE do que o retriever real devolve para as 50 queries congeladas, e
separa as causas possiveis em vez de assumir uma.

O objetivo (item 4 do auditor) e CARACTERIZAR A LIMITACAO — nao encontrar uma
query que passe. Por isso o relatorio traz as 50 linhas, nao um resumo.

AS TRES CAUSAS, MEDIDAS SEPARADAMENTE (item 6)

    duplicacao de armazenamento  o mesmo id em episodic E semantic
    limitacao do retriever       top_k pede menos do que precisaria
    limitacao do corpus          nao ha documentos distintos suficientes

Nenhuma e concluida antes de medir. As tres sao contadas no mesmo passe.
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter
from pathlib import Path

TOP_K = 50


def abre(store: Path):
    import os
    os.environ["EDP_BASE_DIR"] = str(store.parent.parent)
    import edp.config as cfg
    cfg.BASE_DIR = store.parent.parent
    cfg.MEMORY_DIR = store.parent
    import edp.memory as mm, edp.memory.store as sm, edp.memory.semantic as sem
    mm.MEMORY_DIR = sm.MEMORY_DIR = sem.MEMORY_DIR = store.parent
    return mm.MemoryStore("default")


def anatomia_do_indice(store_dir: Path, retr) -> dict:
    """Onde cada documento se perde, do arquivo ate o indice hibrido."""
    epi = json.loads((store_dir / "episodic.json").read_text(encoding="utf-8"))
    sem_p = store_dir / "semantic.json"
    sem = json.loads(sem_p.read_text(encoding="utf-8")) if sem_p.exists() else []
    if isinstance(sem, dict):
        sem = sem.get("entries", sem.get("facts", []))

    def ids(pool):
        return [e.get("id") for e in pool if isinstance(e, dict) and e.get("id")]

    ids_epi, ids_sem = ids(epi), ids(sem)
    inter = set(ids_epi) & set(ids_sem)

    idx = retr._hybrid_index()
    kept = idx["entries"] if idx else []
    ids_kept = [e.get("id") for e in kept]
    txt_kept = [(e.get("text") or "").strip() for e in kept]

    # Motivos de exclusao, na MESMA ordem e com os MESMOS filtros do
    # _hybrid_index. Reproduzir a lista pela metade deixaria um residuo sem
    # explicacao — e um numero que nao fecha nao vira tabela.
    from edp.config import EDP_TOXIC_GUARDS, TOXIC_ANSWER_CLASSES
    try:
        from edp.echo_chamber import detectar_auto_sinal_de_limite as _recusa
    except Exception:
        _recusa = None

    motivos = Counter()
    for layer, pool in (("episodic", epi), ("semantic", sem)):
        for e in pool:
            if not isinstance(e, dict):
                motivos["nao_e_dict"] += 1
            elif not e.get("id"):
                motivos["sem_id"] += 1
            elif not (e.get("text") or "").strip():
                motivos["sem_texto"] += 1
            elif e.get("embedding") is None:
                motivos["sem_embedding"] += 1
            elif e.get("epistemic_status") in ("contradicted", "quarantined"):
                motivos[f"governanca_{e.get('epistemic_status')}"] += 1
            elif EDP_TOXIC_GUARDS and e.get("answer_class") in TOXIC_ANSWER_CLASSES:
                motivos[f"toxico_{e.get('answer_class')}"] += 1
            elif _recusa is not None and (
                    _recusa(e.get("text", "") or "").get("confianca") == "alta"):
                motivos["filtro_recusa"] += 1

    excluidas = (len(epi) + len(sem)) - len(kept)
    if sum(motivos.values()) != excluidas:
        raise RuntimeError(
            f"{excluidas} entradas ficaram fora do indice, mas os motivos "
            f"somam {sum(motivos.values())}. Ha um filtro nao reproduzido "
            f"aqui — a tabela nao sai com residuo inexplicado."
        )

    return {
        "_epi_sem": inter,
        "arquivo": {
            "episodic_entradas":  len(epi),
            "semantic_entradas":  len(sem),
            "episodic_ids_unicos": len(set(ids_epi)),
            "semantic_ids_unicos": len(set(ids_sem)),
            "ids_em_AMBAS_camadas": len(inter),
            "UNIAO_ids_distintos": len(set(ids_epi) | set(ids_sem)),
        },
        "indice_hibrido": {
            "entradas_no_indice":  len(kept),
            "ids_DISTINTOS":       len(set(ids_kept)),
            "textos_DISTINTOS":    len(set(txt_kept)),
            "entradas_duplicadas_por_id": len(kept) - len(set(ids_kept)),
            "excluidas_por_motivo": dict(motivos),
        },
        "retriever": {
            # k = min(top_k*3, len(texts)) em retrieval_hybrid.search
            "top_k_pedido":        TOP_K,
            "candidatos_varridos": min(TOP_K * 3, len(kept)),
            "corpus_do_indice":    len(kept),
            "pede_menos_que_tem":  min(TOP_K * 3, len(kept)) < len(kept),
        },
    }


def por_query(amostra: Path, retr, epi_sem: set[str]) -> list[dict]:
    """
    `epi_sem`: ids presentes nas DUAS camadas. Serve para responder a pergunta
    do item 6 — a duplicacao do ranking e EXATAMENTE a promocao epi->sem, ou
    existe outra fonte? Sem isso a causa seria suposta, nao medida.
    """
    am = json.loads(amostra.read_text(encoding="utf-8"))
    linhas = []
    for q in am["queries"]:
        res = retr.retrieve(q["query"], top_k=TOP_K, min_score=0.0)
        brutos = [r.get("id") for r in res]
        # o proprio turno sai: e a query, nao um candidato
        rank = [i for i in brutos if i != q["id_turno"]]
        vistos, distintos = set(), []
        for i in rank:
            if i not in vistos:
                vistos.add(i); distintos.append(i)
        txt = [(r.get("text") or "").strip() for r in res if r.get("id") != q["id_turno"]]
        # dos ids que aparecem repetidos, quantos sao da intersecao epi/sem
        rep = {i for i, n in Counter(rank).items() if n > 1}
        dup_explicada = len(rep & epi_sem)
        linhas.append({
            "query_sha":        q["sha256_query"][:10],
            "n_bruto":          len(brutos),
            "n_apos_tirar_turno": len(rank),
            "n_ids_distintos":  len(distintos),
            "ids_duplicados":   len(rank) - len(distintos),
            "textos_distintos": len(set(txt)),
            "pos_maxima":       len(brutos) - 1,
            "ids_repetidos":       len(rep),
            "repetidos_epi_e_sem": dup_explicada,
            "repetidos_SEM_causa": len(rep) - dup_explicada,
            "atende_50":        len(distintos) >= 50,
        })
    return linhas


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="cardinalidade real do retriever (REL-001)")
    ap.add_argument("--store",   required=True)
    ap.add_argument("--amostra", default="amostra_congelada.json")
    ap.add_argument("--saida",   default="diagnostico_cardinalidade.json")
    a = ap.parse_args(argv)

    store = Path(a.store)
    retr  = abre(store)
    anat  = anatomia_do_indice(store, retr)
    linhas = por_query(Path(a.amostra), retr, anat.pop("_epi_sem"))

    d = [l["n_ids_distintos"] for l in linhas]
    resumo = {
        "n_queries":       len(linhas),
        "distintos_min":   min(d), "distintos_max": max(d),
        "distintos_mediana": st.median(d),
        "queries_com_50_ou_mais": sum(1 for l in linhas if l["atende_50"]),
        "queries_REPROVADAS":     sum(1 for l in linhas if not l["atende_50"]),
    }
    art = {"experimento": "REL-001", "tipo": "DIAGNOSTICO DE CARDINALIDADE",
           "NAO_E_RESULTADO": ("nenhum kappa, rotulo ou ground truth. Mede "
                               "cardinalidade do retriever, nada mais."),
           "anatomia": anat, "resumo": resumo, "por_query": linhas}
    Path(a.saida).write_text(json.dumps(art, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    print(json.dumps(anat, ensure_ascii=False, indent=2))
    print("\n" + "=" * 74)
    print(f"{'query':<12}{'bruto':>7}{'-turno':>8}{'distintos':>11}"
          f"{'dup':>6}{'txt_dist':>10}{'50?':>6}")
    print("-" * 74)
    for l in linhas:
        print(f"{l['query_sha']:<12}{l['n_bruto']:>7}{l['n_apos_tirar_turno']:>8}"
              f"{l['n_ids_distintos']:>11}{l['ids_duplicados']:>6}"
              f"{l['textos_distintos']:>10}{'sim' if l['atende_50'] else 'NAO':>6}")
    print("-" * 74)
    sc = sum(l["repetidos_SEM_causa"] for l in linhas)
    print(f"ids repetidos explicados pela promocao epi->sem: "
          f"{sum(l['repetidos_epi_e_sem'] for l in linhas)}; SEM essa causa: {sc}")
    print("-" * 74)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
