"""
congela_pares.py — materializa os 500 pares UMA vez, para os dois caminhos.

POR QUE ISTO EXISTE

O §7 exige que A e B julguem **exatamente os mesmos** 500 pares. Se cada caminho
montasse o pool por conta, uma diferença de seed, de ordem ou de versão do
artefato produziria conjuntos distintos — e o κ compararia julgamentos sobre
coisas diferentes, sem que nada acusasse.

Aqui o pool é montado uma vez, congelado com hash, e os dois caminhos passam a
CONSUMIR o mesmo arquivo.

O ESTRATO FICA NO ARQUIVO, MAS NÃO NA TELA

Cada par carrega seu estrato — a análise precisa dele, o gate roda só no `topo`.
Mas o julgador **não pode vê-lo**: saber que um documento é do estrato
`controle` entregaria a resposta. `rotula_humano.py` não exibe o campo, e o
prompt do juiz também não o recebe.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import rel_001 as R

EXPERIMENTO = "REL-001"
TOP_K_RANKING = 50          # §3.2: a cauda sai das posicoes 20-50


def abre_retriever(store: Path):
    """
    O MemoryStore real, apontado para o snapshot.

    ERRATA 31/08: a primeira versao deste arquivo NAO usava retriever. Passava
    `[i for i in txt]` como `ranking` — todos os documentos em ordem de
    INSERCAO. Consequencia: o estrato `topo` eram os 5 primeiros do arquivo,
    IGUAIS para as 50 queries, e nenhum deles era top-5 de coisa nenhuma.

    Os 500 pares congelados em 07:22 e os 492 rotulos coletados sobre eles sao
    INVALIDOS. Ver docs/rel/REL-001_INVALIDACAO_01.md.

    O retriever ja tinha sido rodado de verdade na viabilidade (28cc991,
    "50/50 queries devolvem 50 candidatos"). O erro nao foi nao saber como; foi
    nao ligar, e o smoke conferir formato sem perguntar se o topo era o topo.
    """
    import os, sys
    os.environ["EDP_BASE_DIR"] = str(store.parent.parent)
    import edp.config as cfg
    cfg.BASE_DIR = store.parent.parent
    cfg.MEMORY_DIR = store.parent
    import edp.memory as mm, edp.memory.store as sm, edp.memory.semantic as sem
    mm.MEMORY_DIR = sm.MEMORY_DIR = sem.MEMORY_DIR = store.parent
    return mm.MemoryStore("default")


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def congela(amostra: Path, dominios: Path, store: Path, saida: Path) -> dict:
    if saida.exists():
        raise RuntimeError(
            f"{saida} já existe. Os pares não se reescrevem: remontá-los depois "
            f"do início da coleta trocaria o objeto sob os rótulos já dados."
        )
    am  = json.loads(amostra.read_text(encoding="utf-8"))
    dom = json.loads(dominios.read_text(encoding="utf-8"))["dominios"]
    epi = json.loads((store / "episodic.json").read_text(encoding="utf-8"))
    txt = {e.get("id"): (e.get("text") or "") for e in epi}

    retr = abre_retriever(store)
    pares = []
    for q in am["queries"]:
        # RANKING REAL do retriever, nao ordem de arquivo (errata 31/08)
        res = retr.retrieve(q["query"], top_k=TOP_K_RANKING, min_score=0.0)
        ranking = [r.get("id") for r in res if r.get("id") != q["id_turno"]]
        ctrl = R.corpus_de_outro_dominio(dom, q["dominio"])
        for p in R.monta_pool(q["query"], ranking, ctrl):
            pares.append({
                "par_id":     _sha(f"{q['sha256_query']}:{p['doc']}")[:16],
                "query_sha":  q["sha256_query"],
                "query":      q["query"],
                "doc_id":     p["doc"],
                "documento":  txt.get(p["doc"], ""),
                "estrato":    p["estrato"],     # NÃO exibido ao julgador
            })

    esperado = len(am["queries"]) * R.N_DOCS_POR_QUERY
    if len(pares) != esperado:
        raise RuntimeError(f"{len(pares)} pares, esperado {esperado}")

    art = {
        "experimento":     EXPERIMENTO,
        "congelado_em":    datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_pares":         len(pares),
        "n_queries":       len(am["queries"]),
        "sha256_amostra":  _sha(amostra.read_text(encoding="utf-8")),
        "sha256_pares":    _sha(json.dumps([p["par_id"] for p in pares], sort_keys=True)),
        "ranking":         f"retriever real, top_k={TOP_K_RANKING}, min_score=0.0",
        "por_estrato":     {e: sum(1 for p in pares if p["estrato"] == e)
                            for e in R.ESTRATOS},
        "pares":           pares,
        "aviso": ("o campo `estrato` NAO pode ser exibido ao julgador — saber que "
                  "um documento e do controle entregaria a resposta."),
    }
    saida.write_text(json.dumps(art, ensure_ascii=False, indent=2), encoding="utf-8")
    return art


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="congela os 500 pares do REL-001")
    ap.add_argument("--amostra",  default="amostra_congelada.json")
    ap.add_argument("--dominios", default="dominio_congelado_v2.json")
    ap.add_argument("--store",    required=True)
    ap.add_argument("--saida",    default="pares_congelados.json")
    a = ap.parse_args(argv)
    art = congela(Path(a.amostra), Path(a.dominios), Path(a.store), Path(a.saida))
    print(json.dumps({k: v for k, v in art.items() if k != "pares"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
