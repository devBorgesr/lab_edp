# Auditoria — BASICO v1

`342b892cef0c` · 2026-09-01T05:38:05+00:00

## Status

**BLOCKED**

## Protocolo

**BASICO v1** — protocolo *demonstrativo*

protocolo DEMONSTRATIVO. Serve para exercitar o pipeline e produzir demonstracao; NAO sustenta afirmacao cientifica e NAO substitui o REL-001. Nenhum resultado sob esta regua certifica coisa alguma.

> Esta régua é **demonstrativa**. Não sustenta afirmação científica e não certifica nada.

## Por que bloqueou

- **`ranking.cardinalidade`** — sob o protocolo BASICO v1: 24 de 24 queries nao alcancam os 10 documentos distintos que ELE exige (min=4, mediana=4.0, max=4). Os slots estao cheios; os documentos, nao. Isto NAO diz que o sistema e inauditavel — diz que esta regua nao se aplica a ele.

`BLOCKED` significa que **o protocolo BASICO v1 não pôde ser executado sobre este sistema**. Não é uma falha do serviço, e tampouco afirma que o sistema seja inauditável: outra régua pode se aplicar a ele.

## O que foi medido mesmo assim

Fatos observáveis sobre o material recuperado. **Não são métricas de qualidade de resposta.**

- **cardinalidade_do_ranking**: 4 documentos por query (N = 24, IC 95% [4, 4])
- **duplicacao_intra_query_por_id**: 0,6 fracao dos slots (N = 24, IC 95% [0.6, 0.6])
- **duplicacao_por_texto**: 0 fracao dos documentos distintos (N = 24, IC 95% [0, 0])
- **jaccard_cross_query**: 0 Jaccard entre pares de queries (N = 276, IC 95% [0, 0])
- **razao_score_topo_cauda**: 1,032 razao adimensional (N = 24, IC 95% [1.032, 1.032])

## O que NÃO foi medido

Nenhuma métrica de protocolo do BASICO v1 foi calculada — sem Recall@K, sem índice de acordo, sem *ground truth*.

Etapas não executadas: `estratos`, `amostragem`, `julgadores`, `estatistica`.

As medições acima descrevem o material recuperado. Elas **não** autorizam afirmação sobre a qualidade das respostas do sistema.

## Qual decisão está pendente

Entre **alterar o objeto auditado** e **alterar a régua**. As duas mudam o que está sendo medido; nenhuma pode ser adotada em silêncio, e a escolha não é do serviço.

---

Evidência detalhada em `relatorio_tecnico.md`. **Fonte de verdade: `manifesto.json`** (`f1ea0a30996643f0…`) — tudo neste documento está representado lá.