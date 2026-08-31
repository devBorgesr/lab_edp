# Auditoria — REL-001 v1

`e29d1d53376d` · 2026-08-31T21:43:17+00:00

## Status

**BLOCKED**

## Protocolo

**REL-001 v1** — protocolo *experimental*

regua do experimento REL-001. Exige 50 documentos DISTINTOS no ranking porque a cauda sai das posicoes 20-50. O experimento esta BLOQUEADO: nenhum resultado seu foi validado.

## Por que bloqueou

- **`ranking.cardinalidade`** — sob o protocolo REL-001 v1: 50 de 50 queries nao alcancam os 50 documentos distintos que ELE exige (min=30, mediana=37.0, max=41). Os slots estao cheios; os documentos, nao. Isto NAO diz que o sistema e inauditavel — diz que esta regua nao se aplica a ele.

`BLOCKED` significa que **o protocolo REL-001 v1 não pôde ser executado sobre este sistema**. Não é uma falha do serviço, e tampouco afirma que o sistema seja inauditável: outra régua pode se aplicar a ele.

## O que foi medido mesmo assim

Fatos observáveis sobre o material recuperado. **Não são métricas de qualidade de resposta.**

- **cardinalidade_do_ranking**: 37 documentos por query (N = 50, IC 95% [37, 38])
- **duplicacao_intra_query_por_id**: 0,26 fracao dos slots (N = 50, IC 95% [0.24, 0.26])
- **duplicacao_por_texto**: 0 fracao dos documentos distintos (N = 50, IC 95% [0, 0])
- **jaccard_cross_query**: 0,283 Jaccard entre pares de queries (N = 1225, IC 95% [0.2759, 0.2903])
- **razao_score_topo_cauda**: 1,814 razao adimensional (N = 50, IC 95% [1.75, 1.858])

## O que NÃO foi medido

Nenhuma métrica de protocolo do REL-001 v1 foi calculada — sem Recall@K, sem índice de acordo, sem *ground truth*.

Etapas não executadas: `estratos`, `amostragem`, `julgadores`, `estatistica`.

As medições acima descrevem o material recuperado. Elas **não** autorizam afirmação sobre a qualidade das respostas do sistema.

## Qual decisão está pendente

Entre **alterar o objeto auditado** e **alterar a régua**. As duas mudam o que está sendo medido; nenhuma pode ser adotada em silêncio, e a escolha não é do serviço.

---

Evidência detalhada em `relatorio_tecnico.md`. **Fonte de verdade: `manifesto.json`** (`ae7b5f037fd21124…`) — tudo neste documento está representado lá.