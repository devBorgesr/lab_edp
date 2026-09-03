"""
O modelo produz `Intencao`. So isso.

Este e o unico lugar do runtime onde um LLM aparece, e ele nao recebe
ferramenta nenhuma: recebe o estado da tarefa e devolve JSON. Quem executa e
o `Executor`, depois da `Politica`. Se este modulo fosse comprometido, o pior
que consegue e propor — e a politica nega o que nao foi declarado.

O PARSE E ESTRITO, E ISSO NAO E DETALHE

Saida ilegivel devolve `None`, NUNCA uma intencao default e NUNCA
`concluir=True`. Se ilegivel virasse "concluir", um modelo com problema de
formatacao encerraria a tarefa dizendo que atingiu o objetivo. E se virasse
uma capacidade qualquer, o modelo estaria escolhendo por acidente.

Mesma disciplina de `sujeitos/rel/juiz_llm.py::parse_resposta`, que devolve
`None` e nao `0` — ali para nao esconder falha do juiz dentro da taxa de
irrelevancia; aqui para nao esconder falha de parse dentro do resultado da
tarefa.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .capacidades import busca
from .contrato import Observacao
from .executor import Intencao
from .roteador import Escolha, Roteador, RoteadorFixo
from .tarefa import Tarefa


class ClienteDeModelo(ABC):
    """
    Fala com UM provedor. O runtime nao sabe qual — trocar Claude por Ollama
    nao mexe em nada acima desta interface.
    """
    @abstractmethod
    def completa(self, modelo: str, prompt: str) -> str: ...


class ClienteFake(ClienteDeModelo):
    """Respostas roteirizadas. Todo teste do loop usa isto — nenhum gasta API."""

    def __init__(self, respostas: list[str]):
        self.respostas = list(respostas)
        self.chamadas: list[tuple[str, str]] = []

    def completa(self, modelo: str, prompt: str) -> str:
        self.chamadas.append((modelo, prompt))
        return self.respostas.pop(0) if self.respostas else "{}"


PROMPT = """Voce participa de um loop de investigacao governado por um kernel.

OBJETIVO DA TAREFA
{objetivo}

CAPACIDADES QUE VOCE PODE PROPOR (e SO estas)
{capacidades}

ITERACAO {iteracao} de {teto}

OBSERVACOES JA COLHIDAS
{observacoes}

Responda APENAS com um objeto JSON, sem texto antes ou depois:

  {{"capacidade": "<uma das listadas>", "parametros": {{}}, "porque": "<motivo curto>"}}

ou, se o objetivo ja foi atingido pelas observacoes acima:

  {{"concluir": true, "porque": "<o que voce concluiu>"}}

Voce NAO executa nada. Voce propoe, e o kernel decide se executa."""


@dataclass
class PropositorLLM:
    """
    Junta Roteador + Cliente e vira o `propositor` que o `Executor` chama.

    Guarda a trilha de quem respondeu o que, por iteracao — sem isso, uma
    tarefa que trocou de modelo no meio fica impossivel de reconstruir depois.
    """
    cliente:   ClienteDeModelo
    roteador:  Roteador = field(default_factory=RoteadorFixo)
    trilha:    list[dict[str, Any]] = field(default_factory=list)
    max_ilegiveis: int = 3
    _ilegiveis: int = 0
    _ultimo_modelo: str | None = None

    def __call__(self, tarefa: Tarefa, obs: list[Observacao]) -> Intencao:
        escolha = self.roteador.escolhe(
            f"{tarefa.objetivo} {tarefa.hipotese}".strip(),
            modelo_anterior=self._ultimo_modelo,
            contexto={"iteracao": tarefa.iteracao})
        self._ultimo_modelo = escolha.modelo

        bruto = self.cliente.completa(escolha.modelo,
                                      self._prompt(tarefa, obs))
        intencao = self.parse(bruto, tarefa)

        self.trilha.append({
            "iteracao": tarefa.iteracao, "modelo": escolha.modelo,
            "tier": escolha.tier, "porque_o_modelo": escolha.porque,
            "custo_estimado_usd": escolha.custo_estimado_usd,
            "proposta": (intencao.capacidade if intencao else None),
            "ilegivel": intencao is None,
        })

        if intencao is None:
            self._ilegiveis += 1
            if self._ilegiveis >= self.max_ilegiveis:
                # Nao concluo por desistencia: proponho uma capacidade
                # inexistente de proposito, para a politica NEGAR e o loop
                # terminar em BLOQUEADA com motivo — nunca em CONCLUIDA.
                return Intencao("__ilegivel__", {},
                                f"{self._ilegiveis} respostas ilegiveis seguidas")
            return Intencao("__ilegivel__", {}, "resposta ilegivel")
        return intencao

    def _prompt(self, tarefa: Tarefa, obs: list[Observacao]) -> str:
        caps = "\n".join(f"  - {c}: {busca(c).o_que_faz}"
                         for c in tarefa.capacidades)
        if obs:
            linhas = [f"  [{o.iteracao}] {o.capacidade}: "
                      f"{json.dumps(o.dados, ensure_ascii=False)[:300]}"
                      for o in obs[-12:]]
            texto_obs = "\n".join(linhas)
        else:
            texto_obs = "  (nenhuma ainda)"
        return PROMPT.format(objetivo=tarefa.objetivo, capacidades=caps,
                             iteracao=tarefa.iteracao,
                             teto=tarefa.orcamento.max_iteracoes,
                             observacoes=texto_obs)

    @staticmethod
    def parse(bruto: str, tarefa: Tarefa) -> Intencao | None:
        """
        `None` para ilegivel. Nunca uma intencao default, nunca `concluir`.
        """
        m = re.search(r"\{.*\}", bruto or "", re.S)
        if not m:
            return None
        try:
            d = json.loads(m.group(0))
        except Exception:
            return None
        if not isinstance(d, dict):
            return None

        if d.get("concluir") is True:
            return Intencao("", {}, str(d.get("porque", "")), concluir=True)

        cap = d.get("capacidade")
        if not isinstance(cap, str) or not cap:
            return None
        par = d.get("parametros")
        return Intencao(cap, par if isinstance(par, dict) else {},
                        str(d.get("porque", "")))
