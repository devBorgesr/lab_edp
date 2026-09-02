"""
A Tarefa: uma DECLARACAO de trabalho, nao uma thread.

A diferenca importa. Se o modelo criasse threads, ele teria autoridade — e o
kernel viraria espectador do que ele mesmo deveria governar. Aqui o modelo
produz uma declaracao; quem executa, decide orcamento e para o loop e o
kernel.

ORCAMENTO E OBRIGATORIO. Um loop de agente sem teto nao e autonomo, e
descontrolado: a diferenca entre os dois e alguem ter escrito o numero antes.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .capacidades import Nivel, busca


class EstadoTarefa(str, Enum):
    DECLARADA = "DECLARADA"    # existe, nao comecou
    EXECUTANDO = "EXECUTANDO"
    CONCLUIDA = "CONCLUIDA"    # objetivo atingido
    ESGOTADA = "ESGOTADA"      # bateu no orcamento sem concluir
    BLOQUEADA = "BLOQUEADA"    # politica negou algo essencial
    FALHA = "FALHA"            # erro de execucao do runtime

    @property
    def terminal(self) -> bool:
        return self in (EstadoTarefa.CONCLUIDA, EstadoTarefa.ESGOTADA,
                        EstadoTarefa.BLOQUEADA, EstadoTarefa.FALHA)


class OrcamentoInvalido(ValueError):
    pass


@dataclass
class Orcamento:
    """
    Teto do loop. `max_iteracoes` nao tem default generoso de proposito —
    quem declara a tarefa escolhe, e escolhe olhando.
    """
    max_iteracoes:   int
    max_observacoes: int = 500
    max_segundos:    float = 300.0

    def __post_init__(self):
        if self.max_iteracoes < 1:
            raise OrcamentoInvalido("max_iteracoes precisa ser >= 1")
        if self.max_iteracoes > 100:
            raise OrcamentoInvalido(
                f"max_iteracoes={self.max_iteracoes} acima do teto duro de "
                f"100. Um loop que precisa de mais que isso provavelmente "
                f"nao tem criterio de parada — declare o criterio, nao mais "
                f"iteracoes."
            )


@dataclass
class Tarefa:
    objetivo:     str
    capacidades:  list[str]
    orcamento:    Orcamento
    id:           str = field(default_factory=lambda: f"T-{uuid.uuid4().hex[:8]}")
    estado:       EstadoTarefa = EstadoTarefa.DECLARADA
    criada_em:    str = field(default_factory=
                              lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    criada_por:   str = "?"        # modelo ou humano que declarou
    pai:          str | None = None  # tarefa que gerou esta
    iteracao:     int = 0
    hipotese:     str = ""
    motivo_parada: str = ""

    def __post_init__(self):
        if not self.objetivo.strip():
            raise ValueError("tarefa sem objetivo — um loop sem alvo nao para")
        if not self.capacidades:
            raise ValueError(
                "tarefa sem capacidade declarada. Declarar as capacidades na "
                "TAREFA, e nao pedi-las no meio do loop, e o que permite a "
                "politica decidir antes de comecar."
            )
        for c in self.capacidades:
            busca(c)      # levanta CapacidadeDesconhecida se nao existir

    @property
    def nivel_maximo(self) -> Nivel:
        return max(busca(c).nivel for c in self.capacidades)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["estado"] = self.estado.value
        d["nivel_maximo"] = int(self.nivel_maximo)
        return d


def deriva(pai: "Tarefa", objetivo: str, capacidades: list[str],
           orcamento: Orcamento | None = None) -> "Tarefa":
    """
    Tarefa filha, gerada por outra. A linhagem fica no campo `pai`.

    A filha NAO herda capacidade automaticamente: precisa declarar as suas, e
    passam pela politica de novo. Herdar em silencio seria a forma mais facil
    de uma tarefa L0 virar L2 em tres saltos.
    """
    return Tarefa(objetivo=objetivo, capacidades=capacidades,
                  orcamento=orcamento or Orcamento(max_iteracoes=pai.orcamento.max_iteracoes),
                  pai=pai.id, criada_por=pai.criada_por)
