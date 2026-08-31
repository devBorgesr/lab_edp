"""
Adaptador cosseno puro (numpy/sklearn) — o caso mais simples possivel.

Serve de piso: se ATE ESTE custar trabalho, o problema de adaptacao e
estrutural e nao do FAISS.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from auditor.contrato import SistemaAuditavel


class CossenoAuditavel(SistemaAuditavel):
    VERSAO = "cosseno-1"
    nome = "cosseno"

    def __init__(self, corpus: dict[str, str], vetores: np.ndarray,
                 snapshot: Path):
        self.ids = list(corpus)
        self.docs = corpus
        self.vet = np.asarray(vetores, dtype="float32")
        self._snapshot = Path(snapshot) / "sessions" / "default_cognitive"
        self._snapshot.mkdir(parents=True, exist_ok=True)
        (self._snapshot / "episodic.json").write_text(
            json.dumps([{"id": i, "text": t} for i, t in corpus.items()]),
            encoding="utf-8")
        (self._snapshot / "semantic.json").write_text("[]", encoding="utf-8")

    @property
    def snapshot_dir(self) -> Path:
        return self._snapshot

    def consulta(self, query: str, top_k: int) -> list[tuple[str, float]]:
        qi = self.ids.index(query) if query in self.ids else 0
        sims = cosine_similarity(self.vet[qi:qi + 1], self.vet)[0]
        ordem = np.argsort(-sims)[:top_k]
        # cosseno pode ser <= 0 e o contrato exige score estritamente positivo.
        # Deslocamento monotono: preserva a ordem, muda so a escala.
        return [(self.ids[int(i)], float(sims[i]) + 1.0 + 1e-6) for i in ordem]

    def texto(self, doc_id: str) -> str:
        return self.docs.get(doc_id, "")

    def controle_para(self, q: dict) -> list[str]:
        return self.ids[-20:]
