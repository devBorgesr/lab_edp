"""
sujeitos.edp.analise.analise_006 — Experimento 006 (câmara de eco: maioria vs
recência): análise pós-coleta dedicada.

Movido byte-a-byte de bancada/scorer.py na FASE B6. `from . import exp006`
resolvia dentro de bancada/ (nunca existiu ali) — vira import de módulo, no
topo, sujeito importando sujeito.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bancada.prontuario import get_prontuario
from bancada.scorer import wilson

from .analise_004 import CamadaAutoridade
from ..experimentos import exp006


@dataclass
class Eco006:
    n_reais: int = 0
    n_dry_run: int = 0
    n_registros_total: int = 0
    baselines: Dict[str, CamadaAutoridade] = field(default_factory=dict)  # unanimes (legibilidade)
    conflito_total: int = 0
    conflito: List[CamadaAutoridade] = field(default_factory=list)        # maioria/recencia/nenhuma
    empate_total: int = 0
    empate: List[CamadaAutoridade] = field(default_factory=list)          # segue_recente/segue_outro/nenhuma
    ablacao_fracao: Optional[float] = None
    conflito_vencedor: Optional[str] = None
    conflito_estavel: Optional[bool] = None
    recusa_dominante_conflito: Optional[bool] = None
    setup_valido: Optional[bool] = None


def _coleta_006(store, only_real):
    por_rotulo: Dict[str, list] = {}
    tot = dry = reais = 0
    for row in store.query_index():
        tot += 1
        blob = store.get_blob(row.get("run_id"))
        if not blob:
            continue
        a = blob.get("andaime", {}) or {}
        if a.get("experimento") != "006":
            continue
        if bool(a.get("dry_run", False)):
            dry += 1
            if only_real:
                continue
        else:
            reais += 1
        rot = a.get("condicao_rotulo") or blob.get("formato_id", "?")
        por_rotulo.setdefault(rot, []).extend(blob.get("respostas", []) or [])
    return por_rotulo, tot, dry, reais


def score_eco_006(store=None, only_real: bool = True) -> Eco006:
    """Analise do Exp 006: legibilidade (unanimes), conflito maioria-vs-recencia
    (agregado, contrabalanceado), e a medida do empate (poder da recencia quando a
    maioria nao e esmagadora)."""
    store = store or get_prontuario()
    res = Eco006()
    por_rotulo, res.n_registros_total, res.n_dry_run, res.n_reais = _coleta_006(store, only_real)

    # baselines (unanimes): legibilidade
    for rot in ("unanime_14h30", "unanime_15h"):
        resp = por_rotulo.get(rot, [])
        mai, _rec, _t = exp006.meta_da_condicao(rot)
        n = len(resp)
        k = sum(1 for r in resp if mai in exp006.valores_na_resposta(r))
        lo, hi = wilson(k, n)
        res.baselines[rot] = CamadaAutoridade(rot.replace("unanime_", ""), k, (k/n if n else 0.0), lo, hi, n)

    # conflito (maioria_recente nao entra aqui; sao maioria+recencia concordando):
    # so as condicoes 'conflito' (maioria != recencia)
    cmaioria = crecencia = cnenhuma = 0
    for rot in ("conflito_maioriaA", "conflito_maioriaB"):
        mai, rec, _ = exp006.meta_da_condicao(rot)
        for r in por_rotulo.get(rot, []):
            res.conflito_total += 1
            v = exp006.valor_unico(r)
            if v == mai:
                cmaioria += 1
            elif v == rec:
                crecencia += 1
            else:
                cnenhuma += 1
    Nc = res.conflito_total
    for nome, k in (("maioria", cmaioria), ("recencia", crecencia), ("nenhuma", cnenhuma)):
        lo, hi = wilson(k, Nc)
        res.conflito.append(CamadaAutoridade(nome, k, (k/Nc if Nc else 0.0), lo, hi, Nc))

    # empate: segue o desempate recente vs o outro vs nenhuma
    erec = eoutro = enenhuma = 0
    for rot in ("empate_recente_A", "empate_recente_B"):
        _mai, rec, _ = exp006.meta_da_condicao(rot)
        outro = "15h" if rec == "14h30" else "14h30"
        for r in por_rotulo.get(rot, []):
            res.empate_total += 1
            v = exp006.valor_unico(r)
            if v == rec:
                erec += 1
            elif v == outro:
                eoutro += 1
            else:
                enenhuma += 1
    Ne = res.empate_total
    for nome, k in (("segue_recente", erec), ("segue_outro", eoutro), ("nenhuma", enenhuma)):
        lo, hi = wilson(k, Ne)
        res.empate.append(CamadaAutoridade(nome, k, (k/Ne if Ne else 0.0), lo, hi, Ne))

    # ablacao
    abl = por_rotulo.get("ablacao", [])
    if abl:
        res.ablacao_fracao = sum(1 for r in abl if exp006.valores_na_resposta(r)) / len(abl)

    # veredito do conflito (nenhuma compete, como no 004)
    if Nc > 0:
        top = max(res.conflito, key=lambda c: c.fracao)
        outras = [c for c in res.conflito if c.camada != top.camada]
        separado = bool(outras) and all(top.ci_low > o.ci_high for o in outras)
        res.recusa_dominante_conflito = (top.camada == "nenhuma")
        res.conflito_vencedor = top.camada if (top.camada != "nenhuma" and separado) else None
        res.conflito_estavel = (top.camada != "nenhuma" and separado)
    leg_ok = all(b.fracao >= 0.7 for b in res.baselines.values()) if res.baselines else False
    abl_ok = (res.ablacao_fracao is None) or (res.ablacao_fracao <= 0.10)
    res.setup_valido = leg_ok and abl_ok
    return res


def _tab(linhas, total):
    for c in sorted(linhas, key=lambda x: -x.fracao):
        print(f"    {c.camada:<16}{c.fracao*100:>5.1f}% ({c.acertos}/{total})  [{c.ci_low:.2f}, {c.ci_high:.2f}]")


def report_006(res: Eco006) -> None:
    print("\n" + "=" * 70)
    print("SCORER — Experimento 006  (câmara de eco: maioria vs recência)")
    print("=" * 70)
    print(f"  registros: {res.n_registros_total} (reais={res.n_reais} | dry_run={res.n_dry_run})\n")
    print("  LEGIBILIDADE (unânime — deve recuperar ~alto, sem conflito):")
    for rot in ("unanime_14h30", "unanime_15h"):
        b = res.baselines.get(rot)
        if b:
            print(f"    {b.camada:<10}{b.fracao*100:>5.1f}% ({b.acertos}/{b.n})  [{b.ci_low:.2f}, {b.ci_high:.2f}]")
    print(f"\n  CONFLITO maioria(4×) vs recência(1×, mais nova) — agregado n={res.conflito_total}:")
    _tab(res.conflito, res.conflito_total)
    print(f"\n  EMPATE 2×2 + desempate recente — agregado n={res.empate_total}:")
    _tab(res.empate, res.empate_total)
    print(f"\n  VEREDITO:")
    av = res.ablacao_fracao
    print(f"    controle negativo (ablacao casa valor?): {(av*100 if av is not None else 0):.1f}% "
          f"-> setup {'VALIDO' if res.setup_valido else 'SUSPEITO'}")
    if res.setup_valido is False:
        print("    [ATENCAO] unanime ilegivel ou ablacao alta — achado nao afirmado.")
    elif res.recusa_dominante_conflito:
        print(f"    --> CONFLITO: 'nenhuma' domina ({[c.fracao for c in res.conflito if c.camada=='nenhuma'][0]*100:.1f}%).")
        print(f"        Como no 004: o modelo EXPOE o conflito em vez de arbitrar entre memorias validas.")
        print(f"        Sinal forte: a governanca precisa existir ANTES da janela. (Audite: --audit-exp 006)")
    elif res.conflito_estavel:
        print(f"    --> CONFLITO: '{res.conflito_vencedor}' vence (IC separado). "
              f"{'VOLUME manda.' if res.conflito_vencedor=='maioria' else 'ATUALIDADE manda.'}")
    else:
        print(f"    --> CONFLITO: sem dominancia estavel (ICs se tocam).")
    # empate: poder da recencia
    er = next((c for c in res.empate if c.camada == "segue_recente"), None)
    if er:
        print(f"    empate 2×2: segue o desempate recente em {er.fracao*100:.1f}% [{er.ci_low:.2f},{er.ci_high:.2f}]"
              f" -> {'recencia inclina empates' if er.fracao>0.5 else 'recencia NAO domina nem no empate'}")
    print("=" * 70)


def audit_006(store=None, n_por_grupo: int = 6):
    """Le as respostas do CONFLITO (maioria!=recencia) agrupadas por categoria
    reportada (maioria/recencia/nenhuma). Texto integral, para ver a exposicao."""
    store = store or get_prontuario()
    grupos = {"maioria": [], "recencia": [], "nenhuma": []}
    por_rotulo, *_ = _coleta_006(store, only_real=True)
    for rot in ("conflito_maioriaA", "conflito_maioriaB"):
        mai, rec, _ = exp006.meta_da_condicao(rot)
        for r in por_rotulo.get(rot, []):
            v = exp006.valor_unico(r)
            cat = "maioria" if v == mai else ("recencia" if v == rec else "nenhuma")
            grupos[cat].append(r)
    print("\n" + "=" * 70)
    print("AUDITORIA — Exp 006, respostas do conflito maioria-vs-recência (texto integral)")
    print("=" * 70)
    total = sum(len(v) for v in grupos.values())
    for cat in ("nenhuma", "maioria", "recencia"):
        lst = grupos[cat]
        frac = (len(lst) / total * 100) if total else 0
        print(f"\n── '{cat}': {len(lst)}/{total} ({frac:.1f}%) — amostra de ate {n_por_grupo}:")
        for i, r in enumerate(lst[:n_por_grupo], 1):
            print(f"  ({i}) {(r or '').strip()}")
    print("\n" + "=" * 70)
    return grupos
