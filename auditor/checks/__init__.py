"""
Verificacoes reutilizaveis. Cada uma nasceu de um defeito que passou.

NORTE §4.15 — cada check declara, no proprio objeto, QUAL DEFEITO aquele numero
detectaria. Um check cuja grandeza o defeito nao move e ruido com aparencia de
garantia, e foi assim que o REL-001 perdeu 500 pares.
"""
from .base import Check, Resultado          # noqa: F401
from . import ranking, estratos, procedencia  # noqa: F401
