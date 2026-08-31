"""
Adaptador FAISS — sistema externo real, escrito para medir custo de adaptacao.

NAO e demonstracao: e o instrumento do item 2 do piloto. O que ele custa para
existir E o dado.

O QUE O FAISS ENTREGA, MEDIDO (faiss 1.14.3)

    index.search(q, k) -> (D, I)
      D  scores, float32
      I  POSICOES INTERNAS do indice, nao ids do cliente

Duas lacunas em relacao ao contrato `SistemaAuditavel`:

  1. NAO HA ID. `I` sao posicoes; o mapeamento posicao->id do cliente e
     responsabilidade de quem integra. Se o cliente reindexar sem preservar a
     ordem, os ids mudam de significado em silencio.

  2. A DIRECAO DO SCORE DEPENDE DO INDICE. Medido:
        IndexFlatIP  nao-crescente, positivo   -> satisfaz o contrato
        IndexFlatL2  CRESCENTE, primeiro = 0.0 -> viola os dois requisitos
     Um cliente com L2 reprova em `ranking.veio_do_retriever`, e a conversao
     distancia->similaridade precisa ser DECLARADA, nao improvisada.
"""
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from auditor.contrato import SistemaAuditavel


class FaissAuditavel(SistemaAuditavel):
    VERSAO = "faiss-1"
    nome = "FAISS"

    def __init__(self, corpus: dict[str, str], vetores: np.ndarray,
                 snapshot: Path, metrica: str = "ip"):
        self.ids = list(corpus)
        self.docs = corpus
        self.metrica = metrica
        v = np.ascontiguousarray(vetores.astype("float32"))
        if metrica == "ip":
            faiss.normalize_L2(v)
            self.index = faiss.IndexFlatIP(v.shape[1])
        else:
            self.index = faiss.IndexFlatL2(v.shape[1])
        self.index.add(v)
        self.vet = v

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
        D, I = self.index.search(self.vet[qi:qi + 1], min(top_k, len(self.ids)))
        saida = []
        for pos, sc in zip(I[0], D[0]):
            if pos < 0:
                continue
            s = float(sc)
            if self.metrica != "ip":
                # CONVERSAO DECLARADA distancia -> similaridade. Monotona
                # decrescente, entao a ORDEM do FAISS e preservada; o que muda
                # e a escala. Sem isto o contrato reprova, e com uma conversao
                # nao-monotona o ranking mudaria em silencio.
                s = 1.0 / (1.0 + s)
            saida.append((self.ids[pos], s))
        return saida

    def texto(self, doc_id: str) -> str:
        return self.docs.get(doc_id, "")

    def controle_para(self, q: dict) -> list[str]:
        return self.ids[-20:]
