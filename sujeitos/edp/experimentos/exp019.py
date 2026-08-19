"""
exp019.py — harness do Experimento 019.

PERGUNTA: as instrucoes compensatorias do SYSTEM_TEMPLATE (linhas 16-48, 1.877
dos 3.095 chars) previnem os comportamentos que declaram prevenir?

Pre-registro: docs/preregistro_experimento_019.md — as constantes abaixo sao
espelhadas la e conferidas por tests/test_preregistro_espelha_harness.py.

O QUE ESTE ARQUIVO **NAO** FAZ, DE PROPOSITO

Nao escreve as queries. O §4-bis proibe: quem escreve as queries leu as 60
linhas do template primeiro, e qualquer pergunta escrita depois disso e
calibrada — mesmo sem intencao — para casar com o que as regras proibem.
Construir a prova a partir do gabarito confirma H1 por construcao. As queries
sao AMOSTRADAS do log real, que nao sabe que as regras existem.

Nao julga qualidade de resposta. O E10 mediu essa classe (verificador como
critico autonomo) e a H1 foi refutada. Aqui so entra o contavel por regra fixa.

ANTI-MOCK (§7)

O template e lido do FONTE do edp_v5, nunca transcrito — copia manual diverge
em silencio do que producao usa. Quando o pacote `edp` esta importavel,
`confere_contra_import()` prova que o literal lido do arquivo e identico ao
atributo em memoria.

USO
    PYTHONPATH=/media/sf_edp_v5_main python sujeitos/edp/experimentos/exp019.py --dry-run
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

# ── Constantes congeladas (espelhadas no §8 do pre-registro) ──────────────────

EXPERIMENTO        = "019"
N_POR_CELULA       = 40
ALPHA              = 0.05
MIN_CHARS_VERBATIM = 20
LINHAS_ABLADAS     = (16, 48)     # 1-indexado, inclusivo nas duas pontas
SEED               = 20260818
TOP_K              = 5
MIN_SCORE          = 0.0

# Guarda de tamanho do §7. MEDIDO em 18/08/2026 contra o template real, nao
# escolhido: se o SYSTEM_TEMPLATE mudar, o corte deixa de bater e o harness
# PARA — em vez de ablar silenciosamente o bloco errado.
CHARS_BLOCO_ABLADO = 1877
CHARS_TEMPLATE     = 3095

# Listas congeladas ANTES de olhar o corpus (§4-bis). Nao crescem depois do dado.
MARCADORES_ALVO = (
    # pronome / referencia a turno
    "isso", "sua resposta", "o que voce disse", "qual a base", "tirou", "falou",
    # temporal / continuidade
    "ontem", "agora", "antes", "ultima vez", "lembra",
    # citacao de memoria
    "aquela", "voce falou de",
)

FRASES_NEGACAO = (
    "nao tenho memoria",
    "nao tenho acesso a",
    "nao consigo lembrar",
    "nao tenho como saber",
    "sou um modelo",
)


# ── Leitura do template (anti-mock) ───────────────────────────────────────────

def caminho_do_kernel() -> Path:
    """
    Raiz do edp_v5. Falha alto em vez de adivinhar.

    Mesma guarda do exp_e10: se EDP_KERNEL estiver setado, ele manda; senao usa
    o PYTHONPATH. Rodar contra o kernel errado e o erro que invalidou tres
    medicoes em 18/08/2026, e ele nao da sintoma — so numero errado.
    """
    env = os.environ.get("EDP_KERNEL")
    if env:
        p = Path(env)
        if not (p / "edp" / "llm_adapter.py").exists():
            raise RuntimeError(f"EDP_KERNEL={env} nao contem edp/llm_adapter.py")
        return p
    for raiz in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if raiz and (Path(raiz) / "edp" / "llm_adapter.py").exists():
            return Path(raiz)
    raise RuntimeError(
        "edp_v5 nao localizado. Rode com o kernel no PYTHONPATH:\n"
        "    PYTHONPATH=/media/sf_edp_v5_main python sujeitos/edp/experimentos/exp019.py"
    )


def carrega_template(raiz: Optional[Path] = None) -> str:
    """SYSTEM_TEMPLATE lido do FONTE — nunca transcrito."""
    raiz = raiz or caminho_do_kernel()
    fonte = (raiz / "edp" / "llm_adapter.py").read_text(encoding="utf-8")
    m = re.search(r'SYSTEM_TEMPLATE\s*=\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', fonte, re.S)
    if not m:
        raise RuntimeError("SYSTEM_TEMPLATE nao encontrado como literal em llm_adapter.py")
    return m.group(1)


def confere_contra_import(template: str) -> bool:
    """
    Prova que o literal lido do arquivo e o mesmo objeto que producao usa.

    Devolve False (sem estourar) quando `edp` nao esta importavel — o gate de
    espelhamento importa este modulo sem o kernel no path.
    """
    try:
        from edp.llm_adapter import EDPRuntime  # type: ignore
    except Exception:
        return False
    return getattr(EDPRuntime, "SYSTEM_TEMPLATE", None) == template


# ── Ablacao (§3) ──────────────────────────────────────────────────────────────

def abla(template: str) -> str:
    """
    Remove as linhas 16-48 (blocos compensatorios), preservando o resto.

    A guarda de tamanho e o ponto: um template editado desloca as linhas, e sem
    ela o experimento ablaria o bloco errado sem sintoma nenhum — exatamente o
    modo de falha silenciosa que o §7 existe para impedir.
    """
    linhas = template.splitlines()
    ini, fim = LINHAS_ABLADAS
    bloco = "\n".join(linhas[ini - 1:fim])
    if len(bloco) != CHARS_BLOCO_ABLADO or len(template) != CHARS_TEMPLATE:
        raise RuntimeError(
            f"o SYSTEM_TEMPLATE mudou: template={len(template)} chars "
            f"(esperado {CHARS_TEMPLATE}), bloco {ini}-{fim}={len(bloco)} chars "
            f"(esperado {CHARS_BLOCO_ABLADO}). O corte nao bate mais — refaca o "
            f"pre-registro em vez de ablar o bloco errado."
        )
    return "\n".join(linhas[:ini - 1] + linhas[fim:])


# ── Estratificacao e amostragem (§4-bis) ──────────────────────────────────────

def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn")


def normaliza(texto: str) -> str:
    """strip + casefold + colapso de whitespace — mesma do _dedup_pass_exp017."""
    return re.sub(r"\s+", " ", (texto or "").strip().casefold())


def classifica(texto: str) -> str:
    """`alvo` se casa qualquer marcador congelado; `controle` se nenhum."""
    t = _sem_acento(texto)
    return "alvo" if any(m in t for m in MARCADORES_ALVO) else "controle"


def amostra(entries: Iterable[dict], n_por_celula: int = N_POR_CELULA,
            seed: int = SEED) -> dict:
    """
    Amostra estratificada do log real. Devolve {'alvo': [...], 'controle': [...]}.

    Deduplica por texto normalizado ANTES de estratificar: medido em 18/08 ha 14
    copias extras no store, e amostrar sem deduplicar daria peso extra a quem
    esta repetido — enviesando para o que ja domina.

    NAO completa estrato curto. Se faltar, falta, e o §4-bis manda reportar o N
    alcancado com o poder recalculado: a escassez E o achado.
    """
    import random
    vistos: set = set()
    estratos: dict = {"alvo": [], "controle": []}
    for e in entries:
        if (e or {}).get("source_type") != "user_input":
            continue
        txt = (e.get("text") or "").strip()
        if not txt:
            continue
        k = normaliza(txt)
        if k in vistos:
            continue
        vistos.add(k)
        estratos[classifica(txt)].append(e)

    rng = random.Random(seed)
    return {nome: rng.sample(itens, min(n_por_celula, len(itens)))
            for nome, itens in estratos.items()}


# ── Metricas (§5 — extrativas, nenhuma usa julgamento de modelo) ──────────────

def nega_memoria(resposta: str) -> bool:
    """Casa a lista congelada de frases de negacao, sem acento e sem caixa."""
    r = _sem_acento(resposta)
    return any(f in r for f in FRASES_NEGACAO)


def usa_turno_anterior(resposta: str, texto_turno_anterior: str,
                       min_chars: int = MIN_CHARS_VERBATIM) -> bool:
    """
    True se a resposta contem >= min_chars contiguos VERBATIM do turno anterior.

    Comparacao de substring, nao juizo de relevancia — e essa a diferenca que o
    E10 cobrou caro.
    """
    a, b = normaliza(resposta), normaliza(texto_turno_anterior)
    if len(b) < min_chars or not a:
        return False
    return any(b[i:i + min_chars] in a for i in range(len(b) - min_chars + 1))


# ── Inferencia (§6) ───────────────────────────────────────────────────────────

def wilson_diff(k1: int, n1: int, k2: int, n2: int, alpha: float = ALPHA,
                b: int = 20000, seed: int = SEED) -> tuple[float, float, float]:
    """
    IC bootstrap da diferenca de proporcoes (p2 - p1). Devolve (dif, lo, hi).

    Bootstrap em vez de formula fechada pelo mesmo motivo do arco E9: a
    cobertura e verificavel por simulacao, e formula fechada com n pequeno e
    proporcao perto de 0 mente sobre a cobertura.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    p1, p2 = k1 / n1, k2 / n2
    a = rng.binomial(n1, p1, b) / n1
    c = rng.binomial(n2, p2, b) / n2
    d = c - a
    lo, hi = np.percentile(d, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(p2 - p1), float(lo), float(hi)


def veredito(alvo: tuple[int, int, int, int],
             controle: tuple[int, int, int, int]) -> dict:
    """
    §6: H1 exige IC do ALVO excluindo zero na direcao positiva E o CONTROLE
    NAO excluindo zero. Se o controle mover junto, ha confundidor e o resultado
    e INVALIDO — nao ajustado.
    """
    d_a, lo_a, hi_a = wilson_diff(*alvo)
    d_c, lo_c, hi_c = wilson_diff(*controle)
    alvo_move     = lo_a > 0
    controle_move = (lo_c > 0) or (hi_c < 0)
    if controle_move:
        v = "INVALIDO (controle negativo moveu — confundidor)"
    elif alvo_move:
        v = "H1"
    else:
        v = "H0 (nao detectado com este poder — ver §6)"
    return {"veredito": v,
            "alvo":     {"dif": d_a, "ic": [lo_a, hi_a]},
            "controle": {"dif": d_c, "ic": [lo_c, hi_c]}}


# ── Entrada ───────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description=f"Experimento {EXPERIMENTO}")
    ap.add_argument("--dry-run", action="store_true",
                    help="so mostra template/ablacao/estratos, sem chamar modelo")
    a = ap.parse_args(argv)

    t = carrega_template()
    ab = abla(t)
    print(json.dumps({
        "experimento":       EXPERIMENTO,
        "template_chars":    len(t),
        "ablado_chars":      len(ab),
        "removido_chars":    len(t) - len(ab),
        "confere_com_import": confere_contra_import(t),
    }, indent=2, ensure_ascii=False))

    if a.dry_run:
        print("\n--dry-run: nada foi chamado. O disparo real exige o §8-bis "
              "com o MODELO registrado antes.")
        return 0

    raise SystemExit(
        "disparo real ainda nao armado: registre o MODELO no §8-bis do "
        "pre-registro e o dataset amostrado, conforme §4-bis."
    )


if __name__ == "__main__":
    raise SystemExit(main())
