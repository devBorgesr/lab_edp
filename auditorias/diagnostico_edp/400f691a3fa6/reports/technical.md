# Auditoria `400f691a3fa6` — DIAGNOSTICO v1

**Status: COMPLETE** · protocolo *demonstrativo* · serviço `0.2.0`

## Resultado

- **escopo**: diagnostico do material recuperado
- **medicoes**: {'cardinalidade_do_ranking': 37.0, 'duplicacao_intra_query_por_id': 0.26, 'duplicacao_por_texto': 0.0, 'jaccard_cross_query': 0.2830188679245283, 'razao_score_topo_cauda': 1.813556866722796}
- **NAO_AFIRMA**: nada sobre a qualidade das respostas do sistema. Sem Recall@K, sem ground truth, sem certificacao.

## Medições

Fatos observáveis sobre o material recuperado. **Não são métricas de qualidade de resposta** e não substituem o resultado do protocolo.

| medição | valor | IC 95% | N | unidade |
|---|---|---|---|---|
| `cardinalidade_do_ranking` | 37 | [37, 38] | 50 | documentos por query |
| `duplicacao_intra_query_por_id` | 0,26 | [0,24, 0,26] | 50 | fracao dos slots |
| `duplicacao_por_texto` | 0 | [0, 0] | 50 | fracao dos documentos distintos |
| `jaccard_cross_query` | 0,283 | [0,2759, 0,2903] | 1225 | Jaccard entre pares de queries |
| `razao_score_topo_cauda` | 1,814 | [1,75, 1,858] | 50 | razao adimensional |

**`cardinalidade_do_ranking`** — documentos DISTINTOS entregues na janela top-k (mediana entre queries). Slots cheios nao implicam documentos distintos.

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_intra_query_por_id`** — fracao dos slots do top-k ocupados por um documento que ja apareceu na MESMA query (mediana entre queries)

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_por_texto`** — fracao dos documentos DISTINTOS cujo texto e identico ao de outro documento com id diferente. Sobrevive a deduplicacao por id. ATENCAO: efeito concentrado — leia `queries_afetadas`, nao a mediana.

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`jaccard_cross_query`** — Jaccard mediano entre os conjuntos top-k de PARES de queries distintas. Alto indica que o retriever devolve o mesmo material independentemente da pergunta.

*N = 1225 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

**`razao_score_topo_cauda`** — score mediano das 5 primeiras posicoes dividido pelo das 5 ultimas. Proximo de 1 indica ranking pouco discriminativo.

*N = 50 · k = 50 · snapshot `d64fcc74a0c7e9b0` · fonte: ranking real do retriever do sistema auditado*

## Verificações

| check | estado | barra? | detecta |
|---|---|---|---|
| `procedencia.snapshot_tem_hash` | PASS | não | corpus trocado sob o mesmo caminho entre a auditoria e a contestacao |
| `ranking.veio_do_retriever` | PASS | não | ranking fabricado: ordem de arquivo, ordem alfabetica, ou qualquer sequencia que nao saiu do retriever |
| `estatistica.unidades_suficientes` | PASS | não | intervalo de confianca estreito por construcao: itens correlacionados contados como independentes |

## Etapas

| etapa | estado |
|---|---|
| `snapshot` | PASS |
| `entrada` | PASS |
| `retriever` | PASS |
| `ranking` | PASS |
| `estratos` | PENDING |
| `estratos` | PASS |
| `amostragem` | PASS |
| `julgadores` | PASS |
| `estatistica` | PASS |

## Procedência

```
dir = /tmp/auditoria_gzjxp202/sessions/default_cognitive
store = /tmp/auditoria_gzjxp202/sessions/default_cognitive
sha256_episodic = d64fcc74a0c7e9b08eb3972129a7f5689b008912c3e32abce9e386477d1703be
sha256_semantic = 632a7f228045f89cc92bf98695a4f664e181e214a93236035f0af1a635eab27d
retriever.top_k = 50
retriever.origem = EDPAuditavel
retriever.adaptador = EDPAuditavel
retriever.versao_adaptador = edp-1
retriever.telemetria = {'origem_do_ranking': 'EDPAuditavel.consulta', 'top_k_solicitado': 50, 'n_slots_recebidos': 50, 'n_ids_distintos': 37, 'n_textos_distintos': 37, 'formato_valido': True}
manifesto.sha256 = b7d4e0e02ef996c0a936528001059867386b7655888c7e1a0c0d549a7db8aee7
```

## Custo desta auditoria

```
tempo_total_s = 18.281
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