#!/usr/bin/env python3
"""
sujeitos.edp.experimentos.exp018 — HARNESS: promoção tóxica pelo caminho
automático. Implementa §5, §9 de docs/preregistro_experimento_018.md.

Pré-registro CONGELADO E COMMITADO — este harness não altera nenhuma régua
(condição, métrica, corte). Se a implementação tivesse revelado uma condição
impossível como escrita, o T1 (docs/RELATORIO_EXP018_T1.md) teria PARADO
antes deste arquivo existir — não parou (nenhum GATE disparou).

ANTI-MOCK (§10), NÃO-NEGOCIÁVEL: roda `consolidate()` e
`consolidate_promote_only()` REAIS, importadas de `edp.consolidation`, sobre
o `MemoryStore` REAL de uma sessão `__lab__` isolada (nunca reimplementa a
lógica de clustering/promoção).

A flag `EDP_WRITE_PROVENANCE` é lida por `edp/config.py` NO IMPORT — por
isso cada posição de flag exige um PROCESSO SEPARADO (§5; lição do exp017
Fase 0). `valida_flag()` aborta se a condição pedida não casar com a
posição do processo atual, antes de tocar `edp`.

USO:
    EDP_BASE_DIR=/caminho/para/copia python3 -m \
        sujeitos.edp.experimentos.exp018 --condicao C1
    EDP_WRITE_PROVENANCE=0 EDP_BASE_DIR=... python3 -m \
        sujeitos.edp.experimentos.exp018 --todas
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from sujeitos.edp.experimentos.exp018_dataset import CONDICOES, SCOPE, build_dataset

# ── §5: mapa condição -> posição de flag exigida e funções a rodar ──────────
FLAG_REQUERIDA = {"C1": 1, "C2": 0, "C3": 1, "C4": 0, "C5": 1, "C6": 1, "C7": 1}
FUNCOES_POR_CONDICAO = {
    "C1": ("consolidate",),
    "C2": ("consolidate",),
    "C3": ("consolidate_promote_only",),
    "C4": ("consolidate_promote_only",),
    "C5": ("consolidate", "consolidate_promote_only"),  # controle+: valida ambas
    "C6": ("consolidate", "consolidate_promote_only"),  # controle-: valida ambas
    "C7": ("consolidate",),  # promote_only nunca funde (§3 item 8) — não decisiva aqui
}


def _die(msg: str, code: int = 2) -> None:
    print(f"\n[ERRO] {msg}\n", file=sys.stderr)
    sys.exit(code)


def posicao_flag_atual() -> int:
    """Mesmo parsing que `edp/config.py` faz no import
    (`os.environ.get("EDP_WRITE_PROVENANCE","1")=="1"`), lido aqui direto do
    ambiente para reportar a posição ANTES de qualquer import de `edp`."""
    return 1 if os.environ.get("EDP_WRITE_PROVENANCE", "1") == "1" else 0


def condicoes_para_posicao(pos: int) -> tuple:
    """§5, `--todas`: as condições que compartilham a posição de flag do
    processo atual."""
    return tuple(c for c in CONDICOES if FLAG_REQUERIDA[c] == pos)


def valida_flag(condicao: str, posicao_atual: int) -> None:
    """Aborta se a condição pedida não casar com a flag do processo atual —
    impede rodar C3 com a flag OFF e reportar H2 errado (§5)."""
    esperado = FLAG_REQUERIDA[condicao]
    if posicao_atual != esperado:
        _die(
            f"condição {condicao} exige EDP_WRITE_PROVENANCE={esperado}, mas o "
            f"processo atual está com EDP_WRITE_PROVENANCE={posicao_atual}. "
            f"Rode num processo separado com a posição correta — a flag é lida "
            f"no import de config.py, alternância in-process mede a mesma "
            f"condição duas vezes (lição do exp017 Fase 0)."
        )


# ── §9: métricas puras sobre o que sobrou em memory.semantic/.episodic ──────

def inspeciona_resultado(condicao: str, dataset: list, semantic_entries: list,
                          episodic_entries: Optional[list] = None) -> dict:
    """Não toca `edp` — só dicts. `dataset` é o que foi plantado (para saber
    quais ids/classes procurar); `semantic_entries`/`episodic_entries` são o
    que sobrou depois da chamada real. Testável em isolamento (T5).

    C7 precisa dos DOIS: "a fusão ocorreu" (§5) é um fato do EPISÓDICO
    (`consolidate()` escreve `new_entries` — merged ou passthrough — de volta
    em `memory.episodic`, com `merged_from` no dict merged, independente de
    promoção); "foi promovida" é um fato do SEMÂNTICO. Conflar os dois (só
    olhar semantic) tornaria "fundiu" indistinguível de "fundiu E promoveu" —
    e o H0 do §6 (C7 promover 0) exige poder representar justamente o caso em
    que fundiu mas não promoveu."""
    ids_plantados = {e["id"]: e.get("answer_class") for e in dataset}
    promovidas_por_classe = {"not_found": 0, "disqualification": 0, "normal": 0}
    promovidas_ids = []
    for se in semantic_entries:
        sid = se.get("id")
        if sid in ids_plantados:
            promovidas_ids.append(sid)
            classe = ids_plantados[sid] or "normal"
            promovidas_por_classe[classe] = promovidas_por_classe.get(classe, 0) + 1

    resultado = {
        "condicao": condicao,
        "promovidas_total": len(promovidas_ids),
        "promovidas_por_classe": promovidas_por_classe,
        "n_semantic_apos": len(semantic_entries),
    }
    if condicao == "C7":
        # C7 funde -> a entry resultante tem id NOVO (merge_cluster gera
        # uuid4 novo, consolidation.py:143) — não está em ids_plantados.
        fundidas = [e for e in (episodic_entries or []) if e.get("merged_from") == 2]
        resultado["fundiu"] = bool(fundidas)
        resultado["merged_from"] = fundidas[0].get("merged_from") if fundidas else None
        fused_id = fundidas[0].get("id") if fundidas else None
        promovida = next((se for se in semantic_entries if se.get("id") == fused_id), None) if fused_id else None
        resultado["promovida_fundida"] = promovida is not None
        resultado["answer_class_presente"] = ("answer_class" in promovida) if promovida else None
    return resultado


# ── execução real (só a partir daqui toca `edp`) ─────────────────────────────

def _roda_condicao_funcao(sujeito, condicao: str, funcao: str) -> dict:
    from bancada.isolamento import experimental_session, verify_no_leak
    from edp.consolidation import consolidate, consolidate_promote_only
    from edp.runtime.registry import get_memory

    dataset = build_dataset(condicao)
    fp_before = sujeito.fingerprint_producao()

    with experimental_session(sujeito, purge=True) as session_id:
        sujeito.carregar_snapshot(session_id, dataset)
        memory = get_memory(session_id)
        if funcao == "consolidate":
            consolidate(memory)
        else:
            consolidate_promote_only(memory)
        semantic_entries = [dict(e) for e in memory.semantic.entries]
        episodic_entries = [dict(e) for e in memory.episodic.entries]

    fp_after = sujeito.fingerprint_producao()
    leak_ok = verify_no_leak(fp_before, fp_after)

    resultado = inspeciona_resultado(condicao, dataset, semantic_entries, episodic_entries)
    resultado["funcao"] = funcao
    resultado["leak_ok"] = leak_ok
    return resultado


def _formata_linha(chave: str, r: dict) -> str:
    linha = (
        f"{chave:<32} promovidas={r['promovidas_total']} "
        f"por_classe={r['promovidas_por_classe']} leak_ok={r['leak_ok']}"
    )
    if r["condicao"] == "C7":
        linha += (
            f" fundiu={r.get('fundiu')} merged_from={r.get('merged_from')} "
            f"promovida_fundida={r.get('promovida_fundida')} "
            f"answer_class_presente={r.get('answer_class_presente')}"
        )
    return linha


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="exp018 - Harness: promoção tóxica pelo caminho automático (§5, §9)."
    )
    grupo = p.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--condicao", choices=CONDICOES, help="roda uma condição (C1..C7)")
    grupo.add_argument("--todas", action="store_true",
                        help="roda as condições que casam a posição de flag do processo atual")
    p.add_argument("--out", default="exp018_resultados.json",
                    help="JSON acumulável dos resultados (§9)")
    args = p.parse_args(argv)

    posicao = posicao_flag_atual()
    print(f"EDP_WRITE_PROVENANCE (posição lida) : {posicao}")

    if args.condicao:
        valida_flag(args.condicao, posicao)
        condicoes = [args.condicao]
    else:
        condicoes = list(condicoes_para_posicao(posicao))
        print(f"--todas: condições desta posição de flag: {condicoes}")

    from sujeitos.edp.adaptador import SujeitoEDP
    sujeito = SujeitoEDP(prod_session=os.environ.get("EDP_SESSION_ID", "default"), scope=SCOPE)

    novos = {}
    for condicao in condicoes:
        for funcao in FUNCOES_POR_CONDICAO[condicao]:
            resultado = _roda_condicao_funcao(sujeito, condicao, funcao)
            if not resultado["leak_ok"]:
                # §9: gate de reporte — nenhum resultado (nem os já bem-sucedidos
                # nesta invocação) é impresso ou gravado.
                raise RuntimeError(
                    f"VAZAMENTO DETECTADO (INV-5) em {condicao}/{funcao}: fingerprint "
                    f"da produção mudou entre antes/depois. Nenhum resultado é reportado."
                )
            novos[f"{condicao}/{funcao}"] = resultado

    # acumula no JSON — o harness roda em processos separados por posição de
    # flag; é assim que as duas posições se juntam num veredito só.
    out_path = Path(args.out)
    acumulado = {}
    if out_path.exists():
        acumulado = json.loads(out_path.read_text(encoding="utf-8"))
    acumulado.update(novos)
    out_path.write_text(json.dumps(acumulado, ensure_ascii=False, indent=2), encoding="utf-8")

    for chave, r in novos.items():
        print(_formata_linha(chave, r))
    print(f"\nresultados acumulados em: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
