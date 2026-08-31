"""
coleta_llm.py — caminho B do REL-001. Retomável.

O QUE REGISTRA, POR PAR

    par_id · resposta bruta · resultado parseado · modo de falha · latência

A resposta bruta fica: ela é o JSON curto do juiz, e sem ela não há como auditar
depois se o parser errou ou se o modelo respondeu torto.

O QUE NÃO FAZ

**Nenhum retry.** Timeout e erro de API são registrados como o que são. Um retry
silencioso mudaria o protocolo no meio — a autorização diz que qualquer chamada
adicional exige registro prévio, e "tentar de novo até dar certo" transforma a
taxa de falha do juiz em zero por construção.

**Nenhum `0` por falha.** `resultado` fica `null` quando o par é inclassificável,
e `veredito_de_falhas()` aplica o piso de 10% do §11 sobre a rodada inteira.

**Não lê o caminho A.** `exige_independencia()` recusa rodar com os rótulos
humanos ao lado, pelo mesmo motivo que o inverso.

RETOMÁVEL

Grava a cada chamada. São 500; uma queda de rede na 380ª não pode custar as 379
anteriores.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import juiz_llm as J
import rel_001 as R

SAIDA_A = "rotulos_humano.json"


def exige_independencia(diretorio: Path) -> None:
    """§7, o espelho do que `rotula_humano` impõe ao caminho A."""
    a = diretorio / SAIDA_A
    if a.exists():
        raise RuntimeError(
            f"{a} existe. O §7 exige independência: mova-o para fora deste "
            f"diretório antes de rodar o caminho B."
        )


def _chama(cfg: dict, userp: str):
    t0 = time.time()
    try:
        from anthropic import Anthropic
        cli = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        r = cli.messages.create(
            model=cfg["modelo"], max_tokens=32,
            temperature=cfg["temperatura"], system=cfg["system_prompt"],
            messages=[{"role": "user", "content": userp}],
        )
        txt = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return txt, None, time.time() - t0
    except Exception as e:
        return "", f"{type(e).__name__}: {e}", time.time() - t0


def coleta(pares_path: Path, config_path: Path, saida: Path,
           max_doc_chars: int = 1500) -> dict:
    exige_independencia(saida.parent if saida.parent.name else Path("."))

    art = R.carrega_pares(pares_path)   # recusa INVALIDO e sem procedencia
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    pares = art["pares"]

    feitos = {}
    if saida.exists():
        feitos = {r["par_id"]: r for r in
                  json.loads(saida.read_text(encoding="utf-8"))["rotulos"]}

    pend = [p for p in pares if p["par_id"] not in feitos]
    print(f"{len(pend)} de {len(pares)} pendentes. Modelo {cfg['modelo']}, "
          f"T={cfg['temperatura']}.\n")

    def grava():
        falhas = [r.get("modo_falha") for r in feitos.values()]
        saida.write_text(json.dumps({
            "experimento":    art["experimento"],
            "caminho":        "B (juiz LLM)",
            "modelo":         cfg["modelo"],
            "sha256_system":  cfg["sha256_system"],
            "sha256_pares":   art["sha256_pares"],
            "n_rotulados":    len(feitos),
            "n_total":        len(pares),
            "falhas":         J.veredito_de_falhas(falhas),
            "rotulos":        list(feitos.values()),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    for k, p in enumerate(pend, 1):
        userp = J.monta_user_prompt(p["query"], p["documento"][:max_doc_chars])
        txt, erro, lat = _chama(cfg, userp)
        modo = J.classifica_falha(txt, erro)
        feitos[p["par_id"]] = {
            "par_id":      p["par_id"],
            "resposta":    txt[:200],
            "resultado":   J.parse_resposta(txt) if modo is None else None,
            "modo_falha":  modo,
            "latencia_s":  round(lat, 2),
        }
        grava()
        if k % 25 == 0 or k == len(pend):
            v = J.veredito_de_falhas([r.get("modo_falha") for r in feitos.values()])
            print(f"  {len(feitos)}/{len(pares)}  falhas={v['inclassificaveis']} "
                  f"({v['taxa']:.1%})  {v['veredito'][:34]}")

    v = J.veredito_de_falhas([r.get("modo_falha") for r in feitos.values()])
    return {"n_rotulados": len(feitos), "n_total": len(pares),
            "falhas": v, "pronto_para_congelar": len(feitos) == len(pares)}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="caminho B do REL-001 (juiz LLM)")
    ap.add_argument("--pares",  default="pares_congelados.json")
    ap.add_argument("--config", default="REL-001_CONFIG_CONGELADA.json")
    ap.add_argument("--saida",  default="rotulos_llm.json")
    a = ap.parse_args(argv)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY ausente no ambiente.")
    r = coleta(Path(a.pares), Path(a.config), Path(a.saida))
    print("\n" + json.dumps(r, ensure_ascii=False, indent=2))
    if r["falhas"]["taxa"] > J.MAX_INCLASSIFICAVEIS:
        print("\nRODADA INVALIDA pelo §11 — registre a invalidacao, nao descarte "
              "os pares ruins para seguir.")
    print("\nPARAR. A analise so comeca com os DOIS conjuntos congelados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
