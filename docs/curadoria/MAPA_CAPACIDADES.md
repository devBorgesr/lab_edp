# Mapa de capacidades do ecossistema EDP

**Fase 2.** Agrupa engenharia por **capacidade**, não por módulo — para achar
capacidades equivalentes espalhadas em arquivos diferentes.

## Resumo executivo

```
CAPACIDADES ENCONTRADAS ........ 21
ACOPLÁVEIS AGORA ...............  3
ACOPLÁVEIS DEPOIS DO PILOTO ....  4
PRECISAM DE TESTE ..............  6
PRECISAM DE EXPERIMENTO ........  2
NOVOS SERVIÇOS CANDIDATOS ......  3
NÃO VERIFICADAS ................  7
```

Escala de maturidade, usada em todas as fichas:

```
EXISTE < EXECUTADO < TESTADO < VALIDADO < REUTILIZÁVEL < PRONTO P/ PRODUÇÃO
```

**Não são sinônimas.** Nenhuma capacidade abaixo está em `PRONTO PARA
PRODUÇÃO` no sentido de produto de terceiro — o kernel nunca serviu cliente
externo.

---

## RETRIEVAL

### `retrieval_hybrid` — BM25 + vetorial + RRF

```
arquivos ......... edp/retrieval_hybrid.py (330 L)
função real ...... busca híbrida; k = min(top_k*3, N); fusão por RRF ou
                   ponderada; MMR opcional
entrada .......... query, query_emb, top_k, min_score, method, mmr
saída ............ HybridResult(indices, scores, bm25_scores, vector_scores)
efeito colateral . nenhum (função pura sobre o índice)
quem chama ....... edp/memory/store.py (_hybrid_index / _retrieve_hybrid)
executado hoje ... SIM — EDP_HYBRID_RETRIEVAL default "1" desde 08/07
flag ............. EDP_HYBRID_RETRIEVAL (LIGADA)
teste ............ NENHUM diretamente sobre retrieval_hybrid.py
documentação ..... exp010
maturidade ....... EXECUTADO em produção, SEM TESTE PRÓPRIO
evidência ........ medido nesta curadoria: 0 testes importam edp.retrieval_hybrid
reutilização ..... o MVP já mede a SAÍDA disto; não precisa do módulo
```

### `retrieval` (cosine) e `vector_store`

```
retrieval.py (322 L) · vector_store.py (280 L)
importadores ..... 1 cada
teste ............ NENHUM
maturidade ....... EXISTE
nota ............. o caminho cosine foi APOSENTADO na prática — 11 de 18
                   mecanismos não decidem em produção sob RRF (achado do
                   exp008/exp009). Reutilização: NÃO.
```

### `reranker`

```
edp/reranker.py (189 L) — classes RerankResult, Reranker
importadores ..... 0
teste ............ NENHUM
maturidade ....... EXISTE
reutilização ..... NÃO até verificar se funciona. Marcado morto no catálogo
                   AST do próprio repo.
```

---

## TELEMETRIA / OBSERVABILIDADE

### Camada de eventos `pareto_store` — **a capacidade mais substancial**

```
arquivo .......... edp/runtime/pareto_store.py (1.128 L)
função real ...... 12 emissores de evento + correlation_id + hash_format_state
                   + FileParetoStore
saída ............ JSONL append-only, $EDP_BASE_DIR/pareto/events.jsonl,
                   rotação a 10 MB
emissores ........ memory_added, memory_accessed, mode_switched,
                   task_started, task_completed, camara_outcome,
                   store_degraded, ranking_decision, reflection,
                   contradiction_scan, token_usage, summary_write
efeito colateral . escrita em disco quando a flag do emissor está ON
executado hoje ... PARCIAL — 5 emissores atrás de flags OFF
teste ............ 5 arquivos de teste (um por flag de telemetria)
maturidade ....... TESTADO
reutilização ..... ALTA — ver CANDIDATOS_ACOPLAMENTO_MVP.md
```

Detalhe por flag em `MAPA_FLAGS.md`.

### `observability/` — logger e tracing

```
arquivos ......... edp/observability/{logger,tracing}.py (295 L no total)
importadores ..... 2
teste ............ NENHUM
maturidade ....... EXISTE
reutilização ..... NAO_VERIFICADO — não abri o conteúdo
```

### `metrics`

```
edp/metrics.py (108 L) · 22 importadores · 0 testes
maturidade ....... EXECUTADO (muito importado), SEM TESTE
nota ............. 22 importadores e nenhum teste é o maior descompasso
                   pontual do kernel
```

---

## PROVENIÊNCIA / CORRELAÇÃO

Tratada em `MAPA_PROVENIENCIA.md`. Componentes:

```
runtime/lineage.py (340 L)     SourceEntry, LineageRecord, LineageTracker
write_provenance.py (212 L)    stamp_and_classify, classify, negacao_textual
pareto_store                   correlation_id, hash_format_state
api/routes/lineage.py (91 L)   exposição HTTP
```

`EDP_WRITE_PROVENANCE` está **LIGADA** por default. Cobertura de chamada:
`NAO_VERIFICADO`.

---

## EXPERIMENTAÇÃO — a Bancada (`edp/lab`, ~3.000 L)

Modelada em Burp Suite. **2 arquivos de teste para 3.000 linhas.**

### `sampler` (240 L) — substrato estatístico

```
função ........... resolve o não-determinismo do LLM: N amostras por condição
público .......... sample, render_window, make_runtime_caller, CallResult,
                   SampleResult, LabNotArmedError
determinismo ..... é o módulo que EXISTE por causa da falta dele
teste ............ NENHUM direto
maturidade ....... EXISTE
reutilização ..... alta em conceito, mas exige teste antes de virar dependência
```

### `scorer` (1.025 L) — análise pós-coleta

```
função ........... lê o prontuário, separa REAIS de dry-run, computa métrica
                   primária confirmatória
público .......... score_fidelity, extract_signals, score_prontuario, report,
                   CondicaoFidelidade, CamadaAutoridade
maturidade ....... EXISTE
nota ............. maior arquivo da Bancada; a separação real/dry-run é
                   disciplina que o MVP também tem (check vs run)
```

### `prontuario` (366 L) — store longitudinal

```
função ........... "A BASE. Tudo da Bancada lê e escreve por aqui"
público .......... ProntuarioStore (Protocol), FileProntuarioStore,
                   get_prontuario
persistência ..... arquivo
maturidade ....... EXISTE
reutilização ..... SÉRIE TEMPORAL — o auditor mede um instante; isto guarda
                   histórico. Candidato a serviço novo.
```

### `isolation` (222 L) — não contaminar produção

```
função ........... o _active_scope do MemoryStore é campo mutável compartilhado;
                   este módulo isola sessão de laboratório
público .......... new_lab_session_id, is_lab_session, LabSession,
                   purge_lab_session, experimental_session,
                   cognitive_fingerprint, verify_no_leak, production_contains
maturidade ....... EXISTE
reutilização ..... `verify_no_leak` e `production_contains` são EXATAMENTE a
                   garantia que o MVP afirma dar ("auditar não altera o
                   auditado") e hoje prova por cópia + hash. Duas soluções
                   para o mesmo problema.
```

### `window_formats` (316 L) — **catálogo de perturbação de contexto**

```
função ........... transformações PURAS das seções da janela (system, anchors,
                   retrieval, recent)
público .......... fmt_neutra, fmt_ablacao, fmt_lost_in_middle,
                   fmt_ruido_dominante, fmt_historico_cortado,
                   fmt_ancora_envenenada, fmt_fato_em_camada
maturidade ....... EXISTE
reutilização ..... é uma BATERIA DE AVALIAÇÃO de construção de contexto —
                   ablação, lost-in-middle, âncora envenenada. Nada disso
                   existe no MVP.
```

### `repeater` (176 L) · `rodizio` (147 L) · `run_once` (499 L)

```
repeater ......... junta as quatro peças da base, com invariantes
rodizio .......... roda um PLANO de condições, N amostras cada
run_once ......... a PORTA: roda UM experimento contra o EDP real
maturidade ....... EXISTE
```

---

## MEMÓRIA / CONTEXTO / RESUMO

```
memory/ (2.529 L)          14 importadores, 9 testes    VIVO
consolidation (372 L)       4 importadores, 3 testes    VIVO
session_summary (405 L)     3 importadores, 1 teste     VIVO
context_builder (186 L)     2 importadores, 0 testes    SEM TESTE
compression (206 L)         1 importador,  0 testes     SEM TESTE
attention (151 L)           1 importador,  0 testes     SEM TESTE
blocks (356 L)              1 importador,  1 teste      VIVO
```

---

## CLASSIFICAÇÃO / CONTRADIÇÃO

```
memory_classifier (169 L)      3 imp, 0 testes
epistemic_classifier (144 L)   1 imp, 0 testes
runtime/contradiction_flagger  telemetria sob flag OFF, 1 teste
echo_chamber (1.116 L)         6 imp, 1 teste           VIVO
```

---

## API / DASHBOARD

```
edp/api/routes/ — 4.814 L em 13 rotas
  memory.py           1.775 L
  websocket.py        1.425 L
  flags.py              360 L   <- exposição das flags por HTTP
  wiki.py               201 L
  llm.py                134 L
  cognitive_decisions   113 L
  dashboard_state.py    102 L
  live_feed.py           94 L
  lineage.py             91 L
  health.py              81 L
edp/dashboard/ — static/ + templates/  (EXISTE)
teste ............ 4 arquivos citam edp.api
maturidade ....... EXECUTADO (é o serviço do kernel), cobertura parcial
```

**`flags.py` (360 L) expõe as flags por HTTP** — relevante: um serviço de
diagnóstico que precise ligar telemetria não precisaria de acesso ao processo.

---

## EXPORTAÇÃO / CAPTURA (`sf_exportador`, 6.255 L JS)

```
panel.js             736 L
debugger_capturer    541 L   captura via chrome.debugger
llm_adapter          511 L   Ollama local + Anthropic/OpenAI opcional
sandbox              309 L
terminal_ui          288 L
har_analyzer         276 L   análise de HAR
chat_ui              156 L
llm_config           128 L
teste ............ NAO_VERIFICADO (não há suíte medida)
maturidade ....... EXISTE
```

Detalhe em `CANDIDATOS_NOVOS_SERVICOS.md`.

---

## Capacidades que o MVP tem e o EDP não

```
manifesto versionado (AuditResult v1)    só no MVP
trava de claims (claims.py)              só no MVP
redação de segredo antes de persistir    só no MVP
isolamento multi-inquilino               só no MVP
protocolo com escopo e versão            só no MVP
```

E uma que o EDP tem e o MVP não: **telemetria do funil de retrieval**.
