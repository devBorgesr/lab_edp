"""
Fila em disco e worker minimo. Sem Celery, sem Redis — ainda nao ha carga que
justifique, e uma dependencia de infraestrutura escolhida antes da carga e uma
aposta sobre um numero que ninguem mediu.

    <base>/_fila/pendente/<audit_id>.json     enfileirado
    <base>/_fila/executando/<audit_id>.json   reivindicado por um worker

A reivindicacao e um `rename`, que e atomico no mesmo sistema de arquivos:
dois workers nao pegam a mesma auditoria porque o segundo `rename` falha.

A interface e estreita de proposito (`enfileira`, `reivindica`, `conclui`),
para que trocar por uma fila de verdade depois nao mexa em nada alem daqui.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class Fila:
    def __init__(self, base: Path):
        self.base = Path(base) / "_fila"
        self.pendente = self.base / "pendente"
        self.executando = self.base / "executando"
        for d in (self.pendente, self.executando):
            d.mkdir(parents=True, exist_ok=True)

    def enfileira(self, audit_id: str, tarefa: dict[str, Any]) -> None:
        alvo = self.pendente / f"{audit_id}.json"
        tmp = alvo.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            **tarefa, "audit_id": audit_id,
            "enfileirado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, alvo)          # so aparece completo

    def reivindica(self) -> dict[str, Any] | None:
        """Pega a proxima tarefa, ou None. `rename` decide quem ficou com ela."""
        for arq in sorted(self.pendente.glob("*.json")):
            destino = self.executando / arq.name
            try:
                os.rename(arq, destino)
            except OSError:
                continue               # outro worker foi mais rapido
            return json.loads(destino.read_text(encoding="utf-8"))
        return None

    def conclui(self, audit_id: str) -> None:
        (self.executando / f"{audit_id}.json").unlink(missing_ok=True)

    def devolve(self, audit_id: str) -> None:
        """Worker morreu no meio: a tarefa volta para a fila."""
        p = self.executando / f"{audit_id}.json"
        if p.exists():
            os.replace(p, self.pendente / p.name)

    def pendentes(self) -> int:
        return len(list(self.pendente.glob("*.json")))

    def orfas(self) -> Iterator[str]:
        """Reivindicadas que nunca concluiram — visiveis, nao silenciosas."""
        for p in sorted(self.executando.glob("*.json")):
            yield p.stem


def trabalha_uma(base: Path, protocolos: dict) -> str | None:
    """
    Executa no maximo uma tarefa. Devolve o `audit_id`, ou None se a fila
    estava vazia.

    Uma tarefa por chamada de proposito: quem chama decide a cadencia, e um
    worker que nao decide sozinho quando parar e mais facil de operar.
    """
    from . import jobs as J
    from .servico import executa

    fila = Fila(base)
    tarefa = fila.reivindica()
    if tarefa is None:
        return None

    aid = tarefa["audit_id"]
    raiz = Path(tarefa["raiz"])
    reg = J.Registro(raiz)
    try:
        executa(tarefa["entrada"], raiz, protocolos, audit_id=aid,
                client_id=tarefa.get("client_id", "default"))
    except Exception as e:
        job = reg.ver(aid) or J.Job(aid, client_id=tarefa.get("client_id", "default"))
        # ERROR e falha do SERVICO; nunca um veredito sobre o sistema auditado
        job.erro = f"{type(e).__name__}: {e}"
        alvo = J.INVALID if type(e).__name__ == "EntradaInvalida" else J.ERROR
        if job.status in (J.QUEUED, J.RUNNING):
            reg.grava(job.transita(alvo))
    finally:
        fila.conclui(aid)
    return aid
