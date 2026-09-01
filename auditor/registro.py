"""
Registro de adaptadores. Um lugar so onde se descobre o que existe.

Nao e marketplace: e a lista dos tradutores que este servico sabe construir,
com versao, para que o manifesto possa dizer qual foi usado e o CLI possa
recusar um nome que nao existe ANTES de copiar o snapshot do cliente.
"""
from __future__ import annotations

from typing import Any, Callable

_ADAPTADORES: dict[str, dict[str, Any]] = {}


def register_adapter(nome: str, construtor: Callable[..., Any],
                     versao: str = "?", descricao: str = "") -> None:
    if nome in _ADAPTADORES:
        raise ValueError(f"adaptador '{nome}' ja registrado")
    _ADAPTADORES[nome] = {"construtor": construtor, "versao": versao,
                          "descricao": descricao}


def constroi(nome: str, entrada: dict) -> Any:
    if nome not in _ADAPTADORES:
        raise KeyError(nome)
    return _ADAPTADORES[nome]["construtor"](entrada)


def conhecidos() -> dict[str, dict[str, str]]:
    return {n: {"versao": d["versao"], "descricao": d["descricao"]}
            for n, d in _ADAPTADORES.items()}


def _registra_padrao() -> None:
    """
    Import TARDIO de proposito: `edp` so e carregado se alguem pedir o
    adaptador `edp`. O nucleo do servico continua rodando sem ele.
    """
    from pathlib import Path

    def _edp(e):
        from .adaptadores.edp import EDPAuditavel
        op = e.get("options") or {}
        return EDPAuditavel(Path(e["snapshot"]),
                            Path(op["dominios"]) if op.get("dominios") else None)

    def _sintetico(e):
        from .fixtures import ClienteSintetico
        op = e.get("options") or {}
        return ClienteSintetico(Path(e["snapshot"]),
                                taxa_duplicacao=float(op.get("taxa_duplicacao", 0.0)))

    def _cliente(e):
        from .fixtures_cliente import constroi_cliente
        return constroi_cliente(e)

    register_adapter("edp", _edp, "edp-1",
                     "memoria do EDP; adaptador de referencia interno")
    register_adapter("sintetico", _sintetico, "fixture-1",
                     "corpus sintetico para demonstracao")
    register_adapter("cliente", _cliente, "cliente-1",
                     "sistema externo simulado (fixtures/customer_*)")


_registra_padrao()
