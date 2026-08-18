"""
exp_e9b — Encarnacao em CODIGO do Experimento E9b (validacao de instrumento, 2a).

Espelha docs/preregistro_experimento_e9b.md. CONGELADO apos o 1o disparo real.
Mudou a regua -> e o E9c.

O QUE MUDA EM RELACAO AO E9

1. `load_duration` comparado em ABSOLUTO entre condicoes, nao como fracao de
   `total_duration`. Se o setup e custo fixo em ms e o total cresce em `dobro`,
   a fracao CAI mecanicamente: mediria o denominador, nao o overhead. Foi o
   erro que reprovou o E9, e corrigir a magnitude do teto nao o consertaria.

2. Criterio por EQUIVALENCIA sobre a razao entre condicoes, com IC proprio,
   em vez de "os ICs marginais se sobrepoem". Para o controle negativo a
   logica se inverte: ali se quer provar IGUALDADE, e IC largo sobrepoe
   trivialmente — premia falta de resolucao. IC largo agora REPROVA.

3. Condicao `meio` (~1,5x). Dois pontos nao distinguem "custo cresce com o
   comprimento" de "algo muda de regime entre 1x e 2x". Tres distinguem:
   monotonicidade suave contra salto. Responde ao que o E9 explicitamente NAO
   demonstrou (§3.3).

4. Preenchimento ANINHADO: o texto de `dobro` estende o de `meio`. Assim a
   dose-resposta varia so o comprimento, nao o conteudo do preenchimento.

NAO MEDE ENERGIA. Mesma declaracao do E9 §3.1 — RAPL ausente no guest, Windows
sem joule por processo. Mede tempo de computacao e tokens reportados pelo motor.

Anti-mock: motor REAL, producao do EDP intocada (nao importa edp.*, nao chama
retrieve(), nao toca data/sessions/), harness ocioso durante a inferencia.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_RAIZ = Path(__file__).resolve().parents[3]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from bancada.cobertura import (  # noqa: E402
    ic_bootstrap_razao_de_razoes,
    razao_agregada,
)

try:
    import psutil
except ImportError:
    psutil = None


# ── Constantes CONGELADAS (§11 do pre-registro) ──────────────────────────────
EXPERIMENTO       = "E9b"
K_PROMPTS         = 12
N_REPETICOES      = 30
N_AQUECIMENTO     = 5
TOLERANCIA_CARGA  = (1.8, 2.2)
TOLERANCIA_MEIO   = (1.35, 1.65)
DELTA_EQUIV       = 0.10          # E9b-6: 0.07 dava 67% de potencia no controle
TEMPERATURA       = 0
NUM_PREDICT       = 64
SEED              = 20260814
N_BOOTSTRAP       = 10000
NIVEL_IC          = 0.95
COBERTURA_MINIMA  = 0.90
FATOR_OUTLIER     = 5.0
MAX_DESCARTE_FRAC = 0.05
CONDICOES         = ("base_A", "base_B", "meio", "dobro")
REFERENCIA        = "base_A"
MODELO            = "llama3.2:1b"
TOPOLOGIA         = "windows_local"

OLLAMA = os.environ.get("E9_OLLAMA", "http://127.0.0.1:11434")

# §8 — dataset CONGELADO, identico ao E9 (amostras novas, mesmos prompts).
PROMPTS = (
    "O que e uma memoria episodica?",
    "Explique brevemente a diferenca entre memoria semantica e procedural.",
    "Por que sistemas de recuperacao usam similaridade de vetores?",
    "Descreva o que acontece quando um indice fica desatualizado.",
    "Qual a diferenca entre estimar um custo e medir um custo?",
    "Explique por que um limiar fixo pode ficar acima do maximo de um conjunto.",
    "O que caracteriza um controle negativo em um experimento?",
    "Descreva o papel de uma hipotese nula em uma decisao pre-registrada.",
    "Por que reamostrar pares preserva a estrutura de um estimador de razao?",
    "Explique a diferenca entre um gatilho e um filtro em um sistema de deteccao.",
    "O que significa dizer que um resultado vale apenas para o que foi medido?",
    "Descreva por que ordem de execucao pode se confundir com efeito de carga.",
)

_LEXICO = (
    "processo", "registro", "conjunto", "medida", "amostra", "unidade",
    "trecho", "estado", "camada", "limite", "sequencia", "intervalo",
    "estrutura", "criterio", "fator", "margem", "grupo", "escala",
)


def _frase(rng: random.Random) -> list:
    return ("O " + " ".join(rng.choice(_LEXICO) for _ in range(rng.randint(8, 14)))
            + ".").split()


# ── Transporte ───────────────────────────────────────────────────────────────

def _post(caminho: str, corpo: dict, timeout: float = 600.0) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA}{caminho}", data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def digest_do_modelo() -> str:
    with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=30) as r:
        tags = json.loads(r.read().decode("utf-8"))
    for m in tags.get("models", []):
        if MODELO in (m.get("name"), m.get("model")):
            return str(m.get("digest", ""))[:16]
    raise RuntimeError(f"modelo {MODELO} ausente. Rode: ollama pull {MODELO}")


def _cpu_do_motor() -> Optional[float]:
    if psutil is None:
        return None
    total, achou = 0.0, False
    for p in psutil.process_iter(["name"]):
        if "ollama" in (p.info.get("name") or "").lower():
            try:
                t = p.cpu_times()
                total += t.user + t.system
                achou = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return total if achou else None


def uma_requisicao(prompt: str, num_predict: int = NUM_PREDICT) -> dict:
    cpu0 = _cpu_do_motor()
    t0 = time.perf_counter()
    r = _post("/api/generate", {
        "model": MODELO, "prompt": prompt, "stream": False,
        "options": {"temperature": TEMPERATURA, "seed": SEED,
                    "num_predict": num_predict}})
    parede = time.perf_counter() - t0
    cpu1 = _cpu_do_motor()
    dcpu = round(cpu1 - cpu0, 6) if (cpu0 is not None and cpu1 is not None) else None
    return {
        "prompt_eval_count":    r.get("prompt_eval_count"),
        "prompt_eval_duration": r.get("prompt_eval_duration"),
        "eval_count":           r.get("eval_count"),
        "eval_duration":        r.get("eval_duration"),
        "load_duration":        r.get("load_duration"),
        "total_duration":       r.get("total_duration"),
        "parede_s":             round(parede, 6),
        "cpu_motor_s":          dcpu,
        "regua_secundaria":     dcpu is not None,
    }


def tokens_do_prompt(texto: str) -> int:
    """Motor como tokenizador (E-3). Estimar chars/token aqui seria usar, dentro
    do experimento, a constante que a Fase 2 existe para medir."""
    return int(uma_requisicao(texto, num_predict=1)["prompt_eval_count"] or 0)


# ── Calibragem em ESCADA, aninhada ───────────────────────────────────────────

def _montar(prompt: str, palavras: list) -> str:
    return prompt + (" " + " ".join(palavras) if palavras else "")


def _cresce_ate(prompt: str, base: int, palavras: list,
                faixa: tuple, rng: random.Random) -> float:
    """
    Cresce `palavras` in-place ate a razao cair DENTRO de `faixa`.

    Passo grosso por frase para chegar perto com poucas chamadas; passo fino
    palavra a palavra so quando o grosso estoura o teto. A guarda superior e a
    emenda E-4 do E9: la o calibrador so checava o piso e um prompt saiu em
    2,22x, enviesando o custo unitario na direcao da propria hipotese.
    """
    lo, hi = faixa
    antes = list(palavras)
    r = tokens_do_prompt(_montar(prompt, palavras)) / base if palavras else 1.0
    for _ in range(200):
        if r >= lo:
            break
        antes = list(palavras)
        palavras.extend(_frase(rng))
        r = tokens_do_prompt(_montar(prompt, palavras)) / base
    else:
        raise RuntimeError(f"preenchimento nao atingiu {lo}x em 200 frases")

    if r <= hi:
        return r

    ultima = palavras[len(antes):]
    palavras[:] = list(antes)
    r = tokens_do_prompt(_montar(prompt, palavras)) / base if palavras else 1.0
    for p in ultima:
        palavras.append(p)
        r = tokens_do_prompt(_montar(prompt, palavras)) / base
        if r >= lo:
            break
    return r


def calibrar_escada(prompt: str, rng: random.Random) -> dict:
    """
    Um crescimento so, capturado em dois degraus — `dobro` ESTENDE `meio`.

    Aninhar remove o conteudo do preenchimento como variavel entre os dois
    degraus: o que muda de `meio` para `dobro` e so comprimento.
    """
    base = tokens_do_prompt(prompt)
    if base <= 0:
        raise RuntimeError(f"prompt_eval_count invalido para {prompt!r}")
    palavras: list = []
    r_meio = _cresce_ate(prompt, base, palavras, TOLERANCIA_MEIO, rng)
    texto_meio, n_meio = _montar(prompt, palavras), len(palavras)
    r_dobro = _cresce_ate(prompt, base, palavras, TOLERANCIA_CARGA, rng)
    return {
        "prompt": prompt[:44], "base_tokens": base,
        "meio":  {"texto": texto_meio, "razao": round(r_meio, 3), "n": n_meio,
                  "na_faixa": TOLERANCIA_MEIO[0] <= r_meio <= TOLERANCIA_MEIO[1]},
        "dobro": {"texto": _montar(prompt, palavras), "razao": round(r_dobro, 3),
                  "n": len(palavras),
                  "na_faixa": TOLERANCIA_CARGA[0] <= r_dobro <= TOLERANCIA_CARGA[1]},
    }


# ── Disparo ──────────────────────────────────────────────────────────────────

@dataclass
class ResultadoE9b:
    dry_run: bool = True
    armed: bool = False
    digest: str = ""
    calibragem: list = field(default_factory=list)
    amostras: list = field(default_factory=list)


def plano_de_execucao(rng: random.Random) -> list:
    plano = [(c, i) for c in CONDICOES for i in range(K_PROMPTS)
             for _ in range(N_REPETICOES)]
    rng.shuffle(plano)
    return plano


def run_e9b(dry_run: bool = True) -> ResultadoE9b:
    res = ResultadoE9b(dry_run=dry_run)
    res.armed = os.environ.get("EDP_LAB_ARMED") == "1"
    if not dry_run and not res.armed:
        raise RuntimeError("disparo REAL exige EDP_LAB_ARMED=1. "
                           "Prova-no-espelho primeiro: --dry-run")

    res.digest = digest_do_modelo()
    rng = random.Random(SEED)
    res.calibragem = [calibrar_escada(p, rng) for p in PROMPTS]

    def _texto(cond: str, i: int) -> str:
        if cond == "meio":
            return res.calibragem[i]["meio"]["texto"]
        if cond == "dobro":
            return res.calibragem[i]["dobro"]["texto"]
        return PROMPTS[i]

    if dry_run:
        for cond in CONDICOES:
            am = uma_requisicao(_texto(cond, 0))
            am.update({"condicao": cond, "prompt_idx": 0, "dry_run": True})
            res.amostras.append(am)
        return res

    for _ in range(N_AQUECIMENTO):
        uma_requisicao(PROMPTS[0])

    for cond, idx in plano_de_execucao(rng):
        am = uma_requisicao(_texto(cond, idx))
        am.update({"condicao": cond, "prompt_idx": idx, "dry_run": False,
                   "digest": res.digest, "ts": time.time()})
        res.amostras.append(am)
    return res


# ── Analise — a cascata do §6, na ordem, parando no primeiro que falha ───────

def _validas(amostras: list, cond: str) -> list:
    return [a for a in amostras
            if a.get("condicao") == cond and not a.get("dry_run")
            and a.get("prompt_eval_count") and a.get("prompt_eval_duration")]


def _pares_custo(amostras: list, cond: str) -> tuple:
    """(pares (duracao, tokens), n_descartado) — descarte de outlier, E-2."""
    brutas = _validas(amostras, cond)
    if not brutas:
        return [], 0
    limite = statistics.median(a["total_duration"] or 0 for a in brutas) * FATOR_OUTLIER
    mant = [a for a in brutas if (a["total_duration"] or 0) <= limite]
    return ([(float(a["prompt_eval_duration"]), float(a["prompt_eval_count"]))
             for a in mant], len(brutas) - len(mant))


def _pares_load(amostras: list, cond: str) -> list:
    """(load_duration, 1.0) -> Sigma a / Sigma b = media. ABSOLUTO (§6.2)."""
    return [(float(a.get("load_duration") or 0), 1.0)
            for a in _validas(amostras, cond)]


def _dentro(ic: tuple, delta: float) -> bool:
    return (1.0 - delta) <= ic[0] and ic[1] <= (1.0 + delta)


def score_e9b(amostras: list) -> dict:
    rng = random.Random(SEED)
    out: dict = {"condicoes": {}, "descartes": {}, "R": {}, "checks": []}

    pares: dict = {}
    for cond in CONDICOES:
        p, nd = _pares_custo(amostras, cond)
        pares[cond] = p
        if not p:
            out["condicoes"][cond] = None
            continue
        out["condicoes"][cond] = {
            "n": len(p), "custo": razao_agregada(p),
            "tokens": statistics.median(x[1] for x in p),
        }
        out["descartes"][cond] = {"n": nd, "frac": nd / (len(p) + nd)}

    ref = pares.get(REFERENCIA)
    if not ref or any(not pares.get(c) for c in CONDICOES):
        out["veredito"] = "SEM DADO"
        return out

    for cond in CONDICOES:
        if cond == REFERENCIA:
            continue
        out["R"][cond] = ic_bootstrap_razao_de_razoes(
            pares[cond], ref, b=N_BOOTSTRAP, conf=NIVEL_IC, rng=rng)

    def _reg(nome, ok, detalhe):
        out["checks"].append({"check": nome, "ok": ok, "detalhe": detalhe})
        return ok

    # 6.1 VALIDADE — equivalencia do controle negativo
    ic_b = out["R"]["base_B"]
    if not _reg("6.1 controle negativo (equivalencia)", _dentro(ic_b, DELTA_EQUIV),
                f"IC(R base_B)=[{ic_b[0]:.4f}, {ic_b[1]:.4f}] "
                f"vs [{1-DELTA_EQUIV:.2f}, {1+DELTA_EQUIV:.2f}]"):
        out["veredito"] = "INSTRUMENTO INVALIDO"
        out["motivo"] = ("base_A e base_B sao byte-identicas e o IC da razao nao "
                         "coube na margem de equivalencia. Nada e afirmado sobre "
                         "meio ou dobro.")
        return out

    # 6.3 SANIDADE — recarga real, por FORMA. VEM ANTES do 6.2 (E9b-5):
    # o 6.2 compara MEDIAS de load_duration, e recarga e justamente o que
    # desestabiliza media — a distribuicao vira bimodal e o IC da razao
    # explode. Perguntar "o overhead e comum?" com a distribuicao contaminada
    # por recarga da resposta errada com mensagem enganosa. Detecta-se a
    # recarga primeiro; so entao a pergunta do 6.2 faz sentido.
    vivos = [a for a in amostras if not a.get("dry_run")]
    loads = [float(a.get("load_duration") or 0) for a in vivos]
    med_load = statistics.median(loads) if loads else 0.0
    recargas = sum(1 for x in loads if x > FATOR_OUTLIER * med_load)
    frac_rec = recargas / len(loads) if loads else 0.0
    out["recargas"] = {"n": recargas, "frac": frac_rec, "mediana_load": med_load}
    if not _reg("6.3 recarga por forma", frac_rec <= MAX_DESCARTE_FRAC,
                f"{recargas}/{len(loads)} acima de {FATOR_OUTLIER}x a mediana "
                f"({frac_rec*100:.2f}%, teto {MAX_DESCARTE_FRAC*100:.0f}%)"):
        out["veredito"] = "SANIDADE FALHOU (recarga real)"
        return out

    # 6.2 SANIDADE — load_duration ABSOLUTO comum as condicoes
    ic_l = ic_bootstrap_razao_de_razoes(_pares_load(amostras, "dobro"),
                                        _pares_load(amostras, REFERENCIA),
                                        b=N_BOOTSTRAP, conf=NIVEL_IC, rng=rng)
    out["R_load"] = ic_l
    if not _reg("6.2 load_duration comum", _dentro(ic_l, DELTA_EQUIV),
                f"IC(R load dobro/base_A)=[{ic_l[0]:.4f}, {ic_l[1]:.4f}]"):
        out["veredito"] = "SANIDADE FALHOU (load_duration difere entre condicoes)"
        return out

    # 6.4 SANIDADE — cargas atingiram os alvos
    tok_ref = out["condicoes"][REFERENCIA]["tokens"]
    alvos = {"meio": TOLERANCIA_MEIO, "dobro": TOLERANCIA_CARGA}
    out["cargas"] = {}
    for cond, faixa in alvos.items():
        rc = out["condicoes"][cond]["tokens"] / tok_ref if tok_ref else 0.0
        out["cargas"][cond] = rc
        if not _reg(f"6.4 carga {cond}", faixa[0] <= rc <= faixa[1],
                    f"{rc:.2f}x vs {faixa}"):
            out["veredito"] = f"SANIDADE FALHOU (carga {cond})"
            return out

    for cond, info in out["descartes"].items():
        if not _reg(f"6.4b descarte {cond}", info["frac"] <= MAX_DESCARTE_FRAC,
                    f"{info['frac']*100:.1f}% (teto {MAX_DESCARTE_FRAC*100:.0f}%)"):
            out["veredito"] = f"CONDICAO INSTAVEL ({cond})"
            return out

    # 6.5 CONFIRMATORIO — H1
    ic_d = out["R"]["dobro"]
    h1 = ic_d[0] > 1.0
    _reg("6.5 H1 (dobro > base_A)", h1, f"IC(R dobro)=[{ic_d[0]:.4f}, {ic_d[1]:.4f}]")
    if not h1:
        out["veredito"] = "H0 NAO REJEITADA (instrumento nao resolve 2x)"
        return out

    # 6.6 CONFIRMATORIO — H2 (dose-resposta)
    ic_m = out["R"]["meio"]
    h2 = ic_m[0] > 1.0 and ic_m[1] < ic_d[0]
    _reg("6.6 H2 (dose-resposta)", h2,
         f"IC(R meio)=[{ic_m[0]:.4f}, {ic_m[1]:.4f}] "
         f"{'<' if ic_m[1] < ic_d[0] else '>='} IC(R dobro).lo={ic_d[0]:.4f}")
    out["veredito"] = ("H1 E H2 CONFIRMADAS" if h2
                       else "H1 CONFIRMADA, H2 NAO (sem dose-resposta separada)")
    return out


# ── Saida ────────────────────────────────────────────────────────────────────

def _imprimir(res: ResultadoE9b, v: Optional[dict] = None) -> None:
    print("\n" + "=" * 72)
    print(f"E9b — {'DRY-RUN (prova-no-espelho)' if res.dry_run else 'REAL (armado)'}")
    print("=" * 72)
    print(f"  modelo   : {MODELO}  digest={res.digest}")
    print(f"  topologia: {TOPOLOGIA}   DELTA_EQUIV={DELTA_EQUIV}")
    seg = any(a.get("regua_secundaria") for a in res.amostras)
    print(f"  regua 2a : {'psutil ATIVA' if seg else 'AUSENTE'}")
    print(f"  amostras : {len(res.amostras)}")

    fora = []
    if res.calibragem:
        print(f"\n  calibragem em escada (aninhada)  "
              f"meio={TOLERANCIA_MEIO}  dobro={TOLERANCIA_CARGA}:")
        for c in res.calibragem:
            m, d = c["meio"], c["dobro"]
            if not m["na_faixa"]:
                fora.append(("meio", c["prompt"]))
            if not d["na_faixa"]:
                fora.append(("dobro", c["prompt"]))
            mk = lambda x: "  " if x["na_faixa"] else " <-FORA"
            print(f"    meio {m['razao']:>5.2f}x{mk(m)} | dobro {d['razao']:>5.2f}x{mk(d)}"
                  f" | base={c['base_tokens']:>3}t | {c['prompt']}")
        if fora:
            print(f"\n    {len(fora)} degrau(s) FORA da faixa declarada.")

    if v:
        print("\n  " + "-" * 68)
        for cond in CONDICOES:
            i = v["condicoes"].get(cond)
            if not i:
                print(f"    {cond:<8} sem dado"); continue
            r = v["R"].get(cond)
            sr = f"R=[{r[0]:.4f}, {r[1]:.4f}]" if r else "R= referencia"
            print(f"    {cond:<8} n={i['n']:<5} {i['custo']/1e6:>8.3f} ms/token  {sr}")
        print()
        for c in v["checks"]:
            print(f"    [{'ok ' if c['ok'] else 'FALHA'}] {c['check']:<34} {c['detalhe']}")
        print(f"\n    VEREDITO : {v['veredito']}")
        if v.get("motivo"):
            print(f"    motivo   : {v['motivo']}")
        if "dobro" in v.get("R", {}) and v["condicoes"].get(REFERENCIA):
            mag = v["condicoes"]["dobro"]["custo"] / v["condicoes"][REFERENCIA]["custo"]
            print(f"    R(dobro) : {mag:.3f}x  (descritivo — NAO e criterio, §6.8)")
    print("=" * 72)
    if res.dry_run and fora:
        print("  Prova-no-espelho INCOMPLETA: calibragem fora da faixa. NAO arme.")
    elif res.dry_run:
        print("  Prova-no-espelho OK. Disparo REAL: EDP_LAB_ARMED=1 sem --dry-run.")
        print(f"  Atencao: {len(CONDICOES)}x{K_PROMPTS}x{N_REPETICOES} = "
              f"{len(CONDICOES)*K_PROMPTS*N_REPETICOES} requisicoes.")


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Experimento E9b")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--saida", default="e9b_amostras.jsonl")
    p.add_argument("--score", metavar="ARQUIVO", default=None,
                   help="repontua do JSONL salvo, mesmo criterio congelado")
    args = p.parse_args(argv)

    if args.score:
        am = [json.loads(l) for l in
              Path(args.score).read_text(encoding="utf-8").splitlines() if l.strip()]
        r = ResultadoE9b(dry_run=False, armed=True, amostras=am)
        r.digest = next((a.get("digest", "") for a in am if a.get("digest")), "")
        _imprimir(r, score_e9b(am))
        return 0

    try:
        res = run_e9b(dry_run=args.dry_run)
    except (RuntimeError, urllib.error.URLError, OSError) as e:
        print(f"\n[RECUSADO/ERRO] {e}")
        return 1

    v = None
    if not res.dry_run:
        Path(args.saida).write_text(
            "\n".join(json.dumps(a, ensure_ascii=False) for a in res.amostras),
            encoding="utf-8")
        v = score_e9b(res.amostras)
    _imprimir(res, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
