"""
O Router: escolhe QUAL modelo atende a proxima iteracao.

A propriedade que isto compra e a mais interessante do desenho — o modelo vira
RECURSO SUBSTITUIVEL dentro do loop, nao a identidade do agente:

    T-001 iteracao 1   Claude   -> observe.network
    T-001 iteracao 2   Claude   -> analyze.json
    T-001 iteracao 3   (contexto cresceu) -> modelo de janela maior
    T-001 iteracao 4   Ollama   -> resumir evidencias
    T-001 iteracao 5   Claude   -> concluir

A TAREFA continua a mesma. Trocar de modelo no meio nao reinicia nada, porque
o estado vive na Tarefa e nas Observacoes, nao no modelo.

O kernel do EDP ja tem `edp/model_router.py::route_model` — roteia por
complexidade (termos tecnicos, conectivos logicos, partes de pergunta) e
devolve modelo, tier, motivo e custo estimado. `RoteadorEDP` ADAPTA aquilo;
nao reimplementa. Nota: `model_router` tem 3 importadores e ZERO testes no
kernel (curadoria, 01/09) — por isso o adaptador degrada explicitamente
quando ele nao esta disponivel, em vez de assumir que esta.
"""
from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Escolha:
    """Qual modelo, e por que. O `porque` vai para a trilha da tarefa."""
    modelo: str
    tier: int = 0
    porque: str = ""
    custo_estimado_usd: float | None = None
    sinais: dict[str, Any] = field(default_factory=dict)


class Roteador(ABC):
    @abstractmethod
    def escolhe(self, texto: str, modelo_anterior: str | None = None,
                contexto: dict[str, Any] | None = None) -> Escolha: ...


class RoteadorFixo(Roteador):
    """
    Sempre o mesmo modelo. Existe para TESTE e para quando a escolha nao deve
    variar — um experimento que troca de modelo no meio nao mede o que pensa
    que mede.
    """

    def __init__(self, modelo: str = "fake-1", tier: int = 1):
        self.modelo, self.tier = modelo, tier

    def escolhe(self, texto, modelo_anterior=None, contexto=None) -> Escolha:
        return Escolha(self.modelo, self.tier, "roteador fixo")


class RoteadorEDP(Roteador):
    """
    Adapta `edp.model_router.route_model`. NAO reimplementa a heuristica.

    O caminho do kernel vem de `EDP_V5_PATH` (default: irmao no mesmo nivel).
    Se o kernel nao estiver la, `disponivel` fica False e `escolhe` levanta —
    em vez de cair num modelo default silencioso, que faria toda a tarefa
    rodar no modelo errado sem ninguem notar.
    """

    def __init__(self, caminho_edp: Path | str | None = None):
        self.caminho = Path(caminho_edp or os.environ.get(
            "EDP_V5_PATH", "/media/sf_edp_v5_main"))
        self._route = None
        self.motivo_indisponivel = ""

        # DEFEITO CORRIGIDO 03/09: antes isto so tentava o import. Uma vez que
        # `edp` entra em `sys.modules`, QUALQUER caminho passa a "funcionar" —
        # inclusive um inexistente. `disponivel` dizia True apontando para
        # lugar nenhum, e o kernel usado nao era o do caminho pedido.
        alvo = self.caminho / "edp" / "model_router.py"
        if not alvo.exists():
            self.motivo_indisponivel = f"{alvo} nao existe"
            return
        try:
            if str(self.caminho) not in sys.path:
                sys.path.insert(0, str(self.caminho))
            from edp.model_router import route_model      # type: ignore
            self._route = route_model
        except Exception as e:
            self.motivo_indisponivel = f"{type(e).__name__}: {e}"

    @property
    def disponivel(self) -> bool:
        return self._route is not None

    def escolhe(self, texto, modelo_anterior=None, contexto=None) -> Escolha:
        if not self.disponivel:
            raise RuntimeError(
                f"model_router do kernel indisponivel em {self.caminho} "
                f"({self.motivo_indisponivel}). Nao caio num modelo default: "
                f"a tarefa inteira rodaria no modelo errado em silencio."
            )
        r = self._route(texto, previous_model=modelo_anterior,
                        task_context=contexto or {})
        return Escolha(modelo=r.get("model", "?"), tier=int(r.get("tier", 0)),
                       porque=r.get("reason", ""),
                       custo_estimado_usd=r.get("estimated_cost_per_turn"),
                       sinais=r.get("signals", {}) or {})
