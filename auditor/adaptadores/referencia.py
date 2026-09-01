"""
Adaptador de REFERENCIA — o menor possivel, para ser copiado.

Quatro metodos. Um sistema que implemente os quatro pode ser auditado.

    snapshot_dir      diretorio do corpus (hasheado; vira a identidade)
    consulta          [(doc_id, score), ...] na ordem do SEU retriever
    texto             o texto de um documento
    controle_para     so o protocolo BASICO usa; DIAGNOSTICO ignora

O UNICO PONTO QUE COSTUMA DAR TRABALHO E O `score`.

Ele nao e enfeite: e a prova de que o ranking saiu de um retriever, e nao de
uma lista qualquer de ids. Sem essa prova o servico recusa — porque foi
exatamente assim que este projeto perdeu 500 pares e 492 rotulos, passando
ordem de insercao de arquivo como se fosse ranking.

CONVERSOES LEGITIMAS, medidas em faiss 1.14.3:

    distancia (L2)   1/(1+d)      monotona decrescente, preserva a ordem
    cosseno <= 0     s + 1 + eps  deslocamento, preserva a ordem

Ambas mudam a ESCALA e nao a ORDEM. Declare qual usou. Inventar score nao e
conversao, e o servico barra.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Sequence

from ..contrato import SistemaAuditavel


class AdaptadorDeReferencia(SistemaAuditavel):
    """
    Envolve qualquer funcao de busca que devolva `[(doc_id, score), ...]`.

        sis = AdaptadorDeReferencia(
            corpus={"d1": "texto...", "d2": "..."},
            buscar=lambda q, k: meu_retriever.search(q, k),
            snapshot=Path("/tmp/meu_snapshot"),
        )
    """

    VERSAO = "referencia-1"
    nome = "referencia"

    def __init__(self, corpus: dict[str, str],
                 buscar: Callable[[str, int], Sequence[tuple[str, float]]],
                 snapshot: Path,
                 converte_score: Callable[[float], float] | None = None,
                 nota_da_conversao: str = ""):
        self.docs = dict(corpus)
        self._buscar = buscar
        self._conv = converte_score
        self.nota_da_conversao = nota_da_conversao
        if converte_score is not None and not nota_da_conversao:
            raise ValueError(
                "conversao de score sem nota. Declare o que foi feito — uma "
                "conversao nao-monotona mudaria o ranking em silencio, e quem "
                "le o manifesto precisa poder conferir."
            )
        self._dir = Path(snapshot) / "sessions" / "default_cognitive"
        self._dir.mkdir(parents=True, exist_ok=True)
        (self._dir / "episodic.json").write_text(
            json.dumps([{"id": i, "text": t} for i, t in self.docs.items()]),
            encoding="utf-8")
        (self._dir / "semantic.json").write_text("[]", encoding="utf-8")

    @property
    def snapshot_dir(self) -> Path:
        return self._dir

    def consulta(self, query: str, top_k: int) -> list[tuple[str, float]]:
        bruto = self._buscar(query, top_k)
        if self._conv is None:
            return [(d, float(s)) for d, s in bruto]
        return [(d, float(self._conv(float(s)))) for d, s in bruto]

    def texto(self, doc_id: str) -> str:
        return self.docs.get(doc_id, "")

    def controle_para(self, q: dict) -> list[str]:
        return []          # DIAGNOSTICO v1 nao usa controle negativo


# Conversoes prontas, com o nome do que fazem.
def de_distancia(d: float) -> float:
    """L2 -> similaridade. Monotona decrescente; preserva a ordem do indice."""
    return 1.0 / (1.0 + d)


def desloca_cosseno(s: float) -> float:
    """Cosseno pode ser <= 0; o contrato exige > 0. Deslocamento puro."""
    return s + 1.0 + 1e-6
