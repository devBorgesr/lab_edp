"""
Tempo e custo por auditoria. Sem unidade economica nao ha preco.

Mede o que realmente varia: tempo por etapa, chamadas ao modelo, tokens. O
custo em dinheiro sai de uma tabela de preco EXPLICITA — nunca de constante
enterrada, para que ninguem cite um numero cuja origem ninguem sabe.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# USD por milhao de tokens. Preencher a partir da tabela publica vigente;
# `None` significa "nao sei", e o relatorio diz "nao estimado" em vez de zero.
PRECO_POR_MTOK: dict[str, tuple[float | None, float | None]] = {}


@dataclass
class Contabilidade:
    etapas:   dict[str, float] = field(default_factory=dict)
    chamadas: int = 0
    tok_in:   int = 0
    tok_out:  int = 0
    modelo:   str = ""
    _t0:      float | None = None
    _atual:   str = ""

    def inicia(self, etapa: str) -> None:
        self._t0, self._atual = time.perf_counter(), etapa

    def encerra(self) -> None:
        if self._t0 is not None:
            self.etapas[self._atual] = round(time.perf_counter() - self._t0, 3)
            self._t0 = None

    def chamada(self, tin: int = 0, tout: int = 0) -> None:
        self.chamadas += 1
        self.tok_in += tin
        self.tok_out += tout

    def resumo(self) -> dict[str, Any]:
        total = round(sum(self.etapas.values()), 3)
        d: dict[str, Any] = {
            "tempo_por_etapa_s": dict(self.etapas),
            "tempo_total_s": total,
            "chamadas_ao_modelo": self.chamadas,
            "tokens_entrada": self.tok_in,
            "tokens_saida": self.tok_out,
            "modelo": self.modelo or None,
        }
        p = PRECO_POR_MTOK.get(self.modelo or "")
        if p and p[0] is not None and p[1] is not None:
            d["custo_modelo_usd"] = round(
                self.tok_in / 1e6 * p[0] + self.tok_out / 1e6 * p[1], 6)
            d["fonte_do_preco"] = "auditor.custos.PRECO_POR_MTOK"
        else:
            d["custo_modelo_usd"] = None
            d["custo_nao_estimado_porque"] = (
                f"sem preco registrado para o modelo {self.modelo or '(nenhum)'}. "
                f"Zero seria mentira; None e a resposta honesta."
            )
        return d
