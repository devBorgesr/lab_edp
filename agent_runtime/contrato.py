"""
As interfaces entre o kernel e o mundo. O kernel NAO sabe que Chrome existe.

POR QUE ESTA FRONTEIRA EXISTE

O EDP tem memoria, estado, eventos e proveniencia. O Exportador tem percepcao
do navegador. Uni-los fisicamente amarraria um ao outro para sempre: trocar
Chrome por Playwright, ou rodar o kernel sem navegador nenhum, exigiria mexer
nos dois.

Aqui o kernel fala com `ProvedorDeCapacidade`. Quem implementa pode ser um
leitor de HAR, um driver de navegador, um servidor remoto ou um mock de teste.
Nada disso aparece na assinatura.

O QUE ATRAVESSA A FRONTEIRA

    Observacao   fato colhido do ambiente, com proveniencia
    Artefato     arquivo produzido (HAR, captura, relatorio)

Nada mais. Em particular NAO atravessa: handle de aba, sessao CDP, socket,
credencial. Se atravessasse, o kernel voltaria a saber o que nao deve.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Observacao:
    """
    Um fato colhido do ambiente. IMUTAVEL de proposito.

    Uma observacao que pode ser editada depois de colhida nao serve de
    evidencia — e o loop inteiro decide com base nelas. `frozen=True` nao e
    estilo; e a garantia de que o passo 7 nao reescreve o que o passo 2 viu.
    """
    capacidade:  str                    # qual capacidade a produziu
    tarefa_id:   str
    iteracao:    int
    dados:       dict[str, Any]
    colhida_em:  str = field(default_factory=_agora)
    fonte:       str = ""               # arquivo/endpoint de origem

    def hash(self) -> str:
        """Identidade por conteudo — duas observacoes iguais tem o mesmo id."""
        canonico = json.dumps(
            {"capacidade": self.capacidade, "dados": self.dados,
             "fonte": self.fonte},
            sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"capacidade": self.capacidade, "tarefa_id": self.tarefa_id,
                "iteracao": self.iteracao, "dados": self.dados,
                "colhida_em": self.colhida_em, "fonte": self.fonte,
                "hash": self.hash()}


@dataclass(frozen=True)
class Artefato:
    """Arquivo produzido durante a tarefa. Referenciado, nunca embutido."""
    caminho:    str
    tipo:       str                     # har | json | md | png
    tarefa_id:  str
    sha256:     str = ""
    bytes:      int = 0


class ProvedorDeCapacidade(ABC):
    """
    Quem sabe executar uma capacidade. O kernel so conhece esta interface.

    `capacidades()` declara o que o provedor sabe fazer, por NOME — e o nome
    tem que existir no catalogo de `capacidades.py`. Um provedor nao pode
    inventar capacidade: se pudesse, a politica nao teria o que autorizar.
    """

    nome: str = "provedor"

    @abstractmethod
    def capacidades(self) -> set[str]:
        """Nomes de capacidade que este provedor implementa."""

    @abstractmethod
    def executa(self, capacidade: str, parametros: dict[str, Any],
                tarefa_id: str, iteracao: int) -> list[Observacao]:
        """
        Executa UMA capacidade e devolve observacoes.

        Nunca devolve None e nunca levanta por resultado vazio: "nao achei
        nada" e uma observacao valida, e o loop precisa distinguir isso de
        "falhou". Levantar fica para erro de execucao de verdade.
        """


class RegistroDeMemoria(Protocol):
    """
    O que o runtime precisa de uma memoria. Deliberadamente minimo.

    O EDP implementa muito mais que isto. Amarrar o runtime a interface
    inteira do `MemoryStore` faria o runtime nao rodar sem o EDP — e o
    primeiro consumidor deste codigo e um teste, nao o kernel.
    """
    def escreve(self, chave: str, valor: dict[str, Any]) -> None: ...
    def le(self, chave: str) -> dict[str, Any] | None: ...
