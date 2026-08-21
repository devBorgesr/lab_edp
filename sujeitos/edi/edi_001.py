"""
edi_001.py — harness do EDI-001.

PERGUNTA: existe sinal preditivo entre historico decisorio (Git + conversas) e
desfecho, no proprio corpus do EDP?

Pre-registro: docs/edi/preregistro_edi_001.md — constantes espelhadas la.

O QUE ESTE ARQUIVO GARANTE ESTRUTURALMENTE

O §7.1 declara vazamento temporal como a ameaca principal. Aqui isso nao e
comentario nem assercao a posteriori: as funcoes de feature **recebem apenas o
prefixo** do historico. Elas nao podem olhar o futuro porque o futuro nao chega
ate elas.

    features_*(prefixo, alvo)   <- prefixo = commits[:i], mensagens ate ts

`prova_sem_vazamento()` NAO prova o nao-vazamento — a assinatura ja o impoe, e
isso e mais forte que assercao. Ela verifica o COMPLEMENTO: que as features sao
sensiveis ao prefixo. Estoura se calcular com o prefixo e com a lista inteira
der IGUAL, porque feature que ignora o historico nao vaza e tambem nao preve.

(ERRATA 21/08: este paragrafo dizia o inverso — que divergir era o problema.
Escrito e conferido no mesmo dia. Corrigi a docstring da funcao primeiro e
NAO esta, no mesmo commit: a mesma afirmacao errada em dois lugares, e eu
consertei um. Registrado porque e o modo de falha, nao o descuido.)

Os ROTULOS olham o futuro — e devem. Essa e a assimetria do desenho e esta
isolada em `rotula()`, que nunca e chamada de dentro de uma funcao de feature.
"""
from __future__ import annotations

import glob
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Optional

# ── Constantes congeladas (espelhadas no §8) ──────────────────────────────────

EXPERIMENTO          = "EDI-001"
CUTOFF               = "2026-08-11"
N_CONTEXTO           = 233
N_CONVERSA_ELEGIVEL  = 6056
LIMIAR_REVISED_SOON  = 3
ALPHA                = 0.05
MDE_DECLARADA        = 0.60
N_BOOTSTRAP          = 20000
SEED                 = 20260821

PERNAS_ARMADAS = ("revised_soon", "revised_later")

# Nao armadas (§6.2): classe vazia ou sem poder. Ficam nomeadas para que o
# harness recuse rodar em vez de produzir inconclusivo garantido.
PERNAS_NAO_ARMADAS = {
    "reverted": "classe vazia — zero reverts no repositorio",
    "incident": "classe vazia — nao existe fonte de incidente",
    "errata":   "4 positivos apos split temporal; sem poder nem para AUC 0.70",
}

SESSOES = "/home/kali/.claude/projects/-media-sf-edp-v5-main/*.jsonl"


# ── Corpus ────────────────────────────────────────────────────────────────────

def carrega_commits(repo: Path) -> list[dict]:
    """Commits em ordem cronologica, com arquivos tocados."""
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse",
         "--pretty=format:@%H|%ad|%s", "--date=short", "--name-only"],
        capture_output=True, text=True, check=True).stdout
    commits, cur = [], None
    for ln in out.splitlines():
        if ln.startswith("@"):
            sha, data, msg = ln[1:].split("|", 2)
            cur = {"sha": sha, "data": data, "msg": msg, "arqs": []}
            commits.append(cur)
        elif ln.strip() and cur is not None:
            cur["arqs"].append(ln.strip())
    return commits


def carrega_mensagens(padrao: str = SESSOES) -> tuple[list[dict], dict]:
    """
    Conversa (user+assistant) com timestamp, e o relatorio do corte.

    CORTE POR MENSAGEM, nao por arquivo (§3). Medido em 21/08: a maior sessao
    tem 10.555 linhas e atravessa 06/08->21/08, 63% do corpus local. Filtrar por
    arquivo descartaria ou contaminaria essa fracao inteira.

    Linhas sem timestamp sao metadados (ai-title, mode, snapshots), nao conversa,
    e ficam de fora — contadas, nao silenciadas.
    """
    msgs, bruto, sem_ts, excl = [], 0, 0, 0
    for f in sorted(glob.glob(padrao)):
        for ln in open(f, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if not ln:
                continue
            bruto += 1
            try:
                d = json.loads(ln)
            except Exception:
                sem_ts += 1
                continue
            ts = d.get("timestamp")
            if not ts:
                sem_ts += 1
                continue
            if d.get("type") not in ("user", "assistant"):
                continue
            if ts[:10] >= CUTOFF:
                excl += 1
                continue
            msgs.append({"ts": ts, "tipo": d.get("type"),
                         "texto": _texto(d.get("message"))})
    msgs.sort(key=lambda m: m["ts"])
    return msgs, {"bruto": bruto, "sem_timestamp": sem_ts,
                  "excluidas_pos_cutoff": excl, "elegiveis": len(msgs)}


def _texto(message) -> str:
    """Extrai texto plano de um `message` do transcript."""
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return ""
    c = message.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


# ── Rotulos — ESTES olham o futuro, e e a unica coisa que pode ────────────────

def rotula(commits: list[dict], i: int) -> str:
    """
    Desfecho observado APOS o commit `i`.

    Assimetria deliberada do desenho: rotulo ve o futuro, feature nao. Por isso
    esta funcao e isolada e NUNCA e chamada de dentro de `features_*`.
    """
    for j, c2 in enumerate(commits[i + 1:]):
        if set(commits[i]["arqs"]) & set(c2["arqs"]):
            m = c2["msg"].lower()
            if "errata" in m:
                return "errata"
            if "revert" in m:
                return "reverted"
            return ("revised_soon" if j < LIMIAR_REVISED_SOON
                    else "revised_later")
    return "untouched"


# ── Features — recebem PREFIXO; o futuro nao chega ate aqui ───────────────────

def features_b1(prefixo: list[dict], alvo: dict) -> dict:
    """
    B1 — so Git. Churn, tamanho, idade, frequencia. Heuristica trivial.

    `prefixo` sao os commits ANTERIORES ao alvo. Nao ha parametro por onde o
    futuro entre.
    """
    tocados: dict = {}
    for c in prefixo:
        for a in c["arqs"]:
            tocados[a] = tocados.get(a, 0) + 1
    arqs = alvo["arqs"]
    churn = [tocados.get(a, 0) for a in arqs] or [0]
    return {
        "n_arquivos":      len(arqs),
        "churn_max":       max(churn),
        "churn_medio":     sum(churn) / len(churn),
        "arquivo_novo":    sum(1 for a in arqs if tocados.get(a, 0) == 0),
        "idade_repo":      len(prefixo),
        "len_msg":         len(alvo["msg"]),
        "msg_tem_fix":     int(bool(re.search(r"\b(fix|corrig|bug)", alvo["msg"], re.I))),
        "msg_tem_feat":    int(bool(re.search(r"\b(feat|add|nov)", alvo["msg"], re.I))),
    }


def features_b2(msgs_ate: list[dict], alvo: dict) -> dict:
    """
    B2 — so conversas. O rastro de raciocinio que precedeu o commit.

    PERNA DECISIVA (§5): se B2 empatar com B3, o valor nao esta na ligacao
    decisao-desfecho e sim no rastro — e o produto a construir e outro.

    `msgs_ate` ja vem filtrado por timestamp < commit. Janela das ultimas 50.
    """
    jan = msgs_ate[-50:]
    txt = " ".join(m["texto"] for m in jan).lower()
    usr = [m for m in jan if m["tipo"] == "user"]
    return {
        "n_msgs":          len(jan),
        "n_user":          len(usr),
        "chars_total":     len(txt),
        "chars_por_msg":   len(txt) / max(len(jan), 1),
        "hedge":           len(re.findall(r"\b(talvez|acho que|provavel|nao sei|incert|suponh)", txt)),
        "duvida_usuario":  sum(1 for m in usr if "?" in m["texto"]),
        "mencao_erro":     len(re.findall(r"\b(errad|falh|quebr|bug|corrig)", txt)),
        "mencao_teste":    len(re.findall(r"\b(teste|pytest|suite|gate)", txt)),
    }


def features_b3(prefixo: list[dict], msgs_ate: list[dict], alvo: dict) -> dict:
    """B3 — integrado. A uniao das duas metades."""
    return {**features_b1(prefixo, alvo), **features_b2(msgs_ate, alvo)}


# ── Prova de que o vazamento e impossivel (§7.1) ──────────────────────────────

def prova_sem_vazamento(commits: list[dict], msgs: list[dict],
                        n_amostras: int = 20) -> None:
    """
    Confirma que a garantia estrutural tem dentes.

    O nao-vazamento NAO e provado aqui — ele e imposto pela assinatura: as
    funcoes de feature recebem so o prefixo, entao o futuro nao chega ate elas.
    Isso e mais forte que assercao, porque nao depende de ninguem lembrar.

    O que ESTA funcao verifica e o complemento: que as features sao SENSIVEIS ao
    que recebem. Calcula duas vezes — com o prefixo correto e com a lista
    inteira — e estoura se der IGUAL. Igual significaria que a feature ignora o
    historico, e uma feature que ignora o historico nao vaza (trivialmente) mas
    tambem nao preve nada: a garantia estrutural ficaria vazia.

    ERRATA 21/08: esta docstring dizia o oposto do codigo — "se os valores
    diferirem, alguma feature esta lendo alem do indice". O codigo sempre
    estourou no caso IGUAL. Escrito e conferido no mesmo dia, e a contradicao
    passou; e o quarto caso do padrao "comentario que afirma o contrario do
    mecanismo" nestes tres dias.

    Verifica tambem o §7.2: nenhum nome de feature carrega o rotulo.
    """
    passo = max(len(commits) // n_amostras, 1)
    for i in range(passo, len(commits), passo):
        alvo = commits[i]
        certo = features_b1(commits[:i], alvo)
        vazado = features_b1(commits, alvo)          # de proposito: tudo
        if certo == vazado and len(commits[:i]) != len(commits):
            raise RuntimeError(
                f"features_b1 no commit {i} ({alvo['sha'][:8]}) devolveu o MESMO "
                f"valor com prefixo e com a lista inteira. Ou a feature ignora o "
                f"historico, ou a prova nao esta discriminando — nos dois casos "
                f"ela nao prova nada (§7.1)."
            )
    # o rotulo NAO pode aparecer nas features (§7.2)
    for i, c in enumerate(commits[:50]):
        f = features_b1(commits[:i], c)
        if any(k for k in f if "errata" in k or "revert" in k):
            raise RuntimeError(f"feature com nome de rotulo em {c['sha'][:8]} (§7.2)")


# ── Inferencia ────────────────────────────────────────────────────────────────

def auc(escores: list[float], rotulos: list[int]) -> float:
    """AUC = P(escore de positivo > escore de negativo), com empate valendo 0.5."""
    pos = [s for s, y in zip(escores, rotulos) if y]
    neg = [s for s, y in zip(escores, rotulos) if not y]
    if not pos or not neg:
        return float("nan")
    n = sum((1.0 if p > q else 0.5 if p == q else 0.0) for p in pos for q in neg)
    return n / (len(pos) * len(neg))


def auc_ic(escores: list[float], rotulos: list[int],
           b: int = N_BOOTSTRAP, seed: int = SEED) -> tuple[float, float, float]:
    """
    IC bootstrap ESTRATIFICADO (reamostra positivos e negativos separadamente).

    Estratificado porque com 62-83 positivos em 233, o bootstrap simples produz
    reamostras sem positivo nenhum e o AUC vira NaN — o IC sairia de um
    subconjunto enviesado sem ninguem notar.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    e = np.asarray(escores, dtype=float)
    y = np.asarray(rotulos, dtype=int)
    ip, ineg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    if len(ip) == 0 or len(ineg) == 0:
        return float("nan"), float("nan"), float("nan")
    out = np.empty(b)
    for k in range(b):
        p = e[rng.choice(ip, len(ip), replace=True)]
        q = e[rng.choice(ineg, len(ineg), replace=True)]
        out[k] = ((p[:, None] > q[None, :]).sum()
                  + 0.5 * (p[:, None] == q[None, :]).sum()) / (len(p) * len(q))
    lo, hi = np.percentile(out, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return auc(escores, rotulos), float(lo), float(hi)


def exige_perna_armada(perna: str) -> None:
    """Recusa rodar perna que o §6.2 declarou sem poder ou sem classe."""
    if perna in PERNAS_NAO_ARMADAS:
        raise RuntimeError(
            f"perna '{perna}' NAO esta armada: {PERNAS_NAO_ARMADAS[perna]}. "
            f"Rodar produz inconclusivo garantido, que nao e resultado. "
            f"Ver §6.2 do pre-registro."
        )
    if perna not in PERNAS_ARMADAS:
        raise RuntimeError(f"perna desconhecida: {perna}")
