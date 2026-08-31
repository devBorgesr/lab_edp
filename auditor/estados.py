"""
Os estados de uma etapa de auditoria, e o que cada um autoriza.

A distincao que importa comercialmente nao e PASS/FAIL. E entre:

    FAIL      a etapa rodou e o sistema auditado reprovou  -> resultado do cliente
    BLOCKED   a etapa nao pode rodar; uma pre-condicao quebrou -> NAO ha resultado
    INVALID   o insumo nao e auditavel (artefato marcado, procedencia ausente)

Um servico que confunde FAIL com BLOCKED entrega "seu RAG tem Recall@5 = 0,41"
quando na verdade nao mediu nada. Foi exatamente o que quase aconteceu no
REL-001: 492 rotulos coletados sobre pares invalidos dariam um kappa.
"""
from __future__ import annotations

from enum import Enum


class Estado(str, Enum):
    PENDING = "PENDING"    # ainda nao rodou
    PASS    = "PASS"       # rodou e passou
    FAIL    = "FAIL"       # rodou e reprovou — isto E um resultado
    INVALID = "INVALID"    # o insumo nao e auditavel
    BLOCKED = "BLOCKED"    # nao pode rodar: pre-condicao quebrada

    @property
    def impede_resultado(self) -> bool:
        """Estados sob os quais NENHUMA metrica pode ser publicada."""
        return self in (Estado.BLOCKED, Estado.INVALID, Estado.PENDING)


class StatusAuditoria(str, Enum):
    READY    = "READY"      # pre-condicoes ok, pode executar
    COMPLETE = "COMPLETE"   # executou; ha resultado
    BLOCKED  = "BLOCKED"    # nao executa; ha diagnostico, nao resultado


class AuditoriaBloqueada(RuntimeError):
    """
    Levantada quando alguem tenta ler resultado de auditoria bloqueada.

    Existe para que "nao publicar metrica sem pre-condicao" seja propriedade do
    programa e nao disciplina de quem escreve o relatorio.
    """
