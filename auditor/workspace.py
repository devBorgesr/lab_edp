"""
Isolamento por auditoria. Um diretorio por execucao, nunca compartilhado.

    <raiz>/<audit_id>/
        input/       o que o cliente forneceu
        artifacts/   derivados
        reports/     executivo e tecnico
        manifest.json

POR QUE ISTO E SEPARADO DO PIPELINE

Contaminacao entre clientes nao e um bug que aparece em teste unitario: aparece
quando dois clientes rodam no mesmo dia e um le artefato do outro. A defesa
precisa ser estrutural — `audit_id` no caminho, criacao exclusiva, e recusa de
escrever fora da propria raiz.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Retencao por classe. O servico nao guarda dado de cliente indefinidamente,
# e cada classe tem prazo proprio porque o risco de cada uma e diferente.
RETENCAO_DIAS = {
    "input":     7,     # material bruto do cliente: o mais sensivel, sai antes
    "artifacts": 30,
    "reports":   90,
    "manifest":  365,   # a prova de que a auditoria aconteceu, e o que ela viu
}


class ForaDoWorkspace(RuntimeError):
    """Tentativa de escrever fora da raiz da propria auditoria."""


@dataclass
class Workspace:
    raiz: Path
    audit_id: str

    @classmethod
    def cria(cls, raiz_servico: Path, audit_id: str) -> "Workspace":
        r = Path(raiz_servico) / audit_id
        # A grandeza certa e o que o diretorio CONTEM, nao se ele existe
        # (NORTE §4.15). O registro de jobs grava `job.json` aqui ANTES de a
        # execucao comecar — de proposito, para que exista rastro se o processo
        # morrer. Um guard que olhava so `r.exists()` transformava esse rastro
        # em colisao e derrubava toda auditoria vinda da fila.
        #
        # O que nao pode e reaproveitar diretorio que JA ABRIGOU uma auditoria.
        ocupado = [n for n in ("input", "artifacts", "reports", "manifest.json")
                   if (r / n).exists()]
        if ocupado:
            raise ForaDoWorkspace(
                f"workspace {audit_id} ja abrigou uma auditoria (achei "
                f"{ocupado}). Reaproveitar diretorio entre auditorias e como "
                f"um cliente ler artefato do outro."
            )
        for sub in ("input", "artifacts", "reports"):
            (r / sub).mkdir(parents=True)
        return cls(r, audit_id)

    def caminho(self, sub: str, nome: str) -> Path:
        """Resolve DENTRO da raiz, e recusa qualquer coisa que escape."""
        alvo = (self.raiz / sub / nome).resolve()
        if not str(alvo).startswith(str(self.raiz.resolve())):
            raise ForaDoWorkspace(f"{alvo} esta fora de {self.raiz}")
        alvo.parent.mkdir(parents=True, exist_ok=True)
        return alvo

    def grava(self, sub: str, nome: str, conteudo: str) -> Path:
        p = self.caminho(sub, nome)
        p.write_text(conteudo, encoding="utf-8")
        return p

    def grava_json(self, sub: str, nome: str, obj: Any) -> Path:
        return self.grava(sub, nome,
                          json.dumps(obj, ensure_ascii=False, indent=2, default=str))

    # ── retencao ────────────────────────────────────────────────────────────

    def politica_de_retencao(self) -> dict[str, Any]:
        return {"dias_por_classe": dict(RETENCAO_DIAS),
                "nota": ("o servico nao guarda material do cliente "
                         "indefinidamente; `input` e a classe mais sensivel e "
                         "expira primeiro")}

    @staticmethod
    def expira(raiz_servico: Path, agora: datetime | None = None,
               executar: bool = False) -> list[dict[str, Any]]:
        """
        O que ja passou do prazo. `executar=False` (default) so LISTA.

        Apagar dado de cliente e irreversivel; o default e dizer o que seria
        apagado, e quem apaga decide.
        """
        agora = agora or datetime.now(timezone.utc)
        fora: list[dict[str, Any]] = []
        raiz = Path(raiz_servico)
        if not raiz.exists():
            return fora
        for aud in sorted(p for p in raiz.iterdir() if p.is_dir()):
            for sub, dias in RETENCAO_DIAS.items():
                alvo = aud / sub if sub != "manifest" else aud / "manifest.json"
                if not alvo.exists():
                    continue
                idade = agora - datetime.fromtimestamp(
                    alvo.stat().st_mtime, tz=timezone.utc)
                if idade > timedelta(days=dias):
                    fora.append({"audit_id": aud.name, "classe": sub,
                                 "idade_dias": idade.days, "limite": dias,
                                 "removido": executar})
                    if executar:
                        shutil.rmtree(alvo) if alvo.is_dir() else alvo.unlink()
        return fora
