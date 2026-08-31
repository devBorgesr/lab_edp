"""
rotula_humano.py — caminho A do REL-001. Retomável.

O QUE O JULGADOR VÊ

    QUERY
    DOCUMENTO

E nada mais. O `estrato` existe no arquivo de pares e **não é exibido** —
saber que um documento é do `controle` entregaria a resposta. Também não são
exibidos posição no ranking, score, nem qualquer rótulo do caminho B.

INDEPENDÊNCIA IMPOSTA, NÃO COMBINADA

`exige_independencia()` recusa rodar se o arquivo de saída do caminho B existir
no mesmo diretório. Não é para desconfiar de ninguém: é para que a garantia do
§7 seja propriedade do programa, e não da memória de quem executa às duas da
manhã.

RETOMÁVEL

Grava a cada julgamento. São 500 — ninguém faz de uma vez, e perder o trabalho
por fechar o terminal seria dano irreversível: a segunda passada nunca reproduz
a primeira.

ORDEM

Os pares vêm embaralhados com seed congelado. Julgar na ordem do arquivo
agruparia os 10 pares da mesma query em sequência, e o julgador começaria a
comparar documentos entre si em vez de julgar cada um contra a query.
"""
from __future__ import annotations

import json
import random
import textwrap
from pathlib import Path

import rel_001 as R

SEED = 20260830          # espelhado do §8
SAIDA_B = "rotulos_llm.json"     # o caminho B; a presença dele bloqueia este


def exige_independencia(diretorio: Path) -> None:
    """
    §7: os dois caminhos rotulam sem acesso um ao outro.

    Recusa rodar se o resultado do caminho B estiver ao lado. O julgador não
    precisa abrir o arquivo para ser influenciado — basta saber que ele está
    ali e que dá para conferir.
    """
    b = diretorio / SAIDA_B
    if b.exists():
        raise RuntimeError(
            f"{b} existe. O §7 exige independência: mova-o para fora deste "
            f"diretório antes de rotular. A garantia é do programa, não da "
            f"disciplina de quem executa."
        )


def _mostra(txt: str, larg: int = 78) -> str:
    return "\n".join("    " + l for l in
                     textwrap.wrap(" ".join((txt or "").split()), larg)[:14])


def rotula(pares_path: Path, saida: Path) -> dict:
    exige_independencia(saida.parent if saida.parent.name else Path("."))

    art = R.carrega_pares(pares_path)   # recusa INVALIDO e sem procedencia
    pares = art["pares"]

    feitos = {}
    if saida.exists():
        feitos = {r["par_id"]: r for r in
                  json.loads(saida.read_text(encoding="utf-8"))["rotulos"]}

    ordem = list(range(len(pares)))
    random.Random(SEED).shuffle(ordem)
    pend = [i for i in ordem if pares[i]["par_id"] not in feitos]

    print(f"\n{len(pend)} de {len(pares)} pendentes.")
    print("1 = RELEVANTE   0 = NAO_RELEVANTE   q = salva e sai")
    print("\nRELEVANTE: contribui materialmente para responder ESTA query.")
    print("Similaridade tematica NAO e relevancia. Sem informacao suficiente -> 0.\n")

    def grava():
        saida.write_text(json.dumps({
            "experimento":   art["experimento"],
            "caminho":       "A (humano)",
            "sha256_pares":  art["sha256_pares"],
            "n_rotulados":   len(feitos),
            "n_total":       len(pares),
            "rotulos":       list(feitos.values()),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    n = 0
    for i in pend:
        p = pares[i]
        print("─" * 80)
        print(f"[{len(feitos)+1}/{len(pares)}]")
        print("\n  QUERY:")
        print(_mostra(p["query"]))
        print("\n  DOCUMENTO:")
        print(_mostra(p["documento"]))
        try:
            r = input("\n  relevante? [1 / 0 / q] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            grava(); print(f"\ninterrompido — {n} gravados, retomavel."); break
        if r == "q":
            grava(); print(f"\n{n} gravados. Rode de novo para continuar."); break
        if r not in ("0", "1"):
            print("  (so 1 ou 0 — o §4 proibe escala e 'parcialmente')")
            continue
        feitos[p["par_id"]] = {"par_id": p["par_id"], "humano": int(r)}
        n += 1
        grava()
    else:
        print(f"\nCAMINHO A COMPLETO: {n} nesta sessao, {len(feitos)}/{len(pares)}.")

    rest = len(pares) - len(feitos)
    return {"rotulados_nesta_sessao": n, "pendentes": rest,
            "pronto_para_congelar": rest == 0}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="caminho A do REL-001 (humano)")
    ap.add_argument("--pares", default="pares_congelados.json")
    ap.add_argument("--saida", default="rotulos_humano.json")
    a = ap.parse_args(argv)
    print(json.dumps(rotula(Path(a.pares), Path(a.saida)),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
