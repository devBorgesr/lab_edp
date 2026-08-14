"""
exp_e9 — Encarnacao em CODIGO do Experimento E9 (validacao de instrumento).

Espelha docs/preregistro_experimento_e9.md. CONGELADO apos o primeiro disparo
real. Mudou a regua -> e o E10, nao o E9.

PERGUNTA: uma diferenca de carga que eu SEI ser de ~2x aparece separada nos
numeros que o motor reporta, nesta topologia, com repeticoes suficientes para
os ICs nao se tocarem?

O E9 NAO testa a arquitetura de memoria. Nao existe condicao com memoria, de
proposito (§5 do pre-registro). Ele mede a REGUA. Se a regua nao resolve 2x,
nao vai resolver a diferenca arquitetural, que e menor.

NAO MEDE ENERGIA. RAPL ausente no guest e o Windows nao da joule por processo
(§3.1). Mede tempo de computacao e tokens REPORTADOS PELO MOTOR. Proxy
declarado; o §12 lista o que isso proibe concluir.

TOPOLOGIA (emenda E-1): roda no WINDOWS, junto do Ollama. Sem fronteira de VM
entre medidor e medido. Habilita a segunda regua (psutil sobre o processo
ollama), que e independente da que o motor reporta.

Anti-mock (§10):
  - motor REAL (Ollama), nada simulado, nenhum tempo sintetizado;
  - producao do EDP INTOCADA: nao importa edp.*, nao chama retrieve(), nao le
    nem escreve data/sessions/. Os prompts sao do §8, nao do store;
  - harness ocioso durante a inferencia: o proprio medidor nao pode ser fonte
    de contencao.

CLASSIFICACAO PENDENTE (docs/DIVISAO.md): o sujeito deste experimento nao e o
EDP -- e o instrumento. Pelo criterio da DIVISAO, a maquinaria de medicao
serviria a outro pesquisador medindo outro sujeito e portanto tenderia a
bancada/. Fica aqui por consistencia com a serie E (exp_e7.py), e a decisao de
mover e do Daniel. Registrado para nao virar achado perdido.
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

from bancada.cobertura import ic_bootstrap_percentil, razao_agregada  # noqa: E402

try:
    import psutil  # segunda regua (emenda E-1)
except ImportError:
    psutil = None


# ── Constantes CONGELADAS (§11 do pre-registro) ──────────────────────────────
EXPERIMENTO            = "E9"
K_PROMPTS              = 12
N_REPETICOES           = 30
N_AQUECIMENTO          = 5
FATOR_CARGA            = 2
TOLERANCIA_CARGA       = (1.8, 2.2)
TEMPERATURA            = 0
NUM_PREDICT            = 64
SEED                   = 20260814
N_BOOTSTRAP            = 10000
NIVEL_IC               = 0.95
COBERTURA_MINIMA       = 0.90
LOAD_DURATION_MAX_FRAC = 0.01
CONDICOES              = ("base_A", "base_B", "dobro")
MODELO                 = "llama3.2:1b"        # E-1
TOPOLOGIA              = "windows_local"      # E-1
CONTENCAO_DECLARADA    = False                # E-1
FATOR_OUTLIER          = 5.0                  # E-2
MAX_DESCARTE_FRAC      = 0.05                 # E-2

OLLAMA = os.environ.get("E9_OLLAMA", "http://127.0.0.1:11434")

# §8 — dataset CONGELADO. 12 perguntas em PT-BR, comprimento variado de
# proposito: a razao agregada pondera por tokens, e um dataset de comprimento
# uniforme esconderia o custo fixo por requisicao que o §7 preve.
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

# §5 — preenchimento neutro. PT-BR, sem codigo, sem acentuacao incomum, sem
# repetir n-grama que possa acionar cache de prefixo do motor: cada frase e
# montada com sorteio deterministico a partir da SEED.
_LEXICO = (
    "processo", "registro", "conjunto", "medida", "amostra", "unidade",
    "trecho", "estado", "camada", "limite", "sequencia", "intervalo",
    "estrutura", "criterio", "fator", "margem", "grupo", "escala",
)


def _frase_de_preenchimento(rng: random.Random) -> str:
    palavras = [rng.choice(_LEXICO) for _ in range(rng.randint(8, 14))]
    return "O " + " ".join(palavras) + "."


# ── Transporte ───────────────────────────────────────────────────────────────

def _post(caminho: str, corpo: dict, timeout: float = 600.0) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA}{caminho}",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(caminho: str, timeout: float = 30.0) -> dict:
    with urllib.request.urlopen(f"{OLLAMA}{caminho}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def digest_do_modelo() -> str:
    """
    Pina os PESOS, nao a tag (E-1).

    Tag de Ollama pode ser reempurrada apontando para outro blob. Congelar
    "llama3.2:1b" sem digest congelaria um nome, nao um modelo.
    """
    for m in _get("/api/tags").get("models", []):
        if m.get("name") == MODELO or m.get("model") == MODELO:
            return str(m.get("digest", ""))[:16]
    raise RuntimeError(
        f"modelo {MODELO} nao encontrado no Ollama. Rode: ollama pull {MODELO}"
    )


# ── Medicao ──────────────────────────────────────────────────────────────────

def _cpu_do_motor() -> Optional[float]:
    """Segunda regua (E-1): tempo de CPU do processo ollama, em segundos."""
    if psutil is None:
        return None
    total = 0.0
    achou = False
    for p in psutil.process_iter(["name"]):
        nome = (p.info.get("name") or "").lower()
        if "ollama" in nome:
            try:
                t = p.cpu_times()
                total += t.user + t.system
                achou = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return total if achou else None


def uma_requisicao(prompt: str, num_predict: int = NUM_PREDICT) -> dict:
    """
    Uma chamada ao motor. Devolve os SEIS campos crus, nao o agregado.

    O harness fica ocioso entre enviar e receber (§10) -- as duas leituras de
    CPU cercam a chamada e nada mais roda no meio.
    """
    cpu_antes = _cpu_do_motor()
    t0 = time.perf_counter()
    r = _post("/api/generate", {
        "model":  MODELO,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": TEMPERATURA,
            "seed":        SEED,
            "num_predict": num_predict,
        },
    })
    parede = time.perf_counter() - t0
    cpu_depois = _cpu_do_motor()

    delta_cpu = (
        round(cpu_depois - cpu_antes, 6)
        if (cpu_antes is not None and cpu_depois is not None) else None
    )
    return {
        "prompt_eval_count":    r.get("prompt_eval_count"),
        "prompt_eval_duration": r.get("prompt_eval_duration"),
        "eval_count":           r.get("eval_count"),
        "eval_duration":        r.get("eval_duration"),
        "load_duration":        r.get("load_duration"),
        "total_duration":       r.get("total_duration"),
        "parede_s":             round(parede, 6),
        "cpu_motor_s":          delta_cpu,
        "regua_secundaria":     delta_cpu is not None,
    }


def tokens_do_prompt(texto: str) -> int:
    """
    Pergunta ao MOTOR quantos tokens o prompt tem (emenda E-3).

    num_predict=1 devolve prompt_eval_count sem gerar texto relevante. Usar o
    motor como tokenizador e medicao; assumir "4 chars ~ 1 token" para
    dimensionar o preenchimento seria usar, DENTRO do experimento, exatamente
    a constante nao-calibrada que a Fase 2 existe para medir.
    """
    return int(uma_requisicao(texto, num_predict=1)["prompt_eval_count"] or 0)


def calibrar_preenchimento(prompt: str, rng: random.Random) -> tuple[str, int, float]:
    """
    Cresce o preenchimento frase a frase ate prompt_eval_count cair na faixa.

    Devolve (texto_preenchido, n_frases, razao_atingida).
    """
    base = tokens_do_prompt(prompt)
    if base <= 0:
        raise RuntimeError(f"motor devolveu prompt_eval_count invalido para: {prompt!r}")
    alvo_lo, alvo_hi = TOLERANCIA_CARGA
    frases: list[str] = []
    for _ in range(400):                       # teto de seguranca
        razao = tokens_do_prompt(prompt + " " + " ".join(frases)) / base if frases else 1.0
        if razao >= alvo_lo:
            return (prompt + " " + " ".join(frases), len(frases), razao)
        frases.append(_frase_de_preenchimento(rng))
    raise RuntimeError(f"preenchimento nao atingiu {alvo_lo}x em 400 frases")


# ── Plano de execucao ────────────────────────────────────────────────────────

def plano_de_execucao(rng: random.Random) -> list[tuple[str, int]]:
    """
    Ordem INTERCALADA e EMBARALHADA (§8).

    Rodar todas as base_A e depois todas as dobro confundiria tempo com
    aquecimento termico -- e o controle negativo so pegaria isso tarde demais.
    Embaralhar com seed congelada desalinha deriva e condicao.
    """
    plano = [
        (cond, i)
        for cond in CONDICOES
        for i in range(K_PROMPTS)
        for _ in range(N_REPETICOES)
    ]
    rng.shuffle(plano)
    return plano


# ── Disparo ──────────────────────────────────────────────────────────────────

@dataclass
class ResultadoE9:
    dry_run:   bool = True
    armed:     bool = False
    abortado:  str = ""
    digest:    str = ""
    calibragem: list = field(default_factory=list)
    amostras:  list = field(default_factory=list)


def run_e9(dry_run: bool = True) -> ResultadoE9:
    res = ResultadoE9(dry_run=dry_run)
    res.armed = os.environ.get("EDP_LAB_ARMED") == "1"
    if not dry_run and not res.armed:
        raise RuntimeError(
            "disparo REAL exige EDP_LAB_ARMED=1. "
            "Use a prova-no-espelho primeiro: python -m exp_e9 --dry-run"
        )

    res.digest = digest_do_modelo()
    rng = random.Random(SEED)

    # Calibragem do preenchimento (E-3) -- impressa para revisao humana.
    preenchidos: list[str] = []
    for p in PROMPTS:
        texto, n_frases, razao = calibrar_preenchimento(p, rng)
        preenchidos.append(texto)
        res.calibragem.append({"prompt": p[:48], "n_frases": n_frases,
                               "razao": round(razao, 3)})

    if dry_run:
        # A prova-no-espelho exercita o encanamento inteiro com UMA repeticao
        # por condicao -- nao gera dado de veredito, so prova que roda.
        for cond in CONDICOES:
            texto = preenchidos[0] if cond == "dobro" else PROMPTS[0]
            am = uma_requisicao(texto)
            am.update({"condicao": cond, "prompt_idx": 0, "dry_run": True})
            res.amostras.append(am)
        return res

    plano = plano_de_execucao(rng)

    # Aquecimento descartado ANTES de qualquer estatistica (§8): o
    # load_duration do primeiro carregamento nao pode entrar.
    for _ in range(N_AQUECIMENTO):
        uma_requisicao(PROMPTS[0])

    for cond, idx in plano:
        texto = preenchidos[idx] if cond == "dobro" else PROMPTS[idx]
        am = uma_requisicao(texto)
        am.update({"condicao": cond, "prompt_idx": idx, "dry_run": False,
                   "digest": res.digest, "ts": time.time()})
        res.amostras.append(am)

    return res


# ── Analise (pos-coleta, criterio do §6) ─────────────────────────────────────

def _pares(amostras: list, cond: str) -> tuple[list, int]:
    """Pares (duracao, tokens) da condicao, com descarte de outlier (E-2)."""
    brutas = [a for a in amostras if a["condicao"] == cond
              and a.get("prompt_eval_count") and a.get("prompt_eval_duration")]
    if not brutas:
        return [], 0
    mediana = statistics.median(a["total_duration"] or 0 for a in brutas)
    limite = mediana * FATOR_OUTLIER
    mantidas = [a for a in brutas if (a["total_duration"] or 0) <= limite]
    return ([(float(a["prompt_eval_duration"]), float(a["prompt_eval_count"]))
             for a in mantidas],
            len(brutas) - len(mantidas))


def score_e9(amostras: list) -> dict:
    rng = random.Random(SEED)
    out: dict = {"condicoes": {}, "descartes": {}}

    for cond in CONDICOES:
        pares, n_desc = _pares(amostras, cond)
        if not pares:
            out["condicoes"][cond] = None
            continue
        lo, hi = ic_bootstrap_percentil(pares, b=N_BOOTSTRAP, conf=NIVEL_IC, rng=rng)
        out["condicoes"][cond] = {
            "n":       len(pares),
            "razao":   razao_agregada(pares),   # ns por token de entrada
            "ic":      (lo, hi),
            "tokens":  statistics.median(p[1] for p in pares),
        }
        total = len(pares) + n_desc
        out["descartes"][cond] = {"n": n_desc, "frac": n_desc / total if total else 0.0}

    a, b, d = (out["condicoes"].get(c) for c in CONDICOES)

    # 1. VALIDADE -- controle negativo. Condicoes IDENTICAS tem de sobrepor.
    if not (a and b):
        out["veredito"] = "SEM DADO"
        return out
    sobrepoe = not (a["ic"][1] < b["ic"][0] or b["ic"][1] < a["ic"][0])
    out["controle_negativo_ok"] = sobrepoe
    if not sobrepoe:
        out["veredito"] = "INSTRUMENTO INVALIDO"
        out["motivo"] = ("base_A e base_B sao byte-identicas e os ICs separaram: "
                         "deriva termica, contencao ou recarga de modelo. "
                         "Nada e afirmado sobre `dobro`.")
        return out

    # 2. SANIDADE -- a carga de fato dobrou.
    if not d:
        out["veredito"] = "SEM DADO"
        return out
    razao_carga = d["tokens"] / a["tokens"] if a["tokens"] else 0.0
    out["razao_carga"] = razao_carga
    if not (TOLERANCIA_CARGA[0] <= razao_carga <= TOLERANCIA_CARGA[1]):
        out["veredito"] = "SANIDADE FALHOU (carga)"
        return out

    # 3. SANIDADE -- modelo nao recarregou.
    fracs = [(x.get("load_duration") or 0) / (x.get("total_duration") or 1)
             for x in amostras if not x.get("dry_run")]
    out["load_frac_mediana"] = statistics.median(fracs) if fracs else 0.0
    if out["load_frac_mediana"] >= LOAD_DURATION_MAX_FRAC:
        out["veredito"] = "SANIDADE FALHOU (recarga de modelo)"
        return out

    # 3b. Descarte excessivo invalida a condicao (E-2).
    for cond, info in out["descartes"].items():
        if info["frac"] > MAX_DESCARTE_FRAC:
            out["veredito"] = f"CONDICAO INSTAVEL ({cond})"
            return out

    # 4. CONFIRMATORIO -- H1.
    separou = d["ic"][0] > a["ic"][1]
    out["veredito"] = "H1 CONFIRMADA" if separou else "H0 NAO REJEITADA"
    # descritivo, explicitamente NAO criterio (§6)
    out["razao_medida"] = d["razao"] / a["razao"] if a["razao"] else 0.0
    return out


# ── CLI ──────────────────────────────────────────────────────────────────────

def _imprimir(res: ResultadoE9, veredito: Optional[dict] = None) -> None:
    print("\n" + "=" * 68)
    print(f"E9 — {'DRY-RUN (prova-no-espelho)' if res.dry_run else 'REAL (armado)'}")
    print("=" * 68)
    print(f"  modelo          : {MODELO}  digest={res.digest}")
    print(f"  topologia       : {TOPOLOGIA}  contencao_declarada={CONTENCAO_DECLARADA}")
    seg = any(a.get("regua_secundaria") for a in res.amostras)
    print(f"  regua secundaria: {'psutil ATIVA' if seg else 'AUSENTE (psutil nao instalado)'}")
    print(f"  amostras        : {len(res.amostras)}")

    print("\n  calibragem do preenchimento (E-3 — motor como tokenizador):")
    for c in res.calibragem:
        print(f"    {c['razao']:>5.2f}x  {c['n_frases']:>3} frases  | {c['prompt']}")

    if veredito:
        print("\n  " + "-" * 64)
        for cond in CONDICOES:
            info = veredito["condicoes"].get(cond)
            if not info:
                print(f"    {cond:<8} sem dado"); continue
            lo, hi = info["ic"]
            print(f"    {cond:<8} n={info['n']:<5} "
                  f"{info['razao']/1e6:>8.3f} ms/token  "
                  f"IC[{lo/1e6:.3f}, {hi/1e6:.3f}]")
        print(f"\n    controle negativo : {'OK (sobrepoe)' if veredito.get('controle_negativo_ok') else 'FALHOU'}")
        if "razao_carga" in veredito:
            print(f"    carga atingida    : {veredito['razao_carga']:.2f}x")
        print(f"\n    VEREDITO          : {veredito['veredito']}")
        if veredito.get("motivo"):
            print(f"    motivo            : {veredito['motivo']}")
        if "razao_medida" in veredito:
            print(f"    razao medida      : {veredito['razao_medida']:.2f}x "
                  f"(descritivo — NAO e criterio, §6)")
    print("=" * 68)
    if res.dry_run:
        print("  Prova-no-espelho OK. Disparo REAL: EDP_LAB_ARMED=1 sem --dry-run.")


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Experimento E9 — validacao de instrumento")
    p.add_argument("--dry-run", action="store_true",
                   help="prova-no-espelho: encanamento + motor REAL, sem armar")
    p.add_argument("--saida", default="e9_amostras.jsonl",
                   help="onde gravar as amostras cruas")
    args = p.parse_args(argv)

    try:
        res = run_e9(dry_run=args.dry_run)
    except (RuntimeError, urllib.error.URLError, OSError) as e:
        print(f"\n[RECUSADO/ERRO] {e}")
        return 1

    veredito = None
    if not res.dry_run:
        Path(args.saida).write_text(
            "\n".join(json.dumps(a, ensure_ascii=False) for a in res.amostras),
            encoding="utf-8",
        )
        veredito = score_e9(res.amostras)

    _imprimir(res, veredito)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
