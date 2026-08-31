# Auditoria `e01a62f36d04` — REL-001

**Status: BLOCKED**

## Resumo executivo

Esta auditoria **não produziu métricas**. Uma ou mais pré-condições de validade não foram satisfeitas, e o pipeline foi interrompido antes de qualquer cálculo.

Isto não é uma falha do serviço: é o resultado que o serviço deve entregar quando o sistema auditado não sustenta o protocolo pedido.

## Motivo

**`ranking.cardinalidade` — BLOCKED**

50 de 50 queries nao alcancam 50 documentos distintos (min=30, mediana=37.0, max=41). Os slots estao cheios; os documentos, nao.

```
slots = 50
ids_distintos = 30
exigido = 50
ids_repetidos = 20
queries = 50
distintos_min = 30
distintos_mediana = 37
distintos_max = 41
queries_reprovadas = 50
```

*Este check detecta:* duplicacao no indice consumindo a janela top-k: slots cheios, documentos distintos insuficientes

## O que NÃO foi concluído

Nenhuma métrica foi calculada. Especificamente:

- etapa `estratos` — não executada
- etapa `amostragem` — não executada
- etapa `julgadores` — não executada
- etapa `estatistica` — não executada

Qualquer número que apareça em outro lugar sobre este sistema **não veio desta auditoria**.

## Próximo passo

Decisão do responsável, entre alterar o objeto auditado e alterar o protocolo. As duas mudam o que está sendo medido e nenhuma pode ser adotada em silêncio.

## Medições

Fatos observáveis sobre o material recuperado. **Não são métricas de qualidade de resposta** e não substituem o resultado do protocolo.

| medição | valor | IC 95% | N | unidade |
|---|---|---|---|---|
| `cardinalidade_do_ranking` | 37 | [36,74, 37,86] | 50 | documentos por query |
| `duplicacao_intra_query_por_id` | 0,26 | [0,2428, 0,2652] | 50 | fracao dos slots |
| `duplicacao_por_texto` | 0 | [0,003, 0,04] | 50 | fracao dos documentos distintos |
| `sobreposicao_cross_query` | 0,283 | [0,2824, 0,2946] | 1225 | Jaccard entre pares de queries |
| `razao_score_topo_cauda` | 1,814 | [1,8, 2,039] | 50 | razao adimensional |

**`cardinalidade_do_ranking`** — documentos DISTINTOS entregues na janela top-k (mediana entre queries). Slots cheios nao implicam documentos distintos.

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_intra_query_por_id`** — fracao dos slots do top-k ocupados por um documento que ja apareceu na MESMA query (mediana entre queries)

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_por_texto`** — fracao dos documentos DISTINTOS cujo texto e identico ao de outro documento com id diferente. Sobrevive a deduplicacao por id. ATENCAO: efeito concentrado — leia `queries_afetadas`, nao a mediana.

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`sobreposicao_cross_query`** — Jaccard mediano entre os top-k de pares de queries distintas. Alto indica que o retriever devolve o mesmo material independente da pergunta.

*N = 1225 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`razao_score_topo_cauda`** — score mediano das 5 primeiras posicoes dividido pelo das 5 ultimas. Proximo de 1 indica ranking pouco discriminativo.

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

## Verificações

| check | estado | barra? | detecta |
|---|---|---|---|
| `procedencia.snapshot_tem_hash` | PASS | não | corpus trocado sob o mesmo caminho entre a auditoria e a contestacao |
| `ranking.veio_do_retriever` | PASS | não | ranking fabricado: ordem de arquivo, ordem alfabetica, ou qualquer sequencia que nao saiu do retriever |
| `ranking.cardinalidade` | BLOCKED | **sim** | duplicacao no indice consumindo a janela top-k: slots cheios, documentos distintos insuficientes |

## Etapas

| etapa | estado |
|---|---|
| `snapshot` | PASS |
| `entrada` | PASS |
| `retriever` | PASS |
| `ranking` | BLOCKED |
| `estratos` | PENDING |
| `amostragem` | PENDING |
| `julgadores` | PENDING |
| `estatistica` | PENDING |

## Procedência

```
dir = /tmp/auditoria_anpyeril/sessions/default_cognitive
store = /tmp/auditoria_anpyeril/sessions/default_cognitive
sha256_episodic = d64fcc74a0c7e9b08eb3972129a7f5689b008912c3e32abce9e386477d1703be
sha256_semantic = 632a7f228045f89cc92bf98695a4f664e181e214a93236035f0af1a635eab27d
retriever.top_k = 50
retriever.origem = EDPAuditavel
manifesto.sha256 = 89686215aafcc8b50c2b6cb1ff892aec80d2eade69a2ccfa7075c02ad8672e95
```

## Custo desta auditoria

```
tempo_total_s = 55.843
chamadas_ao_modelo = 0
tokens_entrada = 0
tokens_saida = 0
modelo = None
custo_modelo_usd = None
custo_nao_estimado_porque = sem preco registrado para o modelo (nenhum). Zero seria mentira; None e a resposta honesta.
```

## Privacidade

```
exemplos_em_claro = False
segredos_removidos = []
n_ocorrencias = 0
nota = query e documento aparecem como hash; texto em claro so com --exemplos-em-claro, e segredo e removido nos dois modos
```

---

Manifesto completo em `manifesto.json`. Modo: `AUDIT`. O sha256 acima cobre o manifesto inteiro e permite contestar cada número deste relatório.