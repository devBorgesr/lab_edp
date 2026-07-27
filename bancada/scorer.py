"""
edp.lab.scorer — Scorer do Experimento 001 (analise pos-coleta).

Le o prontuario, separa registros REAIS dos de dry-run, e computa a metrica
primaria CONFIRMATORIA travada no pré-registro (§6): fidelidade = a resposta
contem o valor-agulha? Depois testa H1 (fidelidade nao-crescente com a
profundidade do ruido) vs H0 (plana), e valida pelo controle negativo (ablacao
deve dar fidelidade ~0).

PURO: nao chama modelo, nao gasta. So le o que ja foi gravado e calcula.

Implementa o criterio do pré-registro (congelado ANTES do disparo). O accept-set
default replica exp001.ALVO_NORMALIZADO (constante que ja existia antes do
disparo) — este modulo nao altera a spec, so a aplica. A bancada nao importa
o experimento (PROIBIDO importar sujeitos.*): o accept-set e injetavel via
set_accept_set, mesmo padrao do relogio (bancada/prontuario.py).

FASE B6: as analises especificas por experimento (004/006/006b/007) foram
movidas para sujeitos/edp/analise/ (o `from . import expNNN` daqui era um
ImportError garantido — bancada/ nunca teve expNNN). Este modulo fica so com
o generico 001/003 e os primitivos compartilhados: wilson, normalize,
score_fidelity, extract_signals, valor_concluido, score_prontuario, report.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .prontuario import get_prontuario

logger = logging.getLogger("edp.lab.scorer")

# Accept-set injetavel (default: copia de exp001.ALVO_NORMALIZADO, o valor-agulha
# do pré-registro original). Quem monta o sujeito pode injetar outro via
# set_accept_set — o nucleo nao conhece exp001.
_ACCEPT_SET: Tuple[str, ...] = ("14h30", "14:30")


def set_accept_set(valores: Tuple[str, ...]) -> None:
    """Injeta o accept-set de fidelidade (ex.: exp001.ALVO_NORMALIZADO)."""
    global _ACCEPT_SET
    _ACCEPT_SET = tuple(valores)


# ── Criterio de fidelidade (§6 do pré-registro) ───────────────────────────────
def normalize(text: str) -> str:
    """minusculas; remove espacos ao redor de 'h' e ':' (14 h 30 -> 14h30)."""
    t = (text or "").lower()
    t = re.sub(r"\s*h\s*", "h", t)
    t = re.sub(r"\s*:\s*", ":", t)
    return t


def score_fidelity(text: str) -> bool:
    """True se a resposta (normalizada) contem o valor-agulha (14h30 ou 14:30)."""
    t = normalize(text)
    return any(alvo in t for alvo in _ACCEPT_SET)


# ── Sinais exploratorios (§8 — gera hipotese, NAO achado) ─────────────────────
_RUIDO_TERMOS = ("redis", "postgresql", "gin", "websocket", "embedding", "cosseno",
                 "memcached", "jsonb", "normalização", "normalizacao")
_INCERTEZA = ("não tenho certeza", "nao tenho certeza", "não sei", "nao sei",
              "talvez", "parece que", "fragmento", "não há", "nao ha", "não consigo",
              "nao consigo", "não posso", "nao posso")
_HORARIO_RE = re.compile(r"\d{1,2}h\d{0,2}|\d{1,2}:\d{2}")


def extract_signals(text: str) -> dict:
    """Sinais derivados do texto (pos-coleta). Exploratorios."""
    raw = text or ""
    low = raw.lower()
    norm = normalize(raw)
    horarios = _HORARIO_RE.findall(norm)
    horario_errado = any(("14h30" not in h and "14:30" not in h) for h in horarios)
    return {
        "comprimento":        len(raw),
        "menciona_ruido":     any(t in low for t in _RUIDO_TERMOS),
        "marcador_incerteza": any(t in low for t in _INCERTEZA),
        "cita_horario_errado": horario_errado,
        "acerto":             score_fidelity(raw),
    }


# ── Intervalo de confianca (Wilson) ───────────────────────────────────────────
def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / denom
    meio = (z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)) / denom
    return (max(0.0, centro - meio), min(1.0, centro + meio))


# ── Resultado ─────────────────────────────────────────────────────────────────
@dataclass
class CondicaoFidelidade:
    rotulo: str
    formato_id: str
    papel: str
    n: int
    acertos: int
    fidelidade: float
    ci_low: float
    ci_high: float


@dataclass
class ScorerResultado:
    n_registros_total: int = 0
    n_reais: int = 0
    n_dry_run: int = 0
    condicoes: List[CondicaoFidelidade] = field(default_factory=list)
    # veredito
    monotonica_nao_crescente: Optional[bool] = None
    queda_significativa: Optional[bool] = None
    achado_confirmado: Optional[bool] = None
    setup_valido: Optional[bool] = None
    ablacao_fidelidade: Optional[float] = None
    experimento: Optional[str] = None
    # contraste do 003 (comp_3 vs inert_3): conflito isolado do volume?
    inert_fidelidade: Optional[float] = None
    contraste_conflito_isolado: Optional[bool] = None


def score_prontuario(store=None, only_real: bool = True,
                     experimento: Optional[str] = None) -> ScorerResultado:
    """Le o prontuario, separa real/dry-run, filtra por EXPERIMENTO, e computa
    fidelidade por condicao. Se experimento=None, auto-detecta (usa o experimento
    dos registros reais; se houver mais de um, usa o de mais registros e avisa).
    O veredito e especifico do experimento (001 dose inerte; 003 dose competidor
    + contraste comp_3 vs inert_3)."""
    store = store or get_prontuario()
    res = ScorerResultado()

    # 1) le indice -> abre blobs -> separa real/dry-run, guardando o experimento
    registros = []  # (experimento, rotulo, formato_id, papel, respostas)
    for row in store.query_index():
        res.n_registros_total += 1
        blob = store.get_blob(row.get("run_id"))
        if not blob:
            continue
        andaime = blob.get("andaime", {}) or {}
        is_dry = bool(andaime.get("dry_run", False))
        if is_dry:
            res.n_dry_run += 1
            if only_real:
                continue
        else:
            res.n_reais += 1
        registros.append((
            andaime.get("experimento"),
            andaime.get("condicao_rotulo") or blob.get("formato_id", "?"),
            blob.get("formato_id", "?"),
            andaime.get("condicao_papel", ""),
            blob.get("respostas", []) or [],
        ))

    # 1b) auto-deteccao do experimento (se nao especificado)
    if experimento is None:
        from collections import Counter
        cont = Counter(r[0] for r in registros if r[0])
        if cont:
            experimento = cont.most_common(1)[0][0]
            if len(cont) > 1:
                logger.warning("[scorer] prontuario tem >1 experimento %s; pontuando '%s'. "
                               "Limpe o prontuario entre experimentos para dado limpo.",
                               dict(cont), experimento)
    res.experimento = experimento

    # 2) agrupa SO o experimento alvo e computa fidelidade por condicao
    por_condicao: Dict[str, dict] = {}
    for exp, rotulo, fid_id, papel, respostas in registros:
        if experimento is not None and exp != experimento:
            continue
        slot = por_condicao.setdefault(rotulo, {"formato_id": fid_id, "papel": papel, "respostas": []})
        slot["respostas"].extend(respostas)
    for rotulo, slot in por_condicao.items():
        respostas = slot["respostas"]
        n = len(respostas)
        acertos = sum(1 for r in respostas if score_fidelity(r))
        fid = (acertos / n) if n else 0.0
        lo, hi = wilson(acertos, n)
        res.condicoes.append(CondicaoFidelidade(
            rotulo=rotulo, formato_id=slot["formato_id"], papel=slot["papel"],
            n=n, acertos=acertos, fidelidade=fid, ci_low=lo, ci_high=hi))

    # 3) veredito especifico do experimento
    fid_por = {c.rotulo: c for c in res.condicoes}
    if experimento == "003":
        ordem_dose = ["neutra", "comp_1", "comp_2", "comp_3"]
    else:  # 001 (default)
        ordem_dose = ["neutra", "ruido_n3", "ruido_n5", "ruido_n10"]
    dose = [fid_por[r] for r in ordem_dose if r in fid_por]
    if len(dose) >= 2:
        res.monotonica_nao_crescente = all(
            dose[i].fidelidade >= dose[i + 1].fidelidade - 1e-9 for i in range(len(dose) - 1))
        a, b = dose[0], dose[-1]
        res.queda_significativa = a.ci_low > b.ci_high
        res.achado_confirmado = bool(res.monotonica_nao_crescente and res.queda_significativa)
    if "ablacao_retrieval" in fid_por:
        res.ablacao_fidelidade = fid_por["ablacao_retrieval"].fidelidade
        res.setup_valido = res.ablacao_fidelidade <= 0.05
    # contraste do 003: comp_3 < inert_3 com ICs separados -> conflito isolado
    if "comp_3" in fid_por and "inert_3" in fid_por:
        c3, i3 = fid_por["comp_3"], fid_por["inert_3"]
        res.inert_fidelidade = i3.fidelidade
        res.contraste_conflito_isolado = c3.ci_high < i3.ci_low

    return res


def report(res: ScorerResultado) -> None:
    exp = res.experimento or "001"
    print("\n" + "=" * 70)
    print(f"SCORER — Experimento {exp}  (fidelidade = resposta contem 14h30/14:30)")
    print("=" * 70)
    print(f"  registros no prontuario : {res.n_registros_total} "
          f"(reais={res.n_reais} | dry_run={res.n_dry_run})")
    print(f"  --> analise usa SO os reais do experimento {exp}.\n")

    print(f"  {'condicao':<20}{'papel':<26}{'n':<5}{'fidelidade':<12}{'IC95%'}")
    # ordem de condicoes + rotulo do ultimo nivel da dose, por experimento
    if exp == "003":
        ordem = ["neutra", "comp_1", "comp_2", "comp_3", "inert_3", "ablacao_retrieval"]
        ultimo = "comp_3"
    else:
        ordem = ["neutra", "ruido_n3", "ruido_n5", "ruido_n10", "lost_in_middle_fim", "ablacao_retrieval"]
        ultimo = "ruido_n10"
    fid_por = {c.rotulo: c for c in res.condicoes}
    for rot in ordem + [r for r in fid_por if r not in ordem]:
        c = fid_por.get(rot)
        if not c:
            continue
        ci = f"[{c.ci_low:.2f}, {c.ci_high:.2f}]"
        print(f"  {c.rotulo:<20}{c.papel:<26}{c.n:<5}{c.fidelidade*100:>5.1f}% ({c.acertos}/{c.n})  {ci}")

    print("\n  VEREDITO (criterio travado no pré-registro):")
    print(f"    controle negativo (ablacao ~0?) : fidelidade={(res.ablacao_fidelidade or 0)*100:.1f}% "
          f"-> setup {'VALIDO' if res.setup_valido else 'SUSPEITO (investigar!)'}")
    if res.setup_valido is False:
        print("    [ATENCAO] ablacao com fidelidade alta = agulha vazou / metrica quebrada.")
        print("    Nenhum achado e afirmado ate o setup ser validado.")
    else:
        print(f"    dose-resposta monotonica nao-crescente? {res.monotonica_nao_crescente}")
        print(f"    queda neutra->{ultimo} significativa (ICs separados)? {res.queda_significativa}")
        if res.achado_confirmado:
            if exp == "003":
                print("    --> ACHADO PRIMARIO CONFIRMADO: competidores quase-identicos degradam a fidelidade.")
            else:
                print("    --> ACHADO PRIMARIO CONFIRMADO: enterrar a agulha sob ruido degrada a fidelidade.")
        else:
            print("    --> achado primario NAO confirmado pelo criterio. (H0 nao rejeitada,")
            print("        ou queda nao-monotonica, ou ICs sobrepostos.) Dado valido, efeito nao provado.")
        # contraste exclusivo do 003: o conflito esta isolado do volume?
        if exp == "003" and res.inert_fidelidade is not None:
            print(f"\n    CONTRASTE comp_3 vs inert_3 (mesmo volume, conteudo diferente):")
            c3 = fid_por.get("comp_3"); i3 = fid_por.get("inert_3")
            if c3 and i3:
                print(f"      comp_3 (3 competidores) = {c3.fidelidade*100:.1f}%  [{c3.ci_low:.2f},{c3.ci_high:.2f}]")
                print(f"      inert_3 (3 inertes)     = {i3.fidelidade*100:.1f}%  [{i3.ci_low:.2f},{i3.ci_high:.2f}]")
            if res.contraste_conflito_isolado:
                print("      --> comp_3 < inert_3 com ICs separados: o CONFLITO (nao o volume) e a causa.")
            else:
                print("      --> ICs se tocam: nao da pra isolar o conflito do volume neste n. (Dado valido.)")
    print("=" * 70)
    print("  (Sinais exploratorios do §8 — qual competidor venceu etc. — sao analise separada.)")


# ── Precedencia geral (usada por sujeitos/edp/analise/analise_006b.py e
#    analise_007.py — decisao tem precedencia sobre marcador) ────────────────
def valor_concluido(texto: str, valores_fn) -> Optional[str]:
    """PRECEDENCIA GERAL (corrige o bug 004/007): retorna o VALOR CONCLUIDO da
    resposta, nao apenas 'um valor presente'. Decisao tem precedencia sobre marcador.
    `valores_fn(texto)` -> set dos valores presentes (detector do experimento).
    - 0 valores presentes -> None (exposição/sem decisao).
    - 1 valor presente -> esse valor (decidiu).
    - 2+ valores -> o valor da ULTIMA frase que contem valor (a conclusao costuma vir
      no fim). Se a ultima frase com valor tiver mais de um -> None (ambiguo).
    Impede 'ha conflito, mas e X' de ser lido como exposição/sequestro (bug 004/007).
    """
    presentes = valores_fn(texto)
    if not presentes:
        return None
    if len(presentes) == 1:
        return next(iter(presentes))
    for fr in reversed([f for f in re.split(r"[.!?\n]+", texto or "") if f.strip()]):
        vs = valores_fn(fr)
        if vs:
            return next(iter(vs)) if len(vs) == 1 else None
    return None
