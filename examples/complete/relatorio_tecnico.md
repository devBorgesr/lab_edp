# Auditoria `1044b31119a7` — DIAGNOSTICO v1

**Status: COMPLETE** · protocolo *demonstrativo* · serviço `0.2.0`

## Resultado

- **escopo**: diagnostico do material recuperado
- **medicoes**: {'cardinalidade_do_ranking': 20.0, 'duplicacao_intra_query_por_id': 0.6, 'duplicacao_por_texto': 0.0, 'jaccard_cross_query': 0.08108108108108109, 'razao_score_topo_cauda': 1.3846153846153846}
- **NAO_AFIRMA**: nada sobre a qualidade das respostas do sistema. Sem Recall@K, sem ground truth, sem certificacao.

## Medições

Fatos observáveis sobre o material recuperado. **Não são métricas de qualidade de resposta** e não substituem o resultado do protocolo.

| medição | valor | IC 95% | N | unidade |
|---|---|---|---|---|
| `cardinalidade_do_ranking` | 20 | [20, 20] | 24 | documentos por query |
| `duplicacao_intra_query_por_id` | 0,6 | [0,6, 0,6] | 24 | fracao dos slots |
| `duplicacao_por_texto` | 0 | [0, 0] | 24 | fracao dos documentos distintos |
| `jaccard_cross_query` | 0,0811 | [0,0811, 0,0811] | 276 | Jaccard entre pares de queries |
| `razao_score_topo_cauda` | 1,385 | [1,385, 1,385] | 24 | razao adimensional |

**`cardinalidade_do_ranking`** — documentos DISTINTOS entregues na janela top-k (mediana entre queries). Slots cheios nao implicam documentos distintos.

*N = 24 · k = 50 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_intra_query_por_id`** — fracao dos slots do top-k ocupados por um documento que ja apareceu na MESMA query (mediana entre queries)

*N = 24 · k = 50 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`duplicacao_por_texto`** — fracao dos documentos DISTINTOS cujo texto e identico ao de outro documento com id diferente. Sobrevive a deduplicacao por id. ATENCAO: efeito concentrado — leia `queries_afetadas`, nao a mediana.

*N = 24 · k = 50 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`jaccard_cross_query`** — Jaccard mediano entre os conjuntos top-k de PARES de queries distintas. Alto indica que o retriever devolve o mesmo material independentemente da pergunta.

*N = 276 · k = 50 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

**`razao_score_topo_cauda`** — score mediano das 5 primeiras posicoes dividido pelo das 5 ultimas. Proximo de 1 indica ranking pouco discriminativo.

*N = 24 · k = 50 · snapshot `ddbc8cacc43ae374` · fonte: ranking real do retriever do sistema auditado*

## Limites desta régua

O DIAGNOSTICO v1 descreve o material que o retriever devolveu. **Não foi medido, e este relatório não permite afirmar:**

- qualidade das respostas do sistema;
- Recall@K, precisão ou qualquer comparação com conjunto de referência;
- relevância dos documentos — nenhum julgamento, humano ou automático, foi feito;
- conformidade, certificação ou aprovação.

Também **não há linha de base**: com um único sistema real medido, não é possível dizer se um valor observado é alto ou baixo em relação a outros sistemas.

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
dir = examples/complete/_corpus/sessions/default_cognitive
store = examples/complete/_corpus/sessions/default_cognitive
sha256_episodic = ddbc8cacc43ae37490bbc42bfab8577e166621f5056bd1b3ebcc3127b171400a
sha256_semantic = 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
retriever.top_k = 50
retriever.origem = ClienteSintetico
retriever.adaptador = ClienteSintetico
retriever.versao_adaptador = fixture-1
retriever.telemetria = {'origem_do_ranking': 'ClienteSintetico.consulta', 'top_k_solicitado': 50, 'n_slots_recebidos': 50, 'n_ids_distintos': 20, 'n_textos_distintos': 20, 'formato_valido': True}
manifesto.sha256 = 96f7e7e13835f576aab1743a4e9a865e6ec62cc54af51f35f6aaf01103906b74
```

## Custo desta auditoria

```
tempo_total_s = 0.04
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