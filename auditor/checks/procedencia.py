"""
Checks de procedencia. Nasceram de uma pergunta que nao teve resposta.

Ao investigar a invalidacao 01, o `pares_congelados.json` nao registrava de qual
store havia saido — e ha 17 stores em `edp_data_todo/`. Levou quatro medicoes
para identificar o certo. "Qual corpus produziu este numero" nao pode depender
da memoria de quem executou.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..estados import Estado
from .base import Resultado

CAMPOS = ("store", "sha256_episodic", "ranking_origem", "top_k")


def sha256_de(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def artefato_e_auditavel(art: dict, rotulo: str = "artefato") -> Resultado:
    """
    Recusa artefato marcado INVALIDO e artefato sem procedencia.

    A marca `INVALIDO` no JSON e decorativa sem este check: quem roda o proximo
    comando nao le o cabecalho do arquivo antes.
    """
    D = "artefato invalidado sendo reaproveitado como dado, ou dado orfao de corpus"
    N = "procedencia.artefato_e_auditavel"

    if art.get("INVALIDO"):
        return Resultado(N, Estado.INVALID, D,
                         {"invalidado_em": art.get("invalidado_em"),
                          "documento": art.get("documento")},
                         f"{rotulo} marcado INVALIDO: {art.get('motivo')}")
    proc = art.get("procedencia") or {}
    faltando = [c for c in CAMPOS if not proc.get(c)]
    ev: dict[str, Any] = {"campos_presentes": sorted(proc), "faltando": faltando}
    if faltando:
        return Resultado(N, Estado.INVALID, D, ev,
                         f"{rotulo} sem procedencia completa; faltam: {faltando}")
    return Resultado(N, Estado.PASS, D, {**ev, "store": proc.get("store")})


def snapshot_tem_hash(store: Path) -> Resultado:
    """
    O corpus auditado esta identificado por conteudo, nao por caminho.

    §4.15 — o caminho nao move quando o arquivo muda; o sha256 move. Auditar
    `/x/edp_data` em duas datas e auditar dois corpora.
    """
    D = "corpus trocado sob o mesmo caminho entre a auditoria e a contestacao"
    N = "procedencia.snapshot_tem_hash"

    epi, sem = store / "episodic.json", store / "semantic.json"
    ev = {"store": str(store), "sha256_episodic": sha256_de(epi),
          "sha256_semantic": sha256_de(sem)}
    if not ev["sha256_episodic"]:
        return Resultado(N, Estado.BLOCKED, D, ev,
                         f"nao ha episodic.json em {store}: nada a auditar")
    return Resultado(N, Estado.PASS, D, ev)
