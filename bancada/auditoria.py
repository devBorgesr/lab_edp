#!/usr/bin/env python3
"""
bancada.auditoria — auditoria de retrieval sobre um export JSONL. Modo export:
zero import de qualquer sujeito (nem bancada.sujeito) — a lente universal.

Portado de audit/retrieval_audit.py (edp_v5, RELATORIO_AUDIT_V1.md, ja
validado com dogfood + 16 testes). AUTOCONTIDO: zero imports de edp/bancada/
sujeitos, stdlib apenas. Unica mudanca de contrato: a chave de texto de cada
resultado e "texto" (contrato da bancada — bate com Sujeito.consultar()),
nao "text". Metricas, thresholds e logica de analise identicos ao original.

Formato de entrada CONGELADO (uma linha JSON por query):
    {"query": "...", "results": [{"id": "...", "texto": "...", "score": 0.83}, ...]}
"texto" e OBRIGATORIO em cada resultado. "id" e "score" sao OPCIONAIS — sem
"id", metricas por ID sao omitidas do relatorio (com nota); sem "score", a
analise de escala e omitida (com nota). Linhas malformadas (JSON invalido,
sem "query", "results" nao e lista) sao puladas, contadas e reportadas — o
script NUNCA crasha por dado ruim de cliente. Resultados individuais sem
"texto" utilizavel sao descartados (contados a parte) sem invalidar o resto
da linha/query.

Uso:
    python -m bancada.auditoria export.jsonl
    python -m bancada.auditoria export.jsonl --k 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

# ── Heuristicas v1 (documentadas aqui, nao sao "verdade") ───────────────────
# "Escala esmagada": sinal de que os scores nao discriminam bem entre
# resultados — thresholds escolhidos por julgamento de engenharia, nao
# calibrados estatisticamente. Revisar se o cliente reportar falso positivo.
ADJACENT_TIE_FLAG_THRESHOLD = 0.20   # fracao de empates adjacentes exatos
MEDIAN_SPREAD_FLAG_THRESHOLD = 0.10  # spread mediano relativo


def normalize_text(text) -> str:
    """strip + casefold + colapso de whitespace — a normalizacao do censo
    exp017 (scripts/censo_exp017.py, edp/memory/store.py:_normalize_text_exp017)."""
    return re.sub(r"\s+", " ", (text or "").strip().casefold())


def text_hash(text) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def truncate_query(q: str, max_len: int = 80) -> str:
    """Trunca para exibicao no relatorio, cortando em fronteira de palavra
    (nunca no meio de um token) e marcando o corte com "…"."""
    q = q.strip()
    if len(q) <= max_len:
        return q
    cut = q[:max_len]
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut.rstrip() + "…"


# ── parsing tolerante a dado ruim ───────────────────────────────────────────

class ParseResult:
    def __init__(self):
        self.records: list = []             # [{"query": str, "results": [...]}]
        self.n_malformed_lines = 0
        self.malformed_examples: list = []  # primeiras razoes, para o relatorio
        self.n_dropped_results = 0          # resultados descartados por falta de "texto"

    def add_malformed(self, reason: str):
        self.n_malformed_lines += 1
        if len(self.malformed_examples) < 5:
            self.malformed_examples.append(reason)


def parse_jsonl(path: str) -> ParseResult:
    out = ParseResult()
    # utf-8-sig: exports gerados no Windows (Set-Content -Encoding UTF8)
    # carregam BOM no inicio do arquivo — sem isso, a primeira query sai
    # suja no relatorio.
    with open(path, "r", encoding="utf-8-sig") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                out.add_malformed(f"linha {lineno}: JSON invalido ({e.msg})")
                continue
            if not isinstance(obj, dict):
                out.add_malformed(f"linha {lineno}: nao e um objeto JSON")
                continue
            query = obj.get("query")
            if not isinstance(query, str) or not query.strip():
                out.add_malformed(f"linha {lineno}: campo 'query' ausente ou vazio")
                continue
            raw_results = obj.get("results", [])
            if not isinstance(raw_results, list):
                out.add_malformed(f"linha {lineno}: campo 'results' nao e lista")
                continue

            results = []
            for item in raw_results:
                if not isinstance(item, dict):
                    out.n_dropped_results += 1
                    continue
                texto = item.get("texto")
                if not isinstance(texto, str) or not texto.strip():
                    out.n_dropped_results += 1
                    continue
                rid = item.get("id")
                rid = rid if isinstance(rid, str) and rid.strip() else None
                score = item.get("score")
                score = score if isinstance(score, (int, float)) else None
                results.append({"id": rid, "texto": texto, "score": score})

            out.records.append({"query": query, "results": results})
    return out


def _slice_top_k(results: list, top_k) -> list:
    return results[:top_k] if top_k else results


# ── duplicacao intra-query ──────────────────────────────────────────────────

def analyze_intra_query_duplication(records: list, top_k) -> dict:
    rows = []
    dup_examples: list = []
    any_id = any(r["id"] for rec in records for r in rec["results"])

    for rec in records:
        results = _slice_top_k(rec["results"], top_k)
        k = len(results)
        if k == 0:
            continue

        hashes = [text_hash(r["texto"]) for r in results]
        dup_hash_count = k - len(set(hashes))
        dup_hash_rate = dup_hash_count / k

        # exemplos de texto duplicado (para o relatorio)
        seen_hash: dict = {}
        for r, h in zip(results, hashes):
            if h in seen_hash and len(dup_examples) < 5:
                snippet = r["texto"].strip().replace("\n", " ")[:80]
                dup_examples.append(f'"{snippet}" (query: "{truncate_query(rec["query"])}")')
            seen_hash.setdefault(h, r["texto"])

        ids = [r["id"] for r in results if r["id"]]
        k_id = len(ids)
        if k_id > 0:
            dup_id_count = k_id - len(set(ids))
            dup_id_rate = dup_id_count / k_id
        else:
            dup_id_count = None
            dup_id_rate = None

        rows.append({
            "query": rec["query"], "k": k,
            "dup_hash_count": dup_hash_count, "dup_hash_rate": dup_hash_rate,
            "dup_id_count": dup_id_count, "dup_id_rate": dup_id_rate,
        })

    hash_rates = [r["dup_hash_rate"] for r in rows]
    id_rates = [r["dup_id_rate"] for r in rows if r["dup_id_rate"] is not None]

    worst_hash = max(rows, key=lambda r: r["dup_hash_rate"]) if rows else None
    worst_id = max(
        (r for r in rows if r["dup_id_rate"] is not None),
        key=lambda r: r["dup_id_rate"], default=None,
    )

    return {
        "rows": rows,
        "any_id": any_id,
        "avg_dup_hash_rate": statistics.mean(hash_rates) if hash_rates else None,
        "worst_hash": worst_hash,
        "avg_dup_id_rate": statistics.mean(id_rates) if id_rates else None,
        "worst_id": worst_id,
        "dup_examples": dup_examples,
        "n_queries_sem_id": sum(1 for r in rows if r["dup_id_rate"] is None),
    }


# ── repeticao cross-query ───────────────────────────────────────────────────

def _identity(r: dict) -> str:
    """id quando disponivel, senao hash do texto normalizado (fallback
    documentado: sem id nao existe outra chave de identidade estavel)."""
    return r["id"] if r["id"] else text_hash(r["texto"])


def analyze_cross_query_repetition(records: list, top_k) -> dict:
    query_sets = []
    for rec in records:
        results = _slice_top_k(rec["results"], top_k)
        if not results:
            continue
        query_sets.append((rec["query"], {_identity(r) for r in results}, len(results)))

    n = len(query_sets)
    if n < 2:
        return {"n_queries": n, "insufficient": True}

    # matriz completa par-a-par (i<j), continua e binaria
    matrix = {}
    for i in range(n):
        for j in range(i + 1, n):
            _, set_i, k_i = query_sets[i]
            _, set_j, k_j = query_sets[j]
            k_pair = min(k_i, k_j)
            overlap = len(set_i & set_j)
            frac = overlap / k_pair if k_pair else 0.0
            threshold = min(2, k_pair)
            binary = overlap >= threshold if k_pair else False
            matrix[(i, j)] = {"overlap": overlap, "k_pair": k_pair, "frac": frac, "binary": binary}

    all_pairs = list(matrix.values())
    total_pairs = len(all_pairs)
    ref_binary_rate = sum(1 for p in all_pairs if p["binary"]) / total_pairs if total_pairs else None
    ref_continuous_mean = statistics.mean(p["frac"] for p in all_pairs) if all_pairs else None

    # pares CONSECUTIVOS na ordem do arquivo — CAVEAT: a ordem do export
    # determina o que "consecutivo" significa aqui, nao ha ordem canonica.
    consecutive = []
    for i in range(n - 1):
        q_i, _, _ = query_sets[i]
        q_j, _, _ = query_sets[i + 1]
        p = matrix[(i, i + 1)]
        consecutive.append({"query_a": q_i, "query_b": q_j, **p})

    n_cons = len(consecutive)
    cons_binary_rate = sum(1 for p in consecutive if p["binary"]) / n_cons if n_cons else None
    cons_continuous_mean = statistics.mean(p["frac"] for p in consecutive) if n_cons else None

    show_full_matrix = n <= 15

    return {
        "n_queries": n,
        "insufficient": False,
        "consecutive": consecutive,
        "cons_binary_rate": cons_binary_rate,
        "cons_continuous_mean": cons_continuous_mean,
        "ref_binary_rate": ref_binary_rate,
        "ref_continuous_mean": ref_continuous_mean,
        "total_pairs": total_pairs,
        "show_full_matrix": show_full_matrix,
        "matrix": matrix if show_full_matrix else None,
        "query_labels": [q for q, _, _ in query_sets],
        "off_diag_min": min((p["frac"] for p in all_pairs), default=None),
        "off_diag_max": max((p["frac"] for p in all_pairs), default=None),
    }


# ── escala de score ──────────────────────────────────────────────────────────

def analyze_score_scale(records: list, top_k) -> dict:
    rows = []
    any_score = any(r["score"] is not None for rec in records for r in rec["results"])
    total_adjacent_pairs = 0
    total_tied_pairs = 0

    for rec in records:
        results = _slice_top_k(rec["results"], top_k)
        scores = [r["score"] for r in results if r["score"] is not None]
        if len(scores) < 2:
            continue

        mx, mn = max(scores), min(scores)
        spread = (mx - mn) / mx if mx else 0.0

        adjacent_pairs = len(scores) - 1
        tied = sum(1 for a, b in zip(scores, scores[1:]) if a == b)
        total_adjacent_pairs += adjacent_pairs
        total_tied_pairs += tied

        rows.append({
            "query": rec["query"], "k": len(scores),
            "spread": spread, "tied_adjacent": tied, "adjacent_pairs": adjacent_pairs,
        })

    spreads = [r["spread"] for r in rows]
    median_spread = statistics.median(spreads) if spreads else None
    tie_fraction = (total_tied_pairs / total_adjacent_pairs) if total_adjacent_pairs else None

    flagged = False
    if tie_fraction is not None and tie_fraction > ADJACENT_TIE_FLAG_THRESHOLD:
        flagged = True
    if median_spread is not None and median_spread < MEDIAN_SPREAD_FLAG_THRESHOLD:
        flagged = True

    return {
        "rows": rows,
        "any_score": any_score,
        "median_spread": median_spread,
        "avg_spread": statistics.mean(spreads) if spreads else None,
        "tie_fraction": tie_fraction,
        "flagged": flagged,
        "n_queries_sem_score": sum(
            1 for rec in records if not any(r["score"] is not None for r in _slice_top_k(rec["results"], top_k))
        ),
    }


# ── relatorio Markdown ───────────────────────────────────────────────────────

def _pct(x) -> str:
    return f"{x * 100:.1f}%" if x is not None else "N/D"


def build_report(parse: ParseResult, dup: dict, rep: dict, scale: dict, top_k) -> str:
    k_desc = str(top_k) if top_k else "tamanho de cada export (sem truncamento)"
    n_queries = len(parse.records)

    achados = []
    if dup["avg_dup_hash_rate"] is not None:
        achados.append(
            f"- Em media, **{_pct(dup['avg_dup_hash_rate'])}** dos resultados de cada busca "
            f"sao textos duplicados (mesmo conteudo, presenca repetida no mesmo retorno)."
        )
    if dup["worst_hash"] is not None and dup["worst_hash"]["dup_hash_rate"] > 0:
        w = dup["worst_hash"]
        impacto = (
            f" Na pior busca, {w['dup_hash_count']} de cada {w['k']} resultados eram repeticao "
            f"do mesmo texto — tokens pagos em dobro ocupando o lugar de conteudo novo."
        )
        achados.append(
            f"- Pior caso: a busca \"{truncate_query(w['query'])}\" retornou "
            f"{_pct(w['dup_hash_rate'])} de conteudo duplicado.{impacto}"
        )
    if not rep.get("insufficient") and rep["cons_continuous_mean"] is not None:
        linha = (
            f"- Buscas consecutivas no export compartilham em media "
            f"**{_pct(rep['cons_continuous_mean'])}** dos resultados (referencia sob "
            f"aleatoriedade: {_pct(rep['ref_continuous_mean'])}) — isso pode ser normal "
            f"quando as buscas sao sobre o mesmo assunto, nao e necessariamente falha."
        )
        if (rep["ref_continuous_mean"] is not None
                and rep["cons_continuous_mean"] > rep["ref_continuous_mean"]):
            linha += (
                " Buscas diferentes recebem as mesmas respostas — o sistema tem \"favoritos\" "
                "independentes da pergunta."
            )
        achados.append(linha)
    if scale["flagged"]:
        achados.append(
            "- **Escala de relevancia comprometida**: os scores retornados discriminam mal "
            "entre resultados bons e ruins (muitos empates e/ou pouca variacao). Os scores nao "
            "distinguem resultado bom de ruim — qualquer corte por relevancia que o sistema "
            "faca esta decidindo no escuro."
        )
    if not achados:
        achados.append("- Nenhum padrao de duplicacao, repeticao ou escala achatada saltou aos olhos nesta amostra.")
    if parse.n_malformed_lines:
        achados.append(
            f"- {parse.n_malformed_lines} linha(s) do export vieram malformadas e foram ignoradas "
            f"(ver secao de limitacoes)."
        )

    lines = []
    lines.append("# Relatorio de Auditoria de Retrieval\n")
    lines.append(
        f"Export analisado: {n_queries} queries validas, k considerado: {k_desc}.\n"
    )

    # 1. Sumario executivo
    lines.append("## 1. Sumario executivo\n")
    lines.extend(achados)
    lines.append("")

    # 2. Numeros por familia
    lines.append("## 2. Numeros por familia\n")

    lines.append("### 2a. Duplicacao intra-query\n")
    if not dup["any_id"]:
        lines.append("_Nenhum resultado trouxe campo `id` — metricas de duplicacao por ID omitidas._\n")
    lines.append("| Metrica | Valor |")
    lines.append("|---|---|")
    lines.append(f"| dup_rate@k por hash (media) | {_pct(dup['avg_dup_hash_rate'])} |")
    if dup["worst_hash"]:
        lines.append(f"| dup_rate@k por hash (pior query) | {_pct(dup['worst_hash']['dup_hash_rate'])} — \"{truncate_query(dup['worst_hash']['query'])}\" |")
    if dup["any_id"]:
        lines.append(f"| dup_rate@k por ID (media, queries com ID) | {_pct(dup['avg_dup_id_rate'])} |")
        if dup["worst_id"]:
            lines.append(f"| dup_rate@k por ID (pior query) | {_pct(dup['worst_id']['dup_id_rate'])} — \"{truncate_query(dup['worst_id']['query'])}\" |")
        if dup["n_queries_sem_id"]:
            lines.append(f"| queries sem nenhum ID presente | {dup['n_queries_sem_id']} |")
    lines.append("")
    if dup["dup_examples"]:
        lines.append("Exemplos de texto duplicado encontrado:\n")
        for ex in dup["dup_examples"]:
            lines.append(f"- {ex}")
        lines.append("")

    lines.append("### 2b. Repeticao cross-query\n")
    lines.append(
        "> **Caveat obrigatorio**: \"consecutivo\" e definido pela ORDEM DAS LINHAS no arquivo "
        "exportado — se o export nao preserva a ordem cronologica/real das buscas, esta metrica "
        "reflete a ordem do arquivo, nao necessariamente a experiencia real do usuario.\n"
    )
    if rep.get("insufficient"):
        lines.append(f"_Apenas {rep['n_queries']} query(ies) com resultados — pares insuficientes para esta analise._\n")
    else:
        lines.append("| Visao | Valor observado (pares consecutivos) | Referencia neutra (todos os pares, aleatoria) |")
        lines.append("|---|---|---|")
        lines.append(f"| Binaria (overlap >= min(2,k)) | {_pct(rep['cons_binary_rate'])} | {_pct(rep['ref_binary_rate'])} |")
        lines.append(f"| Continua (\\|∩\\|/k, media) | {_pct(rep['cons_continuous_mean'])} | {_pct(rep['ref_continuous_mean'])} |")
        lines.append("")
        lines.append(
            f"Matriz completa par-a-par: {rep['total_pairs']} pares avaliados entre "
            f"{rep['n_queries']} queries. Overlap fora-da-diagonal: min={_pct(rep['off_diag_min'])}, "
            f"max={_pct(rep['off_diag_max'])}.\n"
        )
        if rep["show_full_matrix"]:
            labels = rep["query_labels"]
            header = "| |" + "|".join(f"q{j+1}" for j in range(len(labels))) + "|"
            lines.append(header)
            lines.append("|---" * (len(labels) + 1) + "|")
            for i in range(len(labels)):
                row = [f"q{i+1}"]
                for j in range(len(labels)):
                    if j <= i:
                        row.append("")
                    else:
                        row.append(f"{rep['matrix'][(i, j)]['frac']*100:.0f}%")
                lines.append("|" + "|".join(row) + "|")
            lines.append("")
            lines.append("Legenda: " + "; ".join(f"q{i+1}=\"{truncate_query(q)}\"" for i, q in enumerate(labels)))
            lines.append("")
        else:
            lines.append(
                f"_Matriz completa omitida do relatorio impresso (>{15} queries; "
                f"calculada internamente para a referencia neutra acima)._\n"
            )

    lines.append("### 2c. Escala de score\n")
    if not scale["any_score"]:
        lines.append("_Nenhum resultado trouxe campo `score` — analise de escala omitida._\n")
    else:
        lines.append("| Metrica | Valor |")
        lines.append("|---|---|")
        lines.append(f"| Spread relativo (mediana) | {_pct(scale['median_spread'])} |")
        lines.append(f"| Spread relativo (media) | {_pct(scale['avg_spread'])} |")
        lines.append(f"| Empates exatos adjacentes (fracao dos pares) | {_pct(scale['tie_fraction'])} |")
        lines.append(f"| **Escala esmagada?** | {'SIM' if scale['flagged'] else 'nao'} |")
        if scale["n_queries_sem_score"]:
            lines.append(f"| queries sem score utilizavel | {scale['n_queries_sem_score']} |")
        lines.append("")
        lines.append(
            f"_Heuristica v1 (nao e verdade absoluta): flag disparada se empates adjacentes > "
            f"{ADJACENT_TIE_FLAG_THRESHOLD*100:.0f}% dos pares OU spread mediano < "
            f"{MEDIAN_SPREAD_FLAG_THRESHOLD*100:.0f}%. Ver `bancada/auditoria.py` (thresholds no topo do arquivo)._\n"
        )

    # 3. Interpretacao
    lines.append("## 3. O que cada numero significa\n")
    lines.append(
        "**Duplicacao intra-query** (2a) mede o mesmo conteudo aparecendo mais de uma vez "
        "dentro do retorno de UMA busca. Isso quase sempre e desperdicio: espaco de contexto "
        "e atencao do modelo gastos em repeticao, nao em cobertura. Um dup_rate@k alto e "
        "candidato forte a correcao (deduplicacao no pipeline de retrieval).\n"
    )
    lines.append(
        "**Repeticao cross-query** (2b) mede o quanto buscas diferentes retornam os mesmos "
        "documentos. Isto **nao e automaticamente um problema**: se duas perguntas seguidas sao "
        "sobre o mesmo assunto, e esperado — e correto — que tragam os mesmos documentos "
        "(topicalidade). O sinal de alerta real e quando o valor observado esta muito acima da "
        "referencia neutra (aleatoria) E as perguntas consecutivas no export nao parecem, pelo "
        "conteudo, ser sobre o mesmo tema — isso sugere que o sistema esta sempre devolvendo os "
        "mesmos itens \"populares\" independente da pergunta.\n"
    )
    lines.append(
        "**Escala de score** (2c) mede se os numeros de relevancia retornados pelo sistema "
        "realmente diferenciam bons resultados de ruins. Uma escala esmagada (pouca variacao, "
        "muitos empates) nao impede o sistema de funcionar, mas invalida qualquer uso do score "
        "para decisoes downstream (corte por threshold, priorizacao, exibicao de \"confianca\" "
        "ao usuario) — o numero deixa de carregar informacao.\n"
    )

    # 4. Limitacoes
    lines.append("## 4. Limitacoes deste diagnostico\n")
    lines.append(
        "Este relatorio analisa exclusivamente o **retorno do retrieval** (o que foi buscado e "
        "o que voltou). Ele nao permite ver, e portanto nao avalia:\n"
    )
    lines.append("- **Write-side**: como e quando os dados entraram no indice/store (a causa raiz de duplicacao pode estar na escrita, nao na busca).")
    lines.append("- **Truncamento de contexto**: se o que chega ao modelo e cortado antes ou depois destes resultados, por limite de janela de contexto.")
    lines.append("- **Qualidade da resposta final**: um retrieval limpo nao garante uma resposta boa, e um retrieval com ruido nao garante uma resposta ruim — isso depende do que o modelo faz com o material recuperado.")
    lines.append(
        f"\nLinhas malformadas no export: {parse.n_malformed_lines} "
        f"(puladas, nao processadas). Resultados individuais descartados por falta de texto "
        f"utilizavel: {parse.n_dropped_results}."
    )
    if parse.malformed_examples:
        lines.append("\nExemplos de linhas malformadas:")
        for ex in parse.malformed_examples:
            lines.append(f"- {ex}")

    return "\n".join(lines) + "\n"


def gerar_relatorio(input_path: str, top_k=None) -> str:
    """Roda o encanamento completo (parse -> 3 analises -> relatorio) e
    devolve o markdown. Determinístico para o mesmo input."""
    parse = parse_jsonl(input_path)
    dup = analyze_intra_query_duplication(parse.records, top_k)
    rep = analyze_cross_query_repetition(parse.records, top_k)
    scale = analyze_score_scale(parse.records, top_k)
    return build_report(parse, dup, rep, scale, top_k)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Auditoria de retrieval sobre export JSONL (modo export da bancada).")
    ap.add_argument("input", help='Caminho do export JSONL (formato: {"query":..., "results":[{"id","texto","score"}]})')
    ap.add_argument("--k", type=int, default=None, help="Trunca cada query aos top-k resultados antes de medir (default: usa o export como veio)")
    args = ap.parse_args(argv)

    if not Path(args.input).exists():
        print(f"[erro] arquivo nao encontrado: {args.input}", file=sys.stderr)
        return 2

    print(gerar_relatorio(args.input, args.k))
    return 0


if __name__ == "__main__":
    sys.exit(main())
