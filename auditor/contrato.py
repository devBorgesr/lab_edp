"""
O contrato que um sistema auditavel cumpre. O EDP e o primeiro, nao o unico.

DESACOPLAMENTO DELIBERADO: enquanto o pipeline importar `edp.*`, o servico
audita um produto so. A interface abaixo e o minimo que um RAG precisa expor
para ser auditado, e nada nela menciona EDP.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class SistemaAuditavel(ABC):
    """
    Quatro metodos. Quem implementa os quatro pode ser auditado.

    `consulta` DEVE devolver `[(doc_id, score), ...]`. Nao e detalhe de
    formato: o score e a prova de que o ranking saiu de um retriever e nao de
    uma lista qualquer de ids (NORTE §4.15 — a grandeza precisa ser uma que o
    defeito moveria). Um adaptador que nao tem score nao tem como provar
    procedencia, e o servico vai barrar.
    """

    nome: str = "sistema"

    @property
    @abstractmethod
    def snapshot_dir(self) -> Path:
        """Diretorio do corpus, para hash de procedencia."""

    @abstractmethod
    def consulta(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Ranking real: `[(doc_id, score), ...]`, ordem do retriever."""

    @abstractmethod
    def texto(self, doc_id: str) -> str:
        """Texto do documento. Usado para medir duplicacao por conteudo."""

    @abstractmethod
    def controle_para(self, query: dict) -> list[str]:
        """Candidatos a controle negativo — documentos de outro dominio."""

    # ── opcional, com default honesto ───────────────────────────────────────

    def telemetria_do_ranking(self, query: str, top_k: int) -> dict[str, Any]:
        """
        Item 4: o ranking vira CONTRATO, nao convencao.

        Registrado por consulta, para que o manifesto possa provar que o
        servico nao recebeu uma lista arbitraria de ids.
        """
        rk = self.consulta(query, top_k)
        ok = all(isinstance(x, (tuple, list)) and len(x) == 2 for x in rk)
        ids = [d for d, _ in rk] if ok else []
        txt = {(self.texto(d) or "").strip() for d in set(ids)} if ok else set()
        return {
            "origem_do_ranking":  f"{type(self).__name__}.consulta",
            "top_k_solicitado":   top_k,
            "n_slots_recebidos":  len(rk),
            "n_ids_distintos":    len(set(ids)),
            "n_textos_distintos": len(txt),
            "formato_valido":     ok,
        }
