"""O contrato de um check."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..estados import Estado


@dataclass
class Resultado:
    """
    O que um check devolve.

    `detecta` NAO e documentacao — e o §4.15 virando campo obrigatorio. Quem
    escreve um check e obrigado a dizer que defeito aquele numero revelaria; se
    nao souber responder, o check nao deveria existir.
    """
    nome:      str
    estado:    Estado
    detecta:   str                            # §4.15: qual defeito este numero move
    evidencia: dict[str, Any] = field(default_factory=dict)
    motivo:    str = ""
    bloqueia:  bool = True                    # False = informativo, nao barra

    def __post_init__(self):
        if not self.detecta.strip():
            raise ValueError(
                f"check '{self.nome}' nao declarou o que detecta (NORTE §4.15). "
                f"Uma verificacao cuja grandeza o defeito nao move nao e evidencia."
            )

    @property
    def barra(self) -> bool:
        """Este check impede a publicacao de metrica.

        Qualquer coisa que nao seja PASS barra, PENDING incluido: um check
        bloqueante que nao rodou nao autoriza nada. So `bloqueia=False` (checks
        informativos, do modo DIAGNOSTIC) escapa.
        """
        return self.bloqueia and self.estado is not Estado.PASS


class Check:
    """Marcador de namespace; os checks sao funcoes puras que devolvem Resultado."""
