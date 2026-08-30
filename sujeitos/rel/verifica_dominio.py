"""
verifica_dominio.py — pré-condição de armamento do REL-001.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR

O controle negativo do `§3.2` escolhe "documento de outro domínio". Esse domínio
vem de `cognitive_decisions`, extraído por LLM, e nunca foi validado. Pelo
NORTE §4.14, *"o LLM disse que são domínios diferentes"* não é verdade.

A errata do REL-001A não remove o LLM da cadeia — **valida a saída dele**. Este
script é essa validação, em dois passos:

    1. gerar   -> escreve os 77 itens num .jsonl para revisão humana
    2. congelar-> lê o revisado, MEDE a discordância, e emite o artefato

O passo 2 produz o número que o §4.14 pede: **quantos dos 77 o LLM errou**. Sem
esse número, trocar rótulo de modelo por rótulo humano seria só mudar de fé.

SEGURANÇA

O arquivo de revisão contém TEXTO DE CONVERSA REAL. Ele é `.jsonl`, e o
`.gitignore` nega essa classe por padrão desde 21/08 — `tests/test_higiene_de_
corpus.py` quebra o build se algum for versionado sem estar na allowlist.
Nenhum dos dois arquivos deste script deve entrar em commit.

USO
    python verifica_dominio.py gerar    --store <path> --saida revisao.jsonl
    # ... edite `dominio_humano` nas linhas em que o LLM errou ...
    python verifica_dominio.py congelar --revisao revisao.jsonl --saida congelado.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

EXPERIMENTO = "REL-001"

# §3.2 / errata do REL-001A: sem esta lista verificada e congelada, o REL-001
# nao dispara. O numero e o medido em 30/08 — muda com o corpus, e a divergencia
# e reportada em vez de aceita em silencio.
N_DOMINIOS_VERIFICADOS = 77

MAX_TRECHO = 400          # o revisor le trecho, nao o documento inteiro


def carrega_com_dominio(store: Path) -> list[dict]:
    """Documentos que TÊM domínio marcado — os únicos que podem servir de controle."""
    epi = json.loads((store / "episodic.json").read_text(encoding="utf-8"))
    out = []
    for e in epi:
        d = ((e.get("cognitive_decisions") or {}).get("domain") or "").strip()
        if not d:
            continue
        out.append({
            "id":            e.get("id"),
            "dominio_llm":   d,
            "dominio_humano": d,          # pré-preenchido: revisar é CORRIGIR
            "verificado":    False,
            "trecho":        (e.get("text") or "")[:MAX_TRECHO],
        })
    return out


def gerar(store: Path, saida: Path) -> dict:
    """
    Escreve os itens para revisão. RECUSA sobrescrever.

    Sobrescrever uma revisão em andamento apagaria trabalho humano sem aviso —
    e a segunda rodada nunca sai igual à primeira, então o dado perdido não
    volta.
    """
    if saida.exists():
        raise RuntimeError(
            f"{saida} já existe. Este script NÃO sobrescreve revisão: se ela "
            f"estiver em andamento, sobrescrever apaga trabalho humano e a "
            f"segunda rodada não reproduz a primeira. Mova ou renomeie."
        )
    itens = carrega_com_dominio(store)
    saida.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in itens),
                     encoding="utf-8")
    return {"n": len(itens), "esperado": N_DOMINIOS_VERIFICADOS,
            "divergiu_do_medido": len(itens) != N_DOMINIOS_VERIFICADOS,
            "saida": str(saida)}


def congelar(revisao: Path, saida: Path) -> dict:
    """
    Lê o revisado, MEDE a discordância, emite o artefato congelado.

    Exige `verificado: true` em TODOS. Item não revisado que passasse silencioso
    entraria no experimento como rótulo de LLM disfarçado de rótulo humano — que
    é exatamente o que esta pré-condição existe para impedir.
    """
    if saida.exists():
        raise RuntimeError(f"{saida} já existe — congelado não se reescreve (§4.4)")

    itens = [json.loads(l) for l in revisao.read_text(encoding="utf-8").splitlines() if l.strip()]
    pendentes = [i["id"] for i in itens if not i.get("verificado")]
    if pendentes:
        raise RuntimeError(
            f"{len(pendentes)} de {len(itens)} itens sem `verificado: true`. "
            f"Item não revisado entra como rótulo de LLM disfarçado de humano — "
            f"é o que esta pré-condição impede. Primeiros: "
            f"{[str(p)[:8] for p in pendentes[:5]]}"
        )

    discordou = [i for i in itens
                 if (i["dominio_humano"] or "").strip().lower()
                 != (i["dominio_llm"] or "").strip().lower()]

    congelado = {
        "experimento":   EXPERIMENTO,
        "n_itens":       len(itens),
        "n_discordou":   len(discordou),
        "taxa_erro_llm": round(len(discordou) / len(itens), 4) if itens else None,
        "correcoes":     [{"id": i["id"], "de": i["dominio_llm"], "para": i["dominio_humano"]}
                          for i in discordou],
        "dominios":      {i["id"]: i["dominio_humano"] for i in itens},
        "nao_diz":       ("mede quanto o rótulo do extrator divergiu DESTE revisor. "
                          "Concordância não é verdade (NORTE §4.14)."),
    }
    saida.write_text(json.dumps(congelado, ensure_ascii=False, indent=2), encoding="utf-8")
    return congelado


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=f"pré-condição de armamento do {EXPERIMENTO}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gerar");    g.add_argument("--store", required=True); g.add_argument("--saida", required=True)
    c = sub.add_parser("congelar"); c.add_argument("--revisao", required=True); c.add_argument("--saida", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "gerar":
        r = gerar(Path(a.store), Path(a.saida))
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if r["divergiu_do_medido"]:
            print(f"\nATENÇÃO: {r['n']} itens, mas N_DOMINIOS_VERIFICADOS = "
                  f"{N_DOMINIOS_VERIFICADOS}. O corpus mudou desde 30/08 — declare "
                  f"a data do snapshot no relatório.")
        print("\nAgora edite `dominio_humano` onde o LLM errou e marque "
              "`verificado: true` em TODAS as linhas.")
    else:
        r = congelar(Path(a.revisao), Path(a.saida))
        print(json.dumps({k: v for k, v in r.items() if k != "dominios"},
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
