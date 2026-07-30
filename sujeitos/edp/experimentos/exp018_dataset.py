#!/usr/bin/env python3
"""
sujeitos.edp.experimentos.exp018_dataset — dataset CONGELADO do §8 de
docs/preregistro_experimento_018.md. Função pura, ZERO import de `edp` —
só stdlib + numpy (numpy não é `edp`, é dependência numérica genérica já
usada pelo próprio `edp.consolidation`).

Cada condição planta entries sintéticas (nunca de store real — §8: "o
experimento não depende do conteúdo de produção, só da mecânica"):
    C1/C2 : consolidate()              — 4 tóxicas, acessos=3, flag 1/0
    C3/C4 : consolidate_promote_only()  — 4 tóxicas, acessos=3, flag 1/0
    C5    : controle + (ambas funções)  — 2 normais, SEM a chave answer_class
    C6    : controle − (ambas funções)  — 4 tóxicas, acessos=2 (abaixo do threshold)
    C7    : decisiva de H3 — consolidate() — A(tóxica, acessos=2) + B(normal,
            acessos=2), embeddings construídos para cosseno > CLUSTER_THRESH_ALVO

IDs: uuid4 FIXOS (gerados uma vez, hardcoded abaixo em `IDS`) — nunca
regenerados em runtime, para que a rodada seja reprodutível e os ids
citáveis no relatório (T6).

Embeddings: C1-C6 determinísticos por hash SHA-256 do texto (nunca
aleatórios entre execuções — mesmo texto ⇒ mesmo vetor sempre). C7 é a
exceção do §8: vetor BASE determinístico (hash do texto de A) + PERTURBAÇÃO
determinística pequena (hash de uma string fixa), somados e renormalizados
— constrói B a partir de A, não do hash do próprio texto de B, para atingir
o cosseno alvo por construção. `cosseno_c7()` recalcula o valor REAL a
partir dos vetores plantados (nunca hardcoded) — é a prova exigida pelo §5
de que a condição foi montada como pedido.

Achado do T1 (docs/RELATORIO_EXP018_T1.md, item d): `SemanticMemory.promote()`
tem um guard anterior (Dívida #49) que recusa promover texto que bata frases
EXATAS de "confiança alta" do echo_chamber ("não consigo responder", "além
do que posso afirmar com honestidade", "esgotei o método disponível"). Os
textos abaixo evitam essas frases de propósito — senão um não-promover
observado seria confundido com essa dívida, não com a ausência de guarda de
toxicidade que o experimento mede.
"""
from __future__ import annotations

import hashlib

import numpy as np

# ── Constantes congeladas (§11), espelhadas LITERALMENTE ─────────────────────
PROMOTE_THRESHOLD = 3
ACESSOS_TRATAMENTO = 3
ACESSOS_CONTROLE_NEG = 2
ACESSOS_C7_CADA = 2
ANSWER_CLASS_TOXICO = ["not_found", "disqualification"]
N_TOXICAS_POR_CONDICAO = 4
N_NORMAIS_C5 = 2
CLUSTER_THRESH_ALVO = 0.80
SCOPE = "cognitive"
EMBED_DIM = 384  # config.py:24 do edp_v5 (all-MiniLM-L6-v2) — confirmado no T1

CONDICOES = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")

# Peso da perturbação determinística de C7 (ver módulo docstring). Escolhido
# por experimentação numérica (não sensível ao resultado): dá cosseno real
# ≈ 0.84 — folga confortável acima de 0.80 sem ser quase-idêntico a 1.0.
_ALPHA_PERTURBACAO_C7 = 0.68

# ── IDs fixos (uuid4 gerados uma vez; NUNCA regenerar em runtime) ────────────
IDS = {
    ("C1", "nf1"): "f25c4cbd-2654-4868-8a30-a53ca903fe04",
    ("C1", "nf2"): "dcb589f8-ea0d-41ed-875e-b0521e023b85",
    ("C1", "dq1"): "1c490a9d-1238-4392-99ad-b2e52cf9898d",
    ("C1", "dq2"): "cf4c4439-4148-4250-b252-e76b002727f5",
    ("C2", "nf1"): "3e38e8b3-ddcf-4af4-8a34-e0779d37883e",
    ("C2", "nf2"): "758d3928-458b-46a4-acb4-71f9dda49c23",
    ("C2", "dq1"): "48c5d74a-7bff-46d7-ad3a-5ff92bd76f39",
    ("C2", "dq2"): "bcd32d95-c4ca-4ec5-8566-27994eac045f",
    ("C3", "nf1"): "664066fc-7061-4249-8ad4-d68b6cf6dd2c",
    ("C3", "nf2"): "a7ebb451-1cc8-4c1e-a6b4-01b866b59852",
    ("C3", "dq1"): "96ce2ecd-e6c9-4e53-af6c-a6ef43a68a54",
    ("C3", "dq2"): "cb34c93f-45e3-4100-94a0-181c8946af0d",
    ("C4", "nf1"): "2386c4ef-0e22-4092-8fdf-f7f85c5b37ea",
    ("C4", "nf2"): "b028e32b-cc1a-4538-965e-c03caaf00131",
    ("C4", "dq1"): "29c82282-78dd-411c-a772-1f53e5b3d056",
    ("C4", "dq2"): "d3176ae2-9d3d-4d01-84d8-65cd733cdb34",
    ("C5", "n1"): "d9ba2ef8-09cc-4cc0-b0be-1379ecf35346",
    ("C5", "n2"): "abdf65b1-dc81-4aec-bc24-ca9f628eb2b4",
    ("C6", "nf1"): "aaafce99-c564-443f-b57a-26a295269355",
    ("C6", "nf2"): "6a988b8e-2e03-4fca-8ec1-db78e74e3368",
    ("C6", "dq1"): "027e0563-5140-4bdd-9fa9-2de4a015e70c",
    ("C6", "dq2"): "590a185e-b8f7-4263-ab91-353aa4c93cb3",
    ("C7", "A"): "a1259514-a5d5-4a67-a5e7-72151d37e150",
    ("C7", "B"): "f693a301-6e3a-43b5-b004-d1cd8041d2dd",
}


def _embedding_from_text(text: str, dim: int = EMBED_DIM) -> list:
    """Determinístico por hash SHA-256 do texto — nunca aleatório entre
    execuções. Vetor unitário (norma 1), dimensão real do EDP (384)."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big")
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim)
    v = v / np.linalg.norm(v)
    return v.tolist()


def _texto(condicao: str, slot: str, papel: str) -> str:
    """Texto distinto por condição (prefixo `[exp018-C{n}]`) e por papel
    (not_found / disqualification / normal) — rastreia qual promoveu.
    Evita de propósito as frases de "confiança alta" do echo_chamber
    (T1, item d)."""
    corpo = {
        "not_found": f"item consultado nao encontrado no indice (slot {slot})",
        "disqualification": f"resposta desqualificada por criterio auto-referente (slot {slot})",
        "normal": f"conteudo consolidavel sobre o assunto do slot {slot}",
    }[papel]
    return f"[exp018-{condicao}] {corpo}."


def _entry(id_: str, text: str, answer_class, acessos: int, embedding: list,
           timestamp: int, prioridade: str = "media") -> dict:
    entry = {
        "id": id_,
        "text": text,
        "acessos": acessos,
        "embedding": embedding,
        "prioridade": prioridade,
        "timestamp": timestamp,
        "layer": "episodic",
    }
    if answer_class is not None:
        entry["answer_class"] = answer_class
    return entry


def _quatro_toxicas(condicao: str, acessos: int) -> list:
    """2 `not_found` + 2 `disqualification` — §8: ambas as classes tóxicas
    plantadas, mesmo custo."""
    slots = [
        ("nf1", "not_found"), ("nf2", "not_found"),
        ("dq1", "disqualification"), ("dq2", "disqualification"),
    ]
    out = []
    for i, (slot, papel) in enumerate(slots):
        texto = _texto(condicao, slot, papel)
        out.append(_entry(
            id_=IDS[(condicao, slot)],
            text=texto,
            answer_class=papel,
            acessos=acessos,
            embedding=_embedding_from_text(texto),
            timestamp=1000 + i,
        ))
    return out


def _duas_normais_c5() -> list:
    out = []
    for i, slot in enumerate(("n1", "n2")):
        texto = _texto("C5", slot, "normal")
        out.append(_entry(
            id_=IDS[("C5", slot)],
            text=texto,
            answer_class=None,  # §8/§3.9: chave AUSENTE, nunca None explícito no dict
            acessos=ACESSOS_TRATAMENTO,
            embedding=_embedding_from_text(texto),
            timestamp=1000 + i,
        ))
    return out


def _par_c7() -> list:
    """A (tóxica not_found, acessos=2) + B (normal, acessos=2). B é derivado
    do embedding de A por perturbação determinística pequena (módulo
    docstring) — não do hash do próprio texto de B — para garantir
    cosseno(A,B) > CLUSTER_THRESH_ALVO por construção."""
    texto_a = _texto("C7", "A", "not_found")
    texto_b = _texto("C7", "B", "normal")

    emb_a = np.array(_embedding_from_text(texto_a), dtype=np.float64)
    perturbacao = np.array(
        _embedding_from_text("[exp018-C7] vetor de perturbacao deterministico"),
        dtype=np.float64,
    )
    emb_b = emb_a + _ALPHA_PERTURBACAO_C7 * perturbacao
    emb_b = emb_b / np.linalg.norm(emb_b)

    entry_a = _entry(
        id_=IDS[("C7", "A")], text=texto_a, answer_class="not_found",
        acessos=ACESSOS_C7_CADA, embedding=emb_a.tolist(), timestamp=1000,
    )
    entry_b = _entry(
        id_=IDS[("C7", "B")], text=texto_b, answer_class=None,
        acessos=ACESSOS_C7_CADA, embedding=emb_b.tolist(), timestamp=1001,
    )
    return [entry_a, entry_b]


def build_dataset(condicao: str) -> list:
    """Dataset CONGELADO (§8) para uma condição (C1..C7). Função pura, sem
    nenhum import de `edp` — o harness (exp018.py) é quem toca o sujeito
    real; este módulo só descreve o dado plantado."""
    if condicao in ("C1", "C2", "C3", "C4"):
        return _quatro_toxicas(condicao, ACESSOS_TRATAMENTO)
    if condicao == "C5":
        return _duas_normais_c5()
    if condicao == "C6":
        return _quatro_toxicas(condicao, ACESSOS_CONTROLE_NEG)
    if condicao == "C7":
        return _par_c7()
    raise ValueError(f"condicao desconhecida: {condicao!r} (esperado uma de {CONDICOES})")


def cosseno_c7() -> float:
    """Recalcula o cosseno REAL entre A e B de C7 a partir dos embeddings
    plantados (nunca hardcoded) — prova exigida pelo §5 de que a condição
    foi montada como pedido."""
    a, b = build_dataset("C7")
    va = np.array(a["embedding"], dtype=np.float64)
    vb = np.array(b["embedding"], dtype=np.float64)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))
