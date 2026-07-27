"""
sujeitos.edp.analise.analise_004 — Experimento 004 (autoridade entre camadas):
análise pós-coleta dedicada.

Movido byte-a-byte de bancada/scorer.py na FASE B6 (fronteira bancada/sujeito
virou invariante executável em tests/test_fronteira.py — ver B5). O único
ajuste é o import: o `from . import exp004` original resolvia dentro de
bancada/ (onde exp004 nunca existiu — ImportError garantido); aqui vira
import direto de sujeito para sujeito, no topo do módulo.

`CamadaAutoridade` também mora aqui (não estava listada na T2, mas é o tipo
de `Autoridade004.baselines`/`.por_camada`) — é reaproveitada por
analise_006.py e analise_006b.py, mesmo padrão de exp006/exp006b
reaproveitando exp004.valor_unico/valores_na_resposta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bancada.prontuario import get_prontuario
from bancada.scorer import wilson

from ..experimentos import exp004


@dataclass
class CamadaAutoridade:
    camada: str
    acertos: int
    fracao: float
    ci_low: float
    ci_high: float
    n: int = 0


@dataclass
class Autoridade004:
    n_reais: int = 0
    n_dry_run: int = 0
    n_registros_total: int = 0
    baselines: Dict[str, CamadaAutoridade] = field(default_factory=dict)   # legibilidade por camada
    conflito_total: int = 0
    por_camada: List[CamadaAutoridade] = field(default_factory=list)       # quem venceu o conflito
    nenhuma_fracao: float = 0.0
    nenhuma_acertos: int = 0
    ablacao_fracao: Optional[float] = None
    camada_vencedora: Optional[str] = None
    hierarquia_estavel: Optional[bool] = None
    recusa_dominante: Optional[bool] = None
    setup_valido: Optional[bool] = None


def score_autoridade_004(store=None, only_real: bool = True) -> Autoridade004:
    """Análise do Exp 004: legibilidade por camada (baselines), e — no conflito
    3-vias agregado e contrabalanceado — qual CAMADA o modelo reportou."""
    store = store or get_prontuario()
    res = Autoridade004()

    por_rotulo: Dict[str, list] = {}
    for row in store.query_index():
        res.n_registros_total += 1
        blob = store.get_blob(row.get("run_id"))
        if not blob:
            continue
        andaime = blob.get("andaime", {}) or {}
        if andaime.get("experimento") != "004":
            continue
        if bool(andaime.get("dry_run", False)):
            res.n_dry_run += 1
            if only_real:
                continue
        else:
            res.n_reais += 1
        rotulo = andaime.get("condicao_rotulo") or blob.get("formato_id", "?")
        por_rotulo.setdefault(rotulo, []).extend(blob.get("respostas", []) or [])

    # baselines: fração que recupera o valor daquela camada (legibilidade)
    for rot in ("base_system", "base_retrieval", "base_recent"):
        resp = por_rotulo.get(rot, [])
        mapa = exp004.mapa_da_condicao(rot)
        valor = next(iter(mapa.values()), None)
        n = len(resp)
        k = sum(1 for r in resp if valor in exp004.valores_na_resposta(r))
        lo, hi = wilson(k, n)
        res.baselines[rot] = CamadaAutoridade(rot.replace("base_", ""), k, (k/n if n else 0.0), lo, hi, n)

    # conflito agregado (A/B/C): atribui cada resposta à camada cujo valor reportou
    tally = {"system": 0, "retrieval": 0, "recent": 0}
    nenhuma = 0
    for rot in ("conflito_A", "conflito_B", "conflito_C"):
        mapa = exp004.mapa_da_condicao(rot)
        for r in por_rotulo.get(rot, []):
            res.conflito_total += 1
            cam = exp004.camada_do_valor(mapa, exp004.valor_unico(r))
            if cam in tally:
                tally[cam] += 1
            else:
                nenhuma += 1
    N = res.conflito_total
    for cam in ("system", "retrieval", "recent"):
        k = tally[cam]
        lo, hi = wilson(k, N)
        res.por_camada.append(CamadaAutoridade(cam, k, (k/N if N else 0.0), lo, hi, N))
    res.nenhuma_acertos = nenhuma
    res.nenhuma_fracao = (nenhuma / N) if N else 0.0

    # ablação: fração que casa QUALQUER valor (deve ser ~0)
    abl = por_rotulo.get("ablacao_total", [])
    if abl:
        casou = sum(1 for r in abl if exp004.valores_na_resposta(r))
        res.ablacao_fracao = casou / len(abl)

    # veredito — "nenhuma" (recusa/sem-valor) COMPETE como categoria.
    # So ha camada vencedora se uma CAMADA for a maior categoria E seu IC estiver
    # separado de TODAS as outras (incluindo nenhuma). Senao: ou recusa domina, ou empate.
    if N > 0:
        nlo, nhi = wilson(nenhuma, N)
        nenhuma_cam = CamadaAutoridade("nenhuma", nenhuma, res.nenhuma_fracao, nlo, nhi, N)
        categorias = list(res.por_camada) + [nenhuma_cam]
        top = max(categorias, key=lambda c: c.fracao)
        outras = [c for c in categorias if c.camada != top.camada]
        separado = bool(outras) and all(top.ci_low > o.ci_high for o in outras)
        res.recusa_dominante = (top.camada == "nenhuma")
        if top.camada != "nenhuma" and separado:
            res.camada_vencedora = top.camada
            res.hierarquia_estavel = True
        else:
            res.camada_vencedora = None
            res.hierarquia_estavel = False
    leg_ok = all(b.fracao >= 0.7 for b in res.baselines.values()) if res.baselines else False
    abl_ok = (res.ablacao_fracao is None) or (res.ablacao_fracao <= 0.10)
    res.setup_valido = leg_ok and abl_ok
    return res


def report_004(res: Autoridade004) -> None:
    print("\n" + "=" * 70)
    print("SCORER — Experimento 004  (autoridade entre camadas)")
    print("=" * 70)
    print(f"  registros: {res.n_registros_total} (reais={res.n_reais} | dry_run={res.n_dry_run})\n")

    print("  LEGIBILIDADE (fato sozinho em cada camada — deve recuperar ~alto):")
    for rot in ("base_system", "base_retrieval", "base_recent"):
        b = res.baselines.get(rot)
        if b:
            print(f"    {b.camada:<12}{b.fracao*100:>5.1f}% ({b.acertos}/{b.n})  [{b.ci_low:.2f}, {b.ci_high:.2f}]")
    print(f"\n  CONFLITO 3-VIAS (contrabalanceado, agregado — n={res.conflito_total} respostas):")
    print("  qual camada o modelo REPORTOU?")
    for c in sorted(res.por_camada, key=lambda x: -x.fracao):
        print(f"    {c.camada:<12}{c.fracao*100:>5.1f}% ({c.acertos}/{res.conflito_total})  [{c.ci_low:.2f}, {c.ci_high:.2f}]")
    print(f"    {'(nenhuma/ambíguo)':<12}{res.nenhuma_fracao*100:>5.1f}% ({res.nenhuma_acertos}/{res.conflito_total})")

    print(f"\n  VEREDITO:")
    av = res.ablacao_fracao
    print(f"    controle negativo (ablacao casa algum valor?): {(av*100 if av is not None else 0):.1f}% "
          f"-> setup {'VALIDO' if res.setup_valido else 'SUSPEITO (investigar legibilidade/ablacao!)'}")
    if res.setup_valido is False:
        print("    [ATENCAO] baseline ilegível ou ablacao alta — uma camada pode 'perder' por")
        print("    nao ter sido lida, nao por perder a disputa. Achado nao afirmado.")
    elif res.recusa_dominante:
        print(f"    --> CATEGORIA DOMINANTE: 'nenhuma' ({res.nenhuma_fracao*100:.1f}%). O modelo NAO")
        print(f"        escolhe uma camada — na maioria das respostas nao reporta nenhum dos 3 valores.")
        print(f"        Provavel sinalizacao de conflito (respostas longas/variadas). NAO ha vencedor")
        print(f"        de camada. CONFIRME lendo as respostas: --audit-exp 004")
    elif res.hierarquia_estavel:
        print(f"    --> HIERARQUIA ESTAVEL: '{res.camada_vencedora}' vence (IC separado de TODAS, incl. nenhuma).")
        print(f"        O EDP deve por a informacao autoritativa nessa camada.")
    else:
        print(f"    --> SEM dominancia estavel: nenhuma categoria tem IC separado das outras. (Dado valido.)")
        print(f"        O EDP NAO pode contar com uma camada para ganhar um conflito.")
    print("=" * 70)


def audit_004(store=None, n_por_grupo: int = 6):
    """Le o prontuario (exp 004, reais) e mostra uma AMOSTRA das respostas do
    conflito 3-vias, agrupadas por categoria reportada (system/retrieval/recent/
    nenhuma). Para VER se a categoria 'nenhuma' e sinalizacao de conflito ou outra
    coisa — o achado primario do 004 depende disto. Texto integral, sem truncar."""
    store = store or get_prontuario()
    grupos = {"system": [], "retrieval": [], "recent": [], "nenhuma": []}
    for row in store.query_index():
        blob = store.get_blob(row.get("run_id"))
        if not blob:
            continue
        a = blob.get("andaime", {}) or {}
        if a.get("experimento") != "004" or a.get("dry_run"):
            continue
        rot = a.get("condicao_rotulo") or ""
        if not rot.startswith("conflito"):
            continue
        mapa = exp004.mapa_da_condicao(rot)
        for r in blob.get("respostas", []) or []:
            cam = exp004.camada_do_valor(mapa, exp004.valor_unico(r)) or "nenhuma"
            grupos[cam].append(r)
    print("\n" + "=" * 70)
    print("AUDITORIA — Exp 004, respostas do conflito 3-vias (texto integral)")
    print("=" * 70)
    total = sum(len(v) for v in grupos.values())
    for cam in ("nenhuma", "system", "retrieval", "recent"):
        lst = grupos[cam]
        frac = (len(lst) / total * 100) if total else 0
        print(f"\n── categoria '{cam}': {len(lst)}/{total} ({frac:.1f}%) — amostra de ate {n_por_grupo}:")
        for i, r in enumerate(lst[:n_por_grupo], 1):
            print(f"  ({i}) {(r or '').strip()}")
    print("\n" + "=" * 70)
    return grupos
