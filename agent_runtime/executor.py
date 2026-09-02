"""
O controlador do loop. Quem para, e por que.

    modelo propoe  ->  politica decide  ->  provedor executa
         ^                                        |
         |                                        v
    memoria da tarefa  <----------------  observacao

O modelo participa do loop; o kernel CONTROLA o loop. Concretamente: o modelo
nunca chama `provedor.executa`. Ele devolve uma intencao, e esta classe e a
unica que executa — depois de passar pela politica.

TODA SAIDA E TERMINAL E EXPLICITA. Nao existe "o loop acabou": existe
CONCLUIDA, ESGOTADA, BLOQUEADA ou FALHA, e o motivo vai gravado. Um loop que
para sem dizer por que e indistinguivel de um que travou.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .capacidades import CapacidadeNaoImplementada, exige_implementada
from .contrato import Observacao, ProvedorDeCapacidade
from .politica import Politica, Veredito
from .tarefa import EstadoTarefa, Tarefa


@dataclass
class Intencao:
    """O que o modelo propoe fazer no proximo passo. Proposta, nao ordem."""
    capacidade: str
    parametros: dict[str, Any] = field(default_factory=dict)
    porque:     str = ""
    concluir:   bool = False       # o modelo julga o objetivo atingido


@dataclass
class Resultado:
    tarefa:       Tarefa
    observacoes:  list[Observacao] = field(default_factory=list)
    negadas:      list[str] = field(default_factory=list)
    memoria:      dict[str, Any] = field(default_factory=dict)

    @property
    def concluida(self) -> bool:
        return self.tarefa.estado is EstadoTarefa.CONCLUIDA


class Executor:
    def __init__(self, politica: Politica, provedores: list[ProvedorDeCapacidade]):
        self.politica = politica
        self.provedores = provedores
        self._mapa: dict[str, ProvedorDeCapacidade] = {}
        for p in provedores:
            for c in p.capacidades():
                self._mapa[c] = p

    def roda(self, tarefa: Tarefa,
             propositor: Callable[[Tarefa, list[Observacao]], Intencao]) -> Resultado:
        """
        `propositor` e o modelo — ou um mock, ou uma heuristica. O runtime nao
        sabe qual, e nao deve: trocar Claude por Ollama nao pode mexer aqui.
        """
        res = Resultado(tarefa=tarefa)

        admissao = self.politica.admite_tarefa(tarefa)
        if not admissao.pode_executar:
            tarefa.estado = EstadoTarefa.BLOQUEADA
            tarefa.motivo_parada = f"admissao: {admissao.motivo}"
            res.negadas.append(admissao.capacidade)
            return res

        tarefa.estado = EstadoTarefa.EXECUTANDO
        t0 = time.perf_counter()

        while True:
            # ── tetos, conferidos ANTES de gastar a iteracao ────────────────
            if tarefa.iteracao >= tarefa.orcamento.max_iteracoes:
                tarefa.estado = EstadoTarefa.ESGOTADA
                tarefa.motivo_parada = (
                    f"orcamento: {tarefa.iteracao} iteracoes, teto "
                    f"{tarefa.orcamento.max_iteracoes}")
                break
            if len(res.observacoes) >= tarefa.orcamento.max_observacoes:
                tarefa.estado = EstadoTarefa.ESGOTADA
                tarefa.motivo_parada = "orcamento: teto de observacoes"
                break
            if time.perf_counter() - t0 > tarefa.orcamento.max_segundos:
                tarefa.estado = EstadoTarefa.ESGOTADA
                tarefa.motivo_parada = "orcamento: teto de tempo"
                break

            intencao = propositor(tarefa, list(res.observacoes))

            if intencao.concluir:
                tarefa.estado = EstadoTarefa.CONCLUIDA
                tarefa.motivo_parada = intencao.porque or "objetivo atingido"
                break

            decisao = self.politica.avalia(tarefa, intencao.capacidade,
                                           intencao.parametros)
            if not decisao.pode_executar:
                # Negar NAO mata a tarefa: o modelo pode propor outra coisa na
                # proxima iteracao. Matar aqui transformaria toda negacao em
                # falha, e o agente perderia a chance de contornar dentro do
                # que ele PODE fazer.
                res.negadas.append(intencao.capacidade)
                tarefa.iteracao += 1
                if len(res.negadas) >= tarefa.orcamento.max_iteracoes:
                    tarefa.estado = EstadoTarefa.BLOQUEADA
                    tarefa.motivo_parada = "toda proposta negada pela politica"
                    break
                continue

            provedor = self._mapa.get(intencao.capacidade)
            if provedor is None:
                tarefa.estado = EstadoTarefa.FALHA
                tarefa.motivo_parada = (
                    f"nenhum provedor implementa '{intencao.capacidade}' — "
                    f"a politica permitiu, mas nao ha quem execute")
                break

            try:
                exige_implementada(intencao.capacidade)
                novas = provedor.executa(intencao.capacidade,
                                         intencao.parametros,
                                         tarefa.id, tarefa.iteracao)
            except CapacidadeNaoImplementada as e:
                tarefa.estado = EstadoTarefa.BLOQUEADA
                tarefa.motivo_parada = str(e).splitlines()[0]
                break
            except Exception as e:
                tarefa.estado = EstadoTarefa.FALHA
                tarefa.motivo_parada = f"{type(e).__name__}: {e}"
                break

            res.observacoes.extend(novas)
            tarefa.iteracao += 1

        return res
