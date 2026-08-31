"""
smoke_rel_001.py — teste de INFRAESTRUTURA do REL-001 (item 3 das instrucoes).

O QUE ELE VERIFICA

    query congelada -> monta_pool -> 5 topo / 3 cauda / 2 controle
                    -> embaralhamento -> system prompt -> user prompt
                    -> chamada ao modelo -> parse -> classificacao de falha

Conectividade, formato e parsing. Nada mais.

O QUE ELE NAO FAZ, E O CODIGO IMPEDE

**Nenhum rotulo do smoke entra no REL-001.** A saida e gravada com a chave
`ROTULOS_DESCARTADOS` e sem o campo `relevant` por par — so o modo de falha e a
latencia. Nao ha caminho por onde um julgamento do smoke vire dado do
experimento, e isso e propriedade do arquivo, nao promessa.

Nao analisa concordancia. Nao ajusta prompt, temperatura, query nem documento.
Se falhar, classifica pela taxonomia do §11 e para — workaround silencioso e
mudanca experimental nao declarada.

E PARA depois. A coleta principal exige confirmacao explicita do pesquisador
(item 5).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import juiz_llm as J          # noqa: E402
import rel_001 as R           # noqa: E402

N_SMOKE = 3                   # pares. Suficiente para conectividade+formato+parse.


def _chama(cfg: dict, sysp: str, userp: str) -> tuple[str, str | None, float]:
    """(texto, erro, latencia_s). Nao trata excecao em silencio."""
    t0 = time.time()
    try:
        from anthropic import Anthropic
        cli = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        r = cli.messages.create(
            model=cfg["modelo"], max_tokens=32,
            temperature=cfg["temperatura"], system=sysp,
            messages=[{"role": "user", "content": userp}],
        )
        txt = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return txt, None, time.time() - t0
    except Exception as e:
        return "", f"{type(e).__name__}: {e}", time.time() - t0


def roda(config: Path, amostra: Path, dominios: Path, store: Path) -> dict:
    cfg = json.loads(config.read_text(encoding="utf-8"))
    am  = json.loads(amostra.read_text(encoding="utf-8"))
    dom = json.loads(dominios.read_text(encoding="utf-8"))["dominios"]

    # texto dos documentos, do snapshot congelado
    epi = json.loads((store / "episodic.json").read_text(encoding="utf-8"))
    txt_de = {e.get("id"): (e.get("text") or "") for e in epi}

    # SO as 3 primeiras queries do conjunto congelado — ordem estavel por hash
    registros, falhas = [], []
    # ERRATA 31/08 (invalidacao 01): esta linha era
    #     ranking = [i for i in txt_de if i != q["id_turno"]]
    # ou seja, ORDEM DE INSERCAO DO ARQUIVO passando por ranking — o mesmo
    # defeito do congela_pares.py. A coluna `estrato` do REL-001_SMOKE.md foi
    # produzida assim e NAO significa nada; conectividade, formato, parse e
    # latencia daquele smoke continuam validos.
    import congela_pares as C
    retr = C.abre_retriever(store)
    for q in am["queries"][:N_SMOKE]:
        res = retr.retrieve(q["query"], top_k=50, min_score=0.0)
        ranking = [(r.get("id"), r.get("ranking_score"))
                   for r in res if r.get("id") != q["id_turno"]]
        ctrl = R.corpus_de_outro_dominio(dom, q["dominio"])
        pool = R.monta_pool(q["query"], ranking, ctrl)

        p = pool[0]                       # UM par por query: e smoke, nao coleta
        userp = J.monta_user_prompt(q["query"], txt_de.get(p["doc"], "")[:1500])
        texto, erro, lat = _chama(cfg, cfg["system_prompt"], userp)
        modo = J.classifica_falha(texto, erro)
        falhas.append(modo)
        registros.append({
            "query_sha":  q["sha256_query"][:12],
            "estrato":    p["estrato"],
            "latencia_s": round(lat, 2),
            "modo_falha": modo,
            "formato_ok": modo is None,
            # NENHUM rotulo aqui, de proposito (item 4)
        })

    return {
        "experimento":  "REL-001",
        "tipo":         "SMOKE DE INFRAESTRUTURA",
        "modelo":       cfg["modelo"],
        "sha256_system": cfg["sha256_system"],
        "n_pares":      len(registros),
        "pares":        registros,
        "falhas":       J.veredito_de_falhas(falhas),
        "ROTULOS_DESCARTADOS": ("nenhum julgamento deste smoke entra no REL-001 "
                                "(item 3). O campo `relevant` nao e gravado."),
        "proximo_passo": ("PARAR. A coleta principal exige confirmacao explicita "
                          "do pesquisador (item 5)."),
    }


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="smoke de infraestrutura do REL-001")
    ap.add_argument("--config",   default="docs/rel/REL-001_CONFIG_CONGELADA.json")
    ap.add_argument("--amostra",  default="amostra_congelada.json")
    ap.add_argument("--dominios", default="dominio_congelado_v2.json")
    ap.add_argument("--store",    required=True)
    a = ap.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY ausente no ambiente.")
    r = roda(Path(a.config), Path(a.amostra), Path(a.dominios), Path(a.store))
    print(json.dumps(r, ensure_ascii=False, indent=2))
    print("\n" + "=" * 68)
    print("SMOKE CONCLUIDO. Nada aqui entra no REL-001.")
    print("A coleta principal NAO comeca sozinha (item 5).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
