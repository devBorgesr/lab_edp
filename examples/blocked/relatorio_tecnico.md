# Auditoria `342b892cef0c` — BASICO v1

**Status: BLOCKED** · protocolo *demonstrativo* · serviço `0.2.0`

## Resumo executivo

Esta auditoria **não produziu métricas**. Uma ou mais pré-condições de validade não foram satisfeitas, e o pipeline foi interrompido antes de qualquer cálculo.

Isto não é uma falha do serviço: é o resultado que o serviço deve entregar quando o sistema auditado não sustenta o protocolo pedido.

## Motivo

**`ranking.cardinalidade` — BLOCKED**

sob o protocolo BASICO v1: 24 de 24 queries nao alcancam os 10 documentos distintos que ELE exige (min=4, mediana=4.0, max=4). Os slots estao cheios; os documentos, nao. Isto NAO diz que o sistema e inauditavel — diz que esta regua nao se aplica a ele.

```
slots = 10
ids_distintos = 4
exigido = 10
ids_repetidos = 6
queries = 24
distintos_min = 4
distintos_mediana = 4
distintos_max = 4
queries_reprovadas = 24
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
| `cardinalidade_do_ranking` | 4 | [4, 4] | 24 | documentos por query |
| `duplicacao_intra_query_por_id` | 0,6 | [0,6, 0,6] | 24 | fracao dos slots |
| `duplicacao_por_texto` | 0 | [0, 0] | 24 | fracao dos documentos distintos |
| `jaccard_cross_query` | 0 | [0, 0] | 276 | Jaccard entre pares de queries |
| `razao_score_topo_cauda` | 1,032 | [1,032, 1,032] | 24 | razao adimensional |

**`cardinalidade_do_ranking`** — documentos DISTINTOS entregues na janela top-k (mediana entre queries). Slots cheios nao implicam documentos distintos.

*N = 24 · k = 10 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_intra_query_por_id`** — fracao dos slots do top-k ocupados por um documento que ja apareceu na MESMA query (mediana entre queries)

*N = 24 · k = 10 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_por_texto`** — fracao dos documentos DISTINTOS cujo texto e identico ao de outro documento com id diferente. Sobrevive a deduplicacao por id. ATENCAO: efeito concentrado — leia `queries_afetadas`, nao a mediana.

*N = 24 · k = 10 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`jaccard_cross_query`** — Jaccard mediano entre os conjuntos top-k de PARES de queries distintas. Alto indica que o retriever devolve o mesmo material independentemente da pergunta.

*N = 276 · k = 10 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`razao_score_topo_cauda`** — score mediano das 5 primeiras posicoes dividido pelo das 5 ultimas. Proximo de 1 indica ranking pouco discriminativo.

*N = 24 · k = 10 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

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
dir = examples/blocked/_corpus/sessions/default_cognitive
store = examples/blocked/_corpus/sessions/default_cognitive
sha256_episodic = ddbc8cacc43ae37490bbc42bfab8577e166621f5056bd1b3ebcc3127b171400a
sha256_semantic = 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
retriever.top_k = 10
retriever.origem = ClienteSintetico
retriever.adaptador = ClienteSintetico
retriever.versao_adaptador = fixture-1
retriever.telemetria = {'origem_do_ranking': 'ClienteSintetico.consulta', 'top_k_solicitado': 10, 'n_slots_recebidos': 10, 'n_ids_distintos': 4, 'n_textos_distintos': 4, 'formato_valido': True}
manifesto.sha256 = f1ea0a30996643f070020fc7b492873ccfde2e1f03e704e387fbce5bdf83b5e1
```

## Custo desta auditoria

```
tempo_total_s = 0.029
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