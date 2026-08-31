"""
Sistemas artificiais para provar que os erros ja cometidos nao passam mais.

Cada fixture reproduz um defeito REAL do REL-001. Nao sao casos hipoteticos:
sao o que aconteceu, congelado em codigo, para que a proxima vez falhe no
pipeline em vez de falhar depois de 492 chamadas de API.
"""
from __future__ import annotations

import json
from pathlib import Path


class SistemaFalso:
    """Corpus sintetico com defeito injetavel."""

    def __init__(self, tmp: Path, n_docs: int = 120, defeito: str | None = None):
        self.defeito = defeito
        self.snapshot_dir = tmp / "sessions" / "default_cognitive"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.docs = {f"d{i:03d}": f"documento {i} sobre assunto {i % 7}"
                     for i in range(n_docs)}
        if defeito != "sem_snapshot":
            (self.snapshot_dir / "episodic.json").write_text(
                json.dumps([{"id": k, "text": v} for k, v in self.docs.items()]),
                encoding="utf-8")
            (self.snapshot_dir / "semantic.json").write_text("[]", encoding="utf-8")

    # ── o que o pipeline consome ────────────────────────────────────────────

    def consulta(self, query: str, top_k: int) -> list[tuple[str, float]]:
        ids = list(self.docs)

        if self.defeito == "ordem_de_arquivo":
            # o defeito exato da invalidacao 01: ids nus, sem score
            return ids[:top_k]                                    # type: ignore

        if self.defeito == "score_constante":
            return [(i, 0.5) for i in ids[:top_k]]

        if self.defeito == "duplicacao_de_camada":
            # 50 slots, ~30 distintos — o mesmo doc em episodic e semantic
            base = ids[:30]
            saida, n = [], 0
            while len(saida) < top_k:
                saida.append(base[n % len(base)]); n += 1
            return [(d, 0.0164 - k * 0.0001) for k, d in enumerate(saida)]

        if self.defeito == "corpus_pequeno":
            base = ids[:20]
            return [(d, 0.0164 - k * 0.0001) for k, d in enumerate(base)]

        if self.defeito == "fora_de_ordem":
            r = [(d, 0.0164 - k * 0.0001) for k, d in enumerate(ids[:top_k])]
            r[2], r[40] = r[40], r[2]
            return r

        return [(d, 0.0164 - k * 0.0001) for k, d in enumerate(ids[:top_k])]

    def texto(self, doc_id: str) -> str:
        return self.docs.get(doc_id, "")

    def controle_para(self, q: dict) -> list[str]:
        if self.defeito == "controle_no_ranking":
            # o achado de 31/08: `corpus_de_outro_dominio` devolvia documentos
            # que o proprio retriever poe no topo
            return list(self.docs)[:4]
        return list(self.docs)[-10:]


class SistemaSaudavel(SistemaFalso):
    """Caso A. O controle vem do fim do corpus, fora da janela consultada."""

    def __init__(self, tmp: Path):
        super().__init__(tmp, n_docs=120, defeito=None)

    def consulta(self, query: str, top_k: int):
        ids = [d for d in self.docs][:80]      # controle (ultimos 10) fica fora
        return [(d, 0.0164 - k * 0.0001) for k, d in enumerate(ids[:top_k])]

    @property
    def estatistica(self):
        return lambda: {"recall_at_5": 0.62, "n_queries": 3}


def queries(n: int = 3) -> list[dict]:
    return [{"id": f"q{i}", "query": f"pergunta {i} sobre assunto {i % 7}",
             "dominio": f"dom{i % 3}"} for i in range(n)]


class ClienteSintetico(SistemaFalso):
    """
    Item 11 — um cliente que parece real, sem expor dado real.

    160 documentos, 60 queries, scores decrescentes, duplicacao configuravel.
    Serve para validar o pipeline inteiro e para demonstracao comercial sem
    tocar em corpus de ninguem.
    """

    def __init__(self, tmp: Path, n_docs: int = 160,
                 taxa_duplicacao: float = 0.0):
        super().__init__(tmp, n_docs=n_docs, defeito=None)
        self.taxa_duplicacao = taxa_duplicacao
        temas = ["indexacao postgres", "acustica de sala", "arquitetura java",
                 "politica de retencao", "modelo de embeddings", "custo de infra"]
        self.docs = {
            f"doc{i:04d}": f"{temas[i % len(temas)]}: nota {i} com detalhe "
                           f"tecnico {i * 7 % 97} e contexto adicional."
            for i in range(n_docs)
        }
        (self.snapshot_dir / "episodic.json").write_text(
            json.dumps([{"id": k, "text": v} for k, v in self.docs.items()]),
            encoding="utf-8")

    # Os ultimos 20 documentos sao RESERVA DE CONTROLE: nunca entram no
    # ranking. Sem isso o proprio check `controle_fora_do_ranking` barra a
    # fixture "saudavel" — e ele estaria certo: um documento que o retriever
    # rankeia nao e controle negativo.
    N_RESERVA = 20

    def consulta(self, query: str, top_k: int) -> list[tuple[str, float]]:
        semente = sum(ord(c) for c in query)
        ids = list(self.docs)[:-self.N_RESERVA]
        # ordem estavel e dependente da query, como um retriever de verdade
        ordem = sorted(ids, key=lambda d: (semente * hash(d)) % 10007)
        base = ordem[:max(1, int(top_k * (1 - self.taxa_duplicacao)))]
        saida = []
        while len(saida) < top_k:
            saida.append(base[len(saida) % len(base)])
        return [(d, 0.0164 - k * 0.0001) for k, d in enumerate(saida[:top_k])]

    def controle_para(self, q: dict) -> list[str]:
        return list(self.docs)[-self.N_RESERVA:]


def queries_cliente(n: int = 60) -> list[dict]:
    temas = ["indexacao postgres", "acustica de sala", "arquitetura java",
             "politica de retencao", "modelo de embeddings", "custo de infra"]
    return [{"id": f"cq{i:03d}",
             "query": f"como resolver {temas[i % len(temas)]} no caso {i}?",
             "dominio": temas[i % len(temas)]} for i in range(n)]
