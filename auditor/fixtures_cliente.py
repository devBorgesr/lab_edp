"""
Clientes externos simulados. DADOS em disco, nao codigo interno.

A diferenca importa: uma fixture que e classe Python do proprio pacote testa o
codigo contra si mesmo. Estas ficam em `fixtures/customer_*/` como corpus.json,
queries.json e config.json — do jeito que material de cliente chega — e o
adaptador as le sem saber como foram geradas.

O EDP NAO e usado aqui. Ele e o nosso sistema; usa-lo como cliente externo
seria medir a integracao contra o unico sistema cuja integracao ja existe.

    customer_a   retriever normal, score de similaridade
    customer_b   com duplicacao entre camadas (o defeito que sabemos existir)
    customer_c   score invalido: distancia crua, sem conversao declarada
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .adaptadores.referencia import AdaptadorDeReferencia, de_distancia

# NAO ha raiz default apontando para o laboratorio. `gera_fixtures` exige
# destino explicito: um pacote instalado em outra maquina nao pode depender de
# `../fixtures` existir, e um default silencioso esconde essa dependencia ate
# o dia em que alguem instala de verdade.

TEMAS = ["indexacao de banco", "acustica de sala", "arquitetura de servicos",
         "politica de retencao", "modelos de embedding", "custo de nuvem",
         "observabilidade", "seguranca de api"]


def _h(t: str) -> int:
    """Hash ESTAVEL entre processos — `hash()` do Python nao e."""
    return int(hashlib.sha256(t.encode("utf-8")).hexdigest()[:8], 16)


def gera_fixtures(raiz: Path) -> dict[str, Path]:
    """Materializa os tres clientes em disco. Deterministico."""
    raiz = Path(raiz)
    perfis = {
        "customer_a": {"n_docs": 220, "duplicacao": 0.0,  "metrica": "similaridade"},
        "customer_b": {"n_docs": 220, "duplicacao": 0.55, "metrica": "similaridade"},
        "customer_c": {"n_docs": 220, "duplicacao": 0.0,  "metrica": "distancia_crua"},
    }
    saida = {}
    for nome, cfg in perfis.items():
        d = raiz / nome
        d.mkdir(parents=True, exist_ok=True)
        corpus = {
            f"{nome[-1]}-{i:04d}":
            f"{TEMAS[i % len(TEMAS)]}: nota {i}, detalhe {i * 13 % 101}."
            for i in range(cfg["n_docs"])
        }
        queries = [{"id": f"{nome[-1]}q{i:03d}",
                    "query": f"como resolver {TEMAS[i % len(TEMAS)]} no caso {i}?",
                    "dominio": TEMAS[i % len(TEMAS)]} for i in range(40)]
        (d / "corpus.json").write_text(json.dumps(corpus, ensure_ascii=False,
                                                  indent=1), encoding="utf-8")
        (d / "queries.json").write_text(json.dumps({"queries": queries},
                                                   ensure_ascii=False, indent=1),
                                        encoding="utf-8")
        (d / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
        saida[nome] = d
    return saida


def constroi_cliente(entrada: dict):
    """
    Le a pasta do cliente e devolve um `SistemaAuditavel`.

    O `customer_c` NAO converte o score de proposito: e o caso em que o cliente
    entrega distancia crua e o servico precisa recusar em vez de adivinhar.
    """
    d = Path(entrada["snapshot"])
    cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
    corpus = json.loads((d / "corpus.json").read_text(encoding="utf-8"))
    ids = list(corpus)
    dup = float(cfg.get("duplicacao", 0.0))
    distancia = cfg.get("metrica") == "distancia_crua"

    def buscar(query: str, top_k: int):
        semente = _h(query)
        ordem = sorted(ids, key=lambda x: (semente ^ _h(x)) % 100003)
        base = ordem[:max(1, int(top_k * (1 - dup)))]
        slots = [base[i % len(base)] for i in range(top_k)]
        if distancia:
            # distancia CRESCENTE, primeira = 0.0 — como um indice L2 devolve
            return [(x, float(i) * 0.37) for i, x in enumerate(slots)]
        return [(x, 0.94 - i * 0.011) for i, x in enumerate(slots)]

    op = entrada.get("options") or {}
    converte = de_distancia if (distancia and op.get("converter_score")) else None
    # SEM `snapshot=`: o adaptador cria diretorio proprio. Passar `d/"_snapshot"`
    # escrevia dentro da pasta do cliente e fazia duas auditorias concorrentes
    # do mesmo corpus corromperem uma a outra.
    return AdaptadorDeReferencia(
        corpus, buscar,
        converte_score=converte,
        nota_da_conversao=("distancia L2 -> 1/(1+d), monotona decrescente"
                           if converte else ""))
