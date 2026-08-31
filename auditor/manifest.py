"""
O manifesto: tudo que outra pessoa precisa para contestar a auditoria.

Um relatorio sem manifesto e opiniao. O manifesto responde, sem depender de
quem executou: qual corpus, qual retriever, qual configuracao, qual amostra,
quais pre-condicoes passaram, quais falharam, o que e valido e o que foi
invalidado.
"""
from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .checks.base import Resultado
from .estados import AuditoriaBloqueada, Estado, StatusAuditoria


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Manifesto:
    audit_id:   str
    protocolo:  str
    modo:       str = "AUDIT"                       # AUDIT | DIAGNOSTIC
    criado_em:  str = field(default_factory=_agora)
    snapshot:   dict[str, Any] = field(default_factory=dict)
    retriever:  dict[str, Any] = field(default_factory=dict)
    dataset:    dict[str, Any] = field(default_factory=dict)
    amostra:    dict[str, Any] = field(default_factory=dict)
    juiz:       dict[str, Any] = field(default_factory=dict)
    checks:     list[Resultado] = field(default_factory=list)
    etapas:     list[dict[str, Any]] = field(default_factory=list)
    invalidados: list[dict[str, Any]] = field(default_factory=list)
    _resultado: dict[str, Any] | None = None

    # ── o portao ─────────────────────────────────────────────────────────────

    @property
    def barreiras(self) -> list[Resultado]:
        """Checks bloqueantes que nao passaram. Nao vazio => nada se publica."""
        return [c for c in self.checks if c.barra]

    @property
    def status(self) -> StatusAuditoria:
        if self.barreiras:
            return StatusAuditoria.BLOCKED
        return (StatusAuditoria.COMPLETE if self._resultado is not None
                else StatusAuditoria.READY)

    def publica_resultado(self, r: dict[str, Any]) -> None:
        """
        Unico caminho por onde uma metrica entra no manifesto — e ele RECUSA
        quando ha barreira.

        Nao e cinto de seguranca redundante: o pipeline ja para antes. E a
        segunda tranca, para o caso de alguem montar as etapas na mao.
        """
        if self.barreiras:
            raise AuditoriaBloqueada(
                f"tentativa de publicar resultado com {len(self.barreiras)} "
                f"pre-condicao(oes) quebrada(s): "
                f"{[c.nome for c in self.barreiras]}"
            )
        self._resultado = r

    @property
    def resultado(self) -> dict[str, Any]:
        if self.status is not StatusAuditoria.COMPLETE:
            raise AuditoriaBloqueada(
                f"auditoria {self.audit_id} esta {self.status.value}; nao ha "
                f"resultado. Bloqueada por: {[c.nome for c in self.barreiras]}"
            )
        return dict(self._resultado or {})

    # ── registro ─────────────────────────────────────────────────────────────

    def registra(self, *cs: Resultado) -> "Manifesto":
        self.checks.extend(cs)
        return self

    def etapa(self, nome: str, estado: Estado, **ev) -> "Manifesto":
        self.etapas.append({"etapa": nome, "estado": estado.value, **ev})
        return self

    def invalida(self, artefato: str, motivo: str) -> "Manifesto":
        self.invalidados.append({"artefato": artefato, "motivo": motivo,
                                 "em": _agora()})
        return self

    # ── serializacao ────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        d = {
            "audit_id":  self.audit_id,
            "protocolo": self.protocolo,
            "modo":      self.modo,
            "criado_em": self.criado_em,
            "status":    self.status.value,
            "ambiente":  {"python": platform.python_version(),
                          "plataforma": platform.platform()},
            "snapshot":  self.snapshot,
            "retriever": self.retriever,
            "dataset":   self.dataset,
            "amostra":   self.amostra,
            "juiz":      self.juiz,
            "etapas":    self.etapas,
            "checks": [
                {"nome": c.nome, "estado": c.estado.value, "detecta": c.detecta,
                 "bloqueia": c.bloqueia, "barra": c.barra,
                 "motivo": c.motivo, "evidencia": c.evidencia}
                for c in self.checks
            ],
            "barreiras":   [c.nome for c in self.barreiras],
            "invalidados": self.invalidados,
        }
        # o resultado so aparece no manifesto se houver resultado
        if self.status is StatusAuditoria.COMPLETE:
            d["resultado"] = self._resultado
        else:
            d["resultado"] = None
            d["NAO_HA_RESULTADO"] = (
                "nenhuma metrica foi calculada. As pre-condicoes listadas em "
                "`barreiras` nao foram satisfeitas."
            )
        d["sha256_manifesto"] = hashlib.sha256(
            json.dumps({k: v for k, v in d.items()},
                       sort_keys=True, ensure_ascii=False, default=str
                       ).encode("utf-8")).hexdigest()
        return d

    def salva(self, caminho) -> None:
        from pathlib import Path
        Path(caminho).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
