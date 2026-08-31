# Auditoria — DIAGNOSTICO v1

`400f691a3fa6` · 2026-08-31T23:34:38+00:00

## Status

**COMPLETE**

## Protocolo

**DIAGNOSTICO v1** — protocolo *demonstrativo*

Descreve o MATERIAL que o retriever devolve: cardinalidade, duplicacao por id e por texto, sobreposicao entre queries e distribuicao de score. NAO mede qualidade de resposta, nao usa estratos, nao usa controle negativo e nao certifica nada. Exige apenas que o ranking tenha procedencia provada.

> Esta régua é **demonstrativa**. Não sustenta afirmação científica e não certifica nada.

## O que foi medido

Fatos observáveis sobre o material recuperado. **Não são métricas de qualidade de resposta.**

- **cardinalidade_do_ranking**: 37 documentos por query (N = 50, IC 95% [37, 38])
- **duplicacao_intra_query_por_id**: 0,26 fracao dos slots (N = 50, IC 95% [0.24, 0.26])
- **duplicacao_por_texto**: 0 fracao dos documentos distintos (N = 50, IC 95% [0, 0])
- **jaccard_cross_query**: 0,283 Jaccard entre pares de queries (N = 1225, IC 95% [0.2759, 0.2903])
- **razao_score_topo_cauda**: 1,814 razao adimensional (N = 50, IC 95% [1.75, 1.858])

## O que NÃO foi medido

O DIAGNOSTICO v1 tem **escopo de diagnóstico**: ele descreve o material que o retriever devolveu, e mais nada.

**Não foi medido, e este relatório não permite afirmar:**

- qualidade das respostas do sistema;
- Recall@K, precisão, ou qualquer métrica que compare o recuperado com um conjunto de referência;
- relevância dos documentos para as perguntas — nenhum julgamento, humano ou automático, foi feito;
- conformidade, certificação ou aprovação de qualquer espécie.

Os números acima descrevem **o que foi recuperado**, não **se o que foi recuperado era o certo**. As duas coisas são diferentes, e só a primeira está aqui.


## Qual decisão está pendente

Se algum número acima indicar desperdício — janela de contexto ocupada por documento repetido, por exemplo — a decisão sobre o que fazer é de quem opera o sistema. Este relatório mede; não recomenda correção nem estima o efeito de corrigi-la.

---

Evidência detalhada em `relatorio_tecnico.md`. **Fonte de verdade: `manifesto.json`** (`b7d4e0e02ef996c0…`) — tudo neste documento está representado lá.