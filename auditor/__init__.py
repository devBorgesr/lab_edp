"""
MVP-0 do servico de auditoria.

A caracteristica que o distingue de uma ferramenta de avaliacao: quando as
pre-condicoes de validade nao sao satisfeitas, ele **nao produz metrica**. O
pipeline para, o manifesto recusa publicacao, e o relatorio explica por que.
"""
from .estados import Estado, StatusAuditoria, AuditoriaBloqueada  # noqa: F401
from .manifest import Manifesto                                    # noqa: F401
from .pipeline import Auditoria, Protocolo                         # noqa: F401
from . import relatorio                                            # noqa: F401
