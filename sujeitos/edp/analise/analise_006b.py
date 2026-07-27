"""
sujeitos.edp.analise.analise_006b — Experimento 006b (data vs posição —
desacoplamento causal): análise pós-coleta dedicada, com PRECEDÊNCIA
(corrige bug 004/007 — ver bancada.scorer.valor_concluido).

Movido byte-a-byte de bancada/scorer.py na FASE B6. `from . import exp006b`
resolvia dentro de bancada/ (nunca existiu ali) — vira import de módulo, no
topo, sujeito importando sujeito.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bancada.prontuario import get_prontuario
from bancada.scorer import valor_concluido, wilson

from .analise_004 import CamadaAutoridade
from ..experimentos import exp006b

# Marcadores de H4 PRE-REGISTRADOS (confirmam exposição; nao substituem a precedencia).
_H4_MARCADORES = (
    "inconsistente", "não consigo determinar", "nao consigo determinar",
    "conflito cronológico", "conflito cronologico", "datas fora de ordem",
    "não há trajetória clara", "nao ha trajetoria clara",
)


def valor_concluido_006b(texto: str) -> Optional[str]:
    """Precedencia do 006b (wrapper sobre valor_concluido com o detector do 006b)."""
    return valor_concluido(texto, exp006b.valores_na_resposta)


def _tem_marcador_h4(texto: str) -> bool:
    t = (texto or "").lower()
    return any(m in t for m in _H4_MARCADORES)


@dataclass
class CondDP:
    rotulo: str
    tipo: str
    n: int
    k_data_nova: int       # concluiu o valor da data mais nova (H1-consistente)
    k_ultima: int          # concluiu o valor da ultima posicao (H2-consistente)
    k_exposicao: int       # nao concluiu valor unico (H4)
    k_marcador_h4: int      # subconjunto da exposicao que cita duvida cronologica


@dataclass
class DataPosicao006b:
    n_reais: int = 0
    n_dry_run: int = 0
    n_registros_total: int = 0
    por_condicao: List[CondDP] = field(default_factory=list)
    # nucleo agregado (desacopladas 2+3, por papel — contrabalanceado por valor)
    nucleo: List[CamadaAutoridade] = field(default_factory=list)   # H1(data_nova)/H2(ultima)/exposição
    # escala de exposição piso-teto
    exposicao_teto: Optional[float] = None
    exposicao_nucleo: Optional[float] = None
    exposicao_piso: Optional[float] = None
    veredito: Optional[str] = None          # "H1 (data vence)" / "H2 (posicao vence)" / "H3" / "exposição" / "inconclusivo"
    estavel: Optional[bool] = None
    setup_valido: Optional[bool] = None


def _classifica_cond_006b(rot, resp, meta) -> CondDP:
    vdn, vup, tipo = meta
    kdn = kup = kexp = kmark = 0
    for r in resp:
        vc = valor_concluido_006b(r)
        if vc is None:
            kexp += 1
            if _tem_marcador_h4(r):
                kmark += 1
        elif vc == vdn:
            kdn += 1
        elif vc == vup:
            kup += 1
        else:
            kexp += 1  # concluiu um valor que nao e nenhum dos esperados (nao deve ocorrer com 2 valores)
    return CondDP(rot, tipo, len(resp), kdn, kup, kexp, kmark)


def score_data_posicao_006b(store=None, only_real: bool = True) -> DataPosicao006b:
    store = store or get_prontuario()
    res = DataPosicao006b()
    por_rotulo: Dict[str, list] = {}
    for row in store.query_index():
        res.n_registros_total += 1
        blob = store.get_blob(row.get("run_id"))
        if not blob:
            continue
        a = blob.get("andaime", {}) or {}
        if a.get("experimento") != "006b":
            continue
        if bool(a.get("dry_run", False)):
            res.n_dry_run += 1
            if only_real:
                continue
        else:
            res.n_reais += 1
        rot = a.get("condicao_rotulo") or blob.get("formato_id", "?")
        por_rotulo.setdefault(rot, []).extend(blob.get("respostas", []) or [])

    for rot in ("acoplada", "desacoplada_B", "desacoplada_A", "sem_trajetoria"):
        resp = por_rotulo.get(rot, [])
        if not resp:
            continue
        res.por_condicao.append(_classifica_cond_006b(rot, resp, exp006b.meta_da_condicao(rot)))
    porc = {c.rotulo: c for c in res.por_condicao}

    # nucleo agregado: H1 (valor-da-data-nova) vs H2 (valor-da-ultima-posicao) vs exposição
    h1 = sum(porc[r].k_data_nova for r in ("desacoplada_B", "desacoplada_A") if r in porc)
    h2 = sum(porc[r].k_ultima    for r in ("desacoplada_B", "desacoplada_A") if r in porc)
    he = sum(porc[r].k_exposicao for r in ("desacoplada_B", "desacoplada_A") if r in porc)
    N = h1 + h2 + he
    for nome, k in (("data_nova (H1)", h1), ("ultima_posicao (H2)", h2), ("exposição (H4)", he)):
        lo, hi = wilson(k, N)
        res.nucleo.append(CamadaAutoridade(nome, k, (k/N if N else 0.0), lo, hi, N))

    # escala de exposição piso-teto
    if "acoplada" in porc:
        c = porc["acoplada"]; res.exposicao_teto = c.k_exposicao / c.n if c.n else None
    if N:
        res.exposicao_nucleo = he / N
    if "sem_trajetoria" in porc:
        c = porc["sem_trajetoria"]; res.exposicao_piso = c.k_exposicao / c.n if c.n else None

    # veredito (precedencia + IC separado + limiar H3)
    if N > 0:
        cats = res.nucleo
        top = max(cats, key=lambda c: c.fracao)
        outras = [c for c in cats if c.camada != top.camada]
        separado = bool(outras) and all(top.ci_low > o.ci_high for o in outras)
        h1f = cats[0].fracao; h2f = cats[1].fracao; h4f = cats[2].fracao
        if separado and top.camada.startswith("data_nova"):
            res.veredito, res.estavel = "H1 (data vence)", True
        elif separado and top.camada.startswith("ultima_posicao"):
            res.veredito, res.estavel = "H2 (posicao vence) — SISMICO", True
        elif separado and top.camada.startswith("exposição"):
            res.veredito, res.estavel = "exposição domina (H4)", True
        elif h1f >= 0.25 and h2f >= 0.25 and h4f < 0.20:
            res.veredito, res.estavel = "H3 (mistura)", False
        else:
            res.veredito, res.estavel = "inconclusivo (sem dominancia, sem limiar H3)", False

    # validade: teto recupera o valor-acordado alto, exposição do teto baixa
    teto = porc.get("acoplada")
    leg_ok = (teto is not None and (teto.k_data_nova / teto.n) >= 0.7 and (teto.k_exposicao / teto.n) <= 0.20)
    res.setup_valido = leg_ok
    return res


def report_006b(res: DataPosicao006b) -> None:
    print("\n" + "=" * 70)
    print("SCORER — Experimento 006b  (data vs posição — desacoplamento causal)")
    print("=" * 70)
    print(f"  registros: {res.n_registros_total} (reais={res.n_reais} | dry_run={res.n_dry_run})\n")
    print(f"  {'condicao':<16}{'tipo':<13}{'n':<4}{'data-nova':<11}{'ult-posicao':<13}{'exposição':<11}{'(cita dúvida)'}")
    for c in res.por_condicao:
        dn = f"{c.k_data_nova/c.n*100:.0f}%" if c.n else "-"
        up = f"{c.k_ultima/c.n*100:.0f}%" if c.n else "-"
        ex = f"{c.k_exposicao/c.n*100:.0f}%" if c.n else "-"
        print(f"  {c.rotulo:<16}{c.tipo:<13}{c.n:<4}{dn:<11}{up:<13}{ex:<11}{c.k_marcador_h4}/{c.k_exposicao}")
    print(f"\n  NÚCLEO agregado (desacopladas 2+3, por papel, contrabalanceado por valor):")
    for c in res.nucleo:
        print(f"    {c.camada:<22}{c.fracao*100:>5.1f}% ({c.acertos}/{c.n})  [{c.ci_low:.2f}, {c.ci_high:.2f}]")
    print(f"\n  ESCALA de exposição (âncora relativa):")
    et = res.exposicao_teto; en = res.exposicao_nucleo; ep = res.exposicao_piso
    print(f"    teto (acoplada): {et*100 if et is not None else 0:.0f}%  <  "
          f"desacoplada: {en*100 if en is not None else 0:.0f}%  <  "
          f"piso (sem_trajetoria): {ep*100 if ep is not None else 0:.0f}%")
    print(f"\n  VEREDITO:")
    print(f"    setup {'VALIDO' if res.setup_valido else 'SUSPEITO (teto deveria recuperar o valor-acordado!)'}")
    if res.setup_valido:
        print(f"    --> {res.veredito}")
        if res.veredito and res.veredito.startswith("H2"):
            print(f"        ATENCAO: posicao vencendo data obrigaria reinterpretar o 006 E parte da tese do 007.")
        if en is not None and et is not None:
            if ep is not None and en >= (et + ep) / 2:
                print(f"        exposição da desacoplada mais perto do PISO: embaralhamento corrói a decidibilidade.")
            else:
                print(f"        exposição da desacoplada mais perto do TETO: embaralhamento quase nao afetou.")
    print(f"    (Confirme a precedencia lendo o texto: --audit-exp 006b)")
    print("=" * 70)


def audit_006b(store=None, n_por_grupo: int = 6):
    """Le as respostas das DESACOPLADAS agrupadas pela classificacao (data-nova/
    ultima-posicao/exposição). Texto integral — para CONFIRMAR que a precedencia
    (decisao antes de marcador) classificou certo, e nao repetiu o bug 004/007."""
    store = store or get_prontuario()
    grupos = {"data_nova (H1)": [], "ultima_posicao (H2)": [], "exposição (H4)": []}
    por_rotulo: Dict[str, list] = {}
    for row in store.query_index():
        blob = store.get_blob(row.get("run_id"))
        if not blob:
            continue
        a = blob.get("andaime", {}) or {}
        if a.get("experimento") != "006b" or a.get("dry_run"):
            continue
        rot = a.get("condicao_rotulo") or ""
        if exp006b.meta_da_condicao(rot)[2] != "desacoplada":
            continue
        por_rotulo.setdefault(rot, []).extend(blob.get("respostas", []) or [])
    for rot, resp in por_rotulo.items():
        vdn, vup, _ = exp006b.meta_da_condicao(rot)
        for r in resp:
            vc = valor_concluido_006b(r)
            cat = ("data_nova (H1)" if vc == vdn else "ultima_posicao (H2)" if vc == vup else "exposição (H4)")
            grupos[cat].append(r)
    print("\n" + "=" * 70)
    print("AUDITORIA — Exp 006b, respostas das DESACOPLADAS (texto integral)")
    print("=" * 70)
    total = sum(len(v) for v in grupos.values())
    for cat in ("exposição (H4)", "data_nova (H1)", "ultima_posicao (H2)"):
        lst = grupos[cat]
        frac = (len(lst) / total * 100) if total else 0
        print(f"\n── '{cat}': {len(lst)}/{total} ({frac:.1f}%) — amostra de ate {n_por_grupo}:")
        for i, r in enumerate(lst[:n_por_grupo], 1):
            print(f"  ({i}) {(r or '').strip()}")
    print("\n" + "=" * 70)
    return grupos
