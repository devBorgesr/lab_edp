"""
Adaptador do EDP — o primeiro cliente do servico e o proprio projeto.

MEDE EM COPIA, NUNCA NO STORE VIVO: `MemoryStore.retrieve` incrementa
`acessos`/`ultimo_acesso` e salva oportunisticamente. Auditar um sistema nao
pode alterar o sistema auditado.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path


class EDPAuditavel:
    def __init__(self, store: Path, dominios: Path | None = None,
                 copia: bool = True):
        origem = Path(store)
        if copia:
            tmp = Path(tempfile.mkdtemp(prefix="auditoria_"))
            destino = tmp / "sessions" / origem.name
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(origem, destino)
            self.snapshot_dir = destino
            self.origem = origem
        else:
            self.snapshot_dir = origem
            self.origem = origem

        self._store = self._abre(self.snapshot_dir)
        epi = json.loads((self.snapshot_dir / "episodic.json").read_text("utf-8"))
        self._txt = {e.get("id"): (e.get("text") or "") for e in epi}
        self._dom = {}
        if dominios and Path(dominios).exists():
            d = json.loads(Path(dominios).read_text("utf-8"))
            self._dom = d.get("dominios", d)

    @staticmethod
    def _abre(store: Path):
        import os
        os.environ["EDP_BASE_DIR"] = str(store.parent.parent)
        import edp.config as cfg
        cfg.BASE_DIR = store.parent.parent
        cfg.MEMORY_DIR = store.parent
        import edp.memory as mm, edp.memory.store as sm, edp.memory.semantic as sem
        mm.MEMORY_DIR = sm.MEMORY_DIR = sem.MEMORY_DIR = store.parent
        return mm.MemoryStore("default")

    def consulta(self, query: str, top_k: int) -> list[tuple[str, float]]:
        res = self._store.retrieve(query, top_k=top_k, min_score=0.0)
        return [(r.get("id"), float(r.get("ranking_score") or 0.0)) for r in res]

    def texto(self, doc_id: str) -> str:
        return self._txt.get(doc_id, "")

    def controle_para(self, q: dict) -> list[str]:
        """Documentos de outro dominio — o controle negativo pre-registrado."""
        alvo = (q.get("dominio") or "").strip().lower()
        fora = [i for i, d in self._dom.items()
                if (d or "").strip().lower() not in (alvo, "sem_tema", "")]
        return fora
