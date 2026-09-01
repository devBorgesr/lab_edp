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
from .esquemas import RESULTADO_VERSAO
from .estados import AuditoriaBloqueada, Estado, StatusAuditoria


def _versao() -> str:
    """Uma fonte so. Versao divergente entre manifesto e pacote e um manifesto
    que mente sobre quem o produziu."""
    from . import __version__
    return __version__


VERSAO_SERVICO = _versao()


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
    protocolo_spec: dict[str, Any] = field(default_factory=dict)
    medicoes:   list[Any] = field(default_factory=list)   # Medicao, descritivas
    custos:     dict[str, Any] = field(default_factory=dict)
    configuracao: dict[str, Any] = field(default_factory=dict)
    privacidade: dict[str, Any] = field(default_factory=dict)
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

    @property
    def procedencia_ok(self) -> bool:
        """
        As medicoes descritivas dependem SO disto: o ranking e real.

        Nao dependem do status geral. Uma auditoria BLOCKED por cardinalidade
        ainda entrega duplicacao e sobreposicao medidas — e essa e a entrega
        comercial do MVP-1. O que nao pode sair de um ranking fabricado e
        NADA, e por isso o portao das medicoes e a procedencia.

        DEFEITO 31/08: a versao anterior aprovava quando os checks de
        procedencia AINDA NAO TINHAM RODADO — `all()` sobre lista vazia e True,
        e `_fecha()` roda apos CADA etapa. Medicao saia calculada sobre ranking
        fabricado, que e precisamente o que esta propriedade existe para
        impedir. Agora os checks exigidos precisam estar PRESENTES e PASS.
        """
        EXIGIDOS = {"ranking.veio_do_retriever", "procedencia.snapshot_tem_hash"}
        por_nome = {c.nome: c for c in self.checks}
        if not EXIGIDOS <= set(por_nome):
            return False
        return all(por_nome[n].estado is Estado.PASS for n in EXIGIDOS)

    def publica_medicoes(self, ms: list[Any]) -> None:
        """Medicao descritiva: exige ranking real, NAO exige protocolo satisfeito."""
        if not self.procedencia_ok:
            raise AuditoriaBloqueada(
                "medicao descritiva exige ranking com procedencia provada; "
                "medir sobre ranking fabricado nao mede nada"
            )
        self.medicoes = list(ms)

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
            # O artefato PERSISTIDO precisa se descrever. Sem isto o
            # `manifest.json` em disco nao dizia qual contrato cumpre — e era
            # justamente ele que a API servia como `AuditResult v1`.
            "schema":    RESULTADO_VERSAO,
            "audit_id":  self.audit_id,
            "protocolo": self.protocolo,
            "protocolo_spec": self.protocolo_spec,
            "protocolo_identidade": self.protocolo_spec.get(
                "identidade", self.protocolo),
            "versao_servico": VERSAO_SERVICO,
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
            # DESCRITIVAS — existem sob BLOCKED. Nao sao metrica de protocolo.
            "medicoes": [m.to_dict() for m in self.medicoes],
            "custos": self.custos,
            "configuracao": self.configuracao,
            "privacidade": self.privacidade,
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
        if self.medicoes:
            d["NOTA_MEDICOES"] = (
                "`medicoes` sao fatos observaveis sobre o material recuperado "
                "(duplicacao, cardinalidade, sobreposicao). NAO sao metrica de "
                "qualidade de resposta e nao substituem `resultado`."
            )
        d["sha256_manifesto"] = hashlib.sha256(
            json.dumps({k: v for k, v in d.items()},
                       sort_keys=True, ensure_ascii=False, default=str
                       ).encode("utf-8")).hexdigest()
        return d

    def salva(self, caminho, politica=None) -> None:
        """
        ULTIMA BARREIRA antes de persistir (item 9).

            objeto -> sanitizacao -> verificacao -> persistencia

        A sanitizacao roda aqui, no unico ponto por onde o manifesto vira
        arquivo, e nao em cada chamador. Segredo que escape de um campo que
        ninguem previu ainda passa por esta varredura — e se sobrar algum, a
        gravacao FALHA em vez de escrever.
        """
        from pathlib import Path

        from .redacao import Politica, varre_segredos

        pol = politica or Politica()
        d = pol.sanitiza(self.to_dict())
        d["privacidade"] = pol.relatorio()
        # o hash precisa cobrir o que foi REALMENTE gravado
        d["sha256_manifesto"] = hashlib.sha256(
            json.dumps({k: v for k, v in d.items() if k != "sha256_manifesto"},
                       sort_keys=True, ensure_ascii=False, default=str
                       ).encode("utf-8")).hexdigest()

        texto = json.dumps(d, ensure_ascii=False, indent=2, default=str)
        restou = varre_segredos(texto)
        if restou:
            raise RuntimeError(
                f"segredo sobreviveu a sanitizacao do manifesto: {restou}. "
                f"Nao gravo — vazamento e irreversivel."
            )
        Path(caminho).write_text(texto, encoding="utf-8")
        return d
