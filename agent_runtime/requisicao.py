"""
`TarefaRequest v1` — o contrato pelo qual um cliente pede uma tarefa.

QUEM E O CLIENTE, E O PROBLEMA DE TRANSPORTE QUE ISTO NAO RESOLVE

O Copiloto e JavaScript, dentro de uma extensao Chrome. O sandbox dele e
IndexedDB da origem `chrome-extension://<id>` — Python nao le isso. Medido em
01/09: `manifest.json` da v4.2 tem `host_permissions: ["https://claude.ai/*"]`
e nada mais, e `chrome.downloads` so aparece em `popup.js`.

Portanto **nao existe transporte Copiloto -> runtime hoje**, e criar um custa:

    HTTP local     ->  adicionar host_permission ao manifest = MEXER no
                       Exportador
    download       ->  o painel do Copiloto precisa expor um botao = MEXER no
                       Exportador
    manual         ->  o operador salva o JSON e aponta o runtime para ele
                       = zero mudanca nos dois lados

Este modulo implementa o terceiro, e deixa os outros dois possiveis: o
contrato e um ARQUIVO JSON. Quem escrever esse arquivo — Copiloto com um
botao novo, um servidor HTTP, ou uma pessoa — nao muda nada aqui.

Nao escolhi o transporte. Registrei que a escolha existe.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .capacidades import Nivel, busca
from .tarefa import Orcamento, Tarefa

SCHEMA = "TarefaRequest v1"

CAMPOS = {"objetivo": str, "capacidades": list}
OPCIONAIS = {"schema": str, "max_iteracoes": int, "max_observacoes": int,
             "max_segundos": (int, float), "criada_por": str,
             "hipotese": str, "ambiente": dict}


class RequisicaoInvalida(ValueError):
    """Recusada antes de virar Tarefa."""


def valida(d: dict[str, Any]) -> dict[str, Any]:
    """
    Recusa cedo e alto. Campo desconhecido e ERRO, nao ruido ignorado: um
    `capacidade` no lugar de `capacidades` rodaria a tarefa sem a capacidade
    que o cliente pensou ter pedido, e a politica negaria tudo sem que
    ninguem entendesse por que.
    """
    if not isinstance(d, dict):
        raise RequisicaoInvalida(f"requisicao precisa ser objeto, veio {type(d).__name__}")

    schema = d.get("schema", SCHEMA)
    if schema != SCHEMA:
        raise RequisicaoInvalida(
            f"schema '{schema}' desconhecido; este runtime fala '{SCHEMA}'")

    faltando = [c for c in CAMPOS if c not in d]
    if faltando:
        raise RequisicaoInvalida(f"{SCHEMA}: faltam campos {faltando}")

    estranhos = sorted(set(d) - set(CAMPOS) - set(OPCIONAIS))
    if estranhos:
        raise RequisicaoInvalida(
            f"campos desconhecidos {estranhos}. Ignorar em silencio faria a "
            f"tarefa rodar diferente do que o cliente pediu.")

    if not isinstance(d["objetivo"], str) or not d["objetivo"].strip():
        raise RequisicaoInvalida("`objetivo` precisa ser texto nao-vazio")
    caps = d["capacidades"]
    if not isinstance(caps, list) or not caps:
        raise RequisicaoInvalida("`capacidades` precisa ser lista nao-vazia")
    for c in caps:
        busca(str(c))          # CapacidadeDesconhecida se nao existir
    return d


def para_tarefa(d: dict[str, Any], teto_nivel: Nivel = Nivel.OBSERVAR) -> Tarefa:
    """
    Requisicao -> Tarefa, com um teto de nivel aplicado NA ENTRADA.

    O teto aqui e redundante com a `Politica` de proposito. A politica decide
    por chamada; isto recusa a tarefa inteira antes de existir. Duas travas
    para a mesma coisa, porque o custo de errar e agir no ambiente de alguem.
    """
    d = valida(d)
    caps = [str(c) for c in d["capacidades"]]
    acima = [c for c in caps if busca(c).nivel > teto_nivel]
    if acima:
        raise RequisicaoInvalida(
            f"capacidades acima do teto L{int(teto_nivel)} deste runtime: "
            f"{sorted(acima)}. Ver docs/agent_runtime/DECISAO_ATUACAO.md — "
            f"L1/L2 estao declaradas e recusadas por decisao pendente.")

    return Tarefa(
        objetivo=d["objetivo"].strip(),
        capacidades=caps,
        orcamento=Orcamento(
            max_iteracoes=int(d.get("max_iteracoes", 10)),
            max_observacoes=int(d.get("max_observacoes", 500)),
            max_segundos=float(d.get("max_segundos", 300.0))),
        criada_por=str(d.get("criada_por", "cliente")),
        hipotese=str(d.get("hipotese", "")),
    )


def de_arquivo(caminho: Path | str, teto_nivel: Nivel = Nivel.OBSERVAR) -> Tarefa:
    """O transporte que existe hoje: um arquivo JSON no disco."""
    p = Path(caminho)
    if not p.exists():
        raise RequisicaoInvalida(f"requisicao nao encontrada: {p}")
    return para_tarefa(json.loads(p.read_text(encoding="utf-8")), teto_nivel)


EXEMPLO = {
    "schema": SCHEMA,
    "objetivo": "descobrir por que /search devolve 403",
    "capacidades": ["observe.network", "analyze.json"],
    "max_iteracoes": 8,
    "criada_por": "copiloto",
    "ambiente": {"har": "/traffic/2026-09-01/sessao.har"},
}
