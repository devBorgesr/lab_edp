# Auditoria — DIAGNOSTICO v1

`1044b31119a7` · 2026-09-01T05:38:04+00:00

## Status

**COMPLETE**

## Protocolo

**DIAGNOSTICO v1** — protocolo *demonstrativo*

Descreve o MATERIAL que o retriever devolve: cardinalidade, duplicacao por id e por texto, sobreposicao entre queries e distribuicao de score. NAO mede qualidade de resposta, nao usa estratos, nao usa controle negativo e nao certifica nada. Exige apenas que o ranking tenha procedencia provada.

> Esta régua é **demonstrativa**. Não sustenta afirmação científica e não certifica nada.

## O que foi medido

Fatos observáveis sobre o material recuperado. **Não são métricas de qualidade de resposta.**

- **cardinalidade_do_ranking**: 20 documentos por query (N = 24, IC 95% [20, 20])
- **duplicacao_intra_query_por_id**: 0,6 fracao dos slots (N = 24, IC 95% [0.6, 0.6])
- **duplicacao_por_texto**: 0 fracao dos documentos distintos (N = 24, IC 95% [0, 0])
- **jaccard_cross_query**: 0,0811 Jaccard entre pares de queries (N = 276, IC 95% [0.0811, 0.0811])
- **razao_score_topo_cauda**: 1,385 razao adimensional (N = 24, IC 95% [1.385, 1.385])

## O que NÃO foi medido

O DIAGNOSTICO v1 tem **escopo de diagnóstico**: ele descreve o material que o retriever devolveu, e mais nada.

**Não foi medido, e este relatório não permite afirmar:**

- qualidade das respostas do sistema;
- Recall@K, precisão, ou qualquer métrica que compare o recuperado com um conjunto de referência;
- relevância dos documentos para as perguntas — nenhum julgamento, humano ou automático, foi feito;
- conformidade, certificação ou aprovação de qualquer espécie.

Os números acima descrevem **o que foi recuperado**, não **se o que foi recuperado era o certo**. As duas coisas são diferentes, e só a primeira está aqui.


## Qual decisão está pendente

O que fazer com estes números é de quem opera o sistema. Este relatório **mede o que foi recuperado**; não estima efeito sobre custo, latência ou qualidade, e não recomenda correção.

Medir esse efeito exigiria um experimento comparativo — o mesmo sistema com e sem a repetição, com desfecho definido antes — que **não foi feito**.

---

Evidência detalhada em `relatorio_tecnico.md`. **Fonte de verdade: `manifesto.json`** (`96f7e7e13835f576…`) — tudo neste documento está representado lá.