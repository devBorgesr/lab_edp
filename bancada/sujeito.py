"""
bancada.sujeito — o Protocol que a bancada enxerga. Nada mais.

A bancada so conhece isto. Todo conhecimento de interno do sistema-sob-
inspecao (schema de store, atributos privados, layout em disco) mora no
adaptador concreto (ex.: sujeitos/edp/adaptador.py), nunca aqui.
"""
from __future__ import annotations

from typing import Protocol


class Sujeito(Protocol):
    """Contrato minimo de um sistema-sob-inspecao (RAG ou analogo).

    A bancada so enxerga isto. Todo conhecimento de interno do sistema
    (schema de store, atributos privados, layout em disco) mora no adaptador.
    """
    nome: str

    def abrir_sessao(self) -> str:
        """Cria sessao ISOLADA da producao. Retorna session_id."""

    def fechar_sessao(self, session_id: str) -> dict:
        """Purga a sessao. Deve recusar purgar producao (guarda dura)."""

    def carregar_snapshot(self, session_id: str, entries: list) -> None:
        """Injeta o corpus clonado na sessao isolada."""

    def consultar(self, session_id: str, query: str, k: int) -> list:
        """Retrieve real. Retorna lista ordenada de dicts com, no minimo,
        as chaves: id (str), texto (str), score (float)."""

    def fingerprint_producao(self) -> dict:
        """Estado da producao para verify_no_leak. Deve conter 'hash'."""

    def exportar_producao(self) -> list:
        """Clone READ-ONLY do corpus de producao (sem mutar, sem persistir)."""
