"""
A autoridade. O modelo PROPOE; isto DECIDE.

A inversao e o ponto inteiro deste runtime. Um agente com ferramentas decide e
executa. Aqui o modelo devolve uma intencao, e a intencao passa por esta
camada antes de virar acao. Se a politica sumisse, o resto continuaria
funcionando — e seria exatamente o sistema que este desenho existe para nao
ser.

TRES RESPOSTAS, e "pedir aprovacao" nao e enfeite: e o unico caminho pelo qual
uma capacidade que altera o ambiente do usuario pode rodar.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from .capacidades import CapacidadeDesconhecida, Nivel, busca
from .tarefa import Tarefa


class Veredito(str, Enum):
    PERMITE = "PERMITE"
    EXIGE_APROVACAO = "EXIGE_APROVACAO"
    NEGA = "NEGA"


@dataclass(frozen=True)
class Decisao:
    veredito: Veredito
    capacidade: str
    motivo: str

    @property
    def pode_executar(self) -> bool:
        return self.veredito is Veredito.PERMITE


class Politica:
    """
    `nivel_maximo` e o teto do que esta politica admite SEM aprovacao humana.

    Default `OBSERVAR`: a instancia mais permissiva por acidente ainda so
    observa. Um default frouxo aqui seria o tipo de erro que so aparece
    quando alguem ja rodou.
    """

    def __init__(self, nivel_maximo: Nivel = Nivel.OBSERVAR,
                 aprovador: Callable[[str, dict], bool] | None = None,
                 negadas: set[str] | None = None):
        self.nivel_maximo = nivel_maximo
        self.aprovador = aprovador
        self.negadas = negadas or set()
        self.trilha: list[dict[str, Any]] = []

    def avalia(self, tarefa: Tarefa, capacidade: str,
               parametros: dict[str, Any] | None = None) -> Decisao:
        parametros = parametros or {}
        try:
            cap = busca(capacidade)
        except CapacidadeDesconhecida:
            # DEFEITO CORRIGIDO 03/09: isto levantava e DERRUBAVA o loop.
            #
            # Um modelo alucina nome de capacidade — e o que modelos fazem. Se
            # a alucinacao derruba o runtime, o agente fica refem da
            # formatacao do modelo, e uma tarefa de 20 iteracoes morre na
            # primeira palavra inventada.
            #
            # DECLARAR capacidade inexistente na Tarefa continua levantando
            # (`Tarefa.__post_init__`): ali e erro de contrato do cliente, e
            # deve falhar alto. PROPOR uma no meio do loop e alucinacao, e a
            # resposta certa e negar.
            d = Decisao(Veredito.NEGA, capacidade,
                        "capacidade inexistente no catalogo (proposta invalida)")
            self.trilha.append({"tarefa": tarefa.id, "iteracao": tarefa.iteracao,
                                "capacidade": capacidade,
                                "veredito": d.veredito.value, "motivo": d.motivo})
            return d

        if capacidade in self.negadas:
            d = Decisao(Veredito.NEGA, capacidade,
                        "capacidade na lista de negadas desta politica")
        elif capacidade not in tarefa.capacidades:
            # A tarefa declarou o que precisaria. Pedir fora da declaracao e
            # como o escopo cresce no meio do loop, e e onde um agente
            # escapa da autorizacao que recebeu.
            d = Decisao(Veredito.NEGA, capacidade,
                        f"nao declarada na tarefa {tarefa.id} "
                        f"(declaradas: {sorted(tarefa.capacidades)})")
        elif cap.nivel <= self.nivel_maximo:
            d = Decisao(Veredito.PERMITE, capacidade,
                        f"L{int(cap.nivel)} dentro do teto L{int(self.nivel_maximo)}")
        elif self.aprovador is not None:
            ok = self.aprovador(capacidade, parametros)
            d = (Decisao(Veredito.PERMITE, capacidade,
                         f"L{int(cap.nivel)} acima do teto, aprovado explicitamente")
                 if ok else
                 Decisao(Veredito.NEGA, capacidade,
                         f"L{int(cap.nivel)} acima do teto, aprovacao recusada"))
        else:
            d = Decisao(Veredito.EXIGE_APROVACAO, capacidade,
                        f"L{int(cap.nivel)} acima do teto L{int(self.nivel_maximo)} "
                        f"e nao ha aprovador configurado")

        self.trilha.append({"tarefa": tarefa.id, "iteracao": tarefa.iteracao,
                            "capacidade": capacidade,
                            "veredito": d.veredito.value, "motivo": d.motivo})
        return d

    def admite_tarefa(self, tarefa: Tarefa) -> Decisao:
        """
        Avalia a tarefa ANTES de comecar, pelo nivel mais alto que ela declara.

        Descobrir na iteracao 7 que a tarefa nunca poderia rodar e desperdicio
        — e pior, e sete iteracoes de efeito colateral ja gasto.
        """
        pior = max(tarefa.capacidades, key=lambda c: busca(c).nivel)
        return self.avalia(tarefa, pior)
