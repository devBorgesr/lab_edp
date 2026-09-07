# Auditoria `7642c0ad8597` — DIAGNOSTICO v1

**Status: COMPLETE** · protocolo *demonstrativo* · serviço `0.4.0`

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
dir = /tmp/auditoria_dxzib027/sessions/default_cognitive
origem = /home/kali/Desktop/edp_data_todo/edp_data/sessions/default_cognitive
store = /tmp/auditoria_dxzib027/sessions/default_cognitive
sha256_episodic = d64fcc74a0c7e9b08eb3972129a7f5689b008912c3e32abce9e386477d1703be
sha256_semantic = 632a7f228045f89cc92bf98695a4f664e181e214a93236035f0af1a635eab27d
retriever.top_k = 50
retriever.origem = EDPAuditavel
retriever.adaptador = EDPAuditavel
retriever.versao_adaptador = edp-1
retriever.telemetria = {'origem_do_ranking': 'EDPAuditavel.consulta', 'top_k_solicitado': 50, 'n_slots_recebidos': 50, 'n_ids_distintos': 37, 'n_textos_distintos': 37, 'formato_valido': True}
retriever.configuracao_sujeito = {'disponivel': True, 'identidade': {'modulo': '/media/sf_edp_v5_main/edp/__init__.py', 'versao': '3.0.0'}, 'fonte': 'edp.config.FORMAT_STATE_FLAGS', 'flags': {'EDP_HYBRID_RETRIEVAL': True, 'EDP_CTX_SLOTS': True, 'EDP_WRITE_PROVENANCE': True, 'EDP_TOXIC_GUARDS': True, 'EDP_RETRIEVE_DEDUP': False, 'EDP_RETRIEVE_SHUFFLE': False, 'EDP_RETRIEVE_RANDOM_DROP': False, 'EDP_ANCHOR_COMPACT': False, 'EDP_STORE_QUARANTINE': True, 'EDP_SUMMARY_DEDUP': False}}
manifesto.sha256 = 16b0b51b314b52d5bf6f0359a139432d68b469f53cfcd200a5e84a9e62a93129
```

## Custo desta auditoria

```
tempo_total_s = 16.526
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