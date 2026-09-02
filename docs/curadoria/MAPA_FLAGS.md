# Mapa das 12 flags desligadas

**Fase 2 da curadoria.** Nenhuma flag foi ligada. Nenhum código alterado.

**As 12 têm teste — e agora verificado por EXECUÇÃO, não só por existência de
arquivo.** `pytest tests/ -q` no `edp_v5`: **448 passed, 1 deselected, 0
failed** (medido na Fase 3, 01/09/2026). Nenhum dos 12 arquivos de teste
citados abaixo está entre falhas ou erros — todos correm dentro de uma suíte
que passa inteira. Isso não é código abandonado — é engenharia gated.

**Achado de escopo, fora dos 19 catalogados:** esta lista cobre só flags no
padrão `X = os.environ.get("EDP_X", "0") == "1"`, centralizadas em
`config.py`. Há pelo menos mais 6 variáveis de ambiente lidas **direto nos
módulos**, fora dessa convenção — `EDP_LAB_ARMED` (trava de segurança do
laboratório, default OFF, 6 pontos de leitura em `edp/lab/`),
`EDP_AUTO_CONSOLIDATE`, `EDP_COGNITIVE_DECISIONS_ENABLED`, `EDP_HEALTH_INDEX`,
`EDP_LINEAGE`, `EDP_QUALITY_SCORE` (as 5 últimas com default `"true"`). Não
catalogadas aqui — ver `ACHADOS_FORA_DE_ESCOPO` em
`LACUNAS_E_NAO_VERIFICADO.md`.

Legenda de maturidade: `EXISTE` < `EXECUTADO` < `TESTADO` < `VALIDADO` <
`REUTILIZÁVEL` < `PRONTO PARA PRODUÇÃO`. Não são sinônimos.

---

## Grupo A — Telemetria (5 flags, todas escrevem no mesmo sink)

Todas emitem via `edp/runtime/pareto_store.py` → **JSONL append-only** em
`$EDP_BASE_DIR/pareto/events.jsonl`, com rotação a 10 MB.

### `EDP_RANKING_TELEMETRY`

```
default ................. 0 (OFF)
arquivos ................ edp/memory/store.py:765, :1838
                          edp/runtime/pareto_store.py:707 (emit_ranking_decision)
função que habilita ..... emit_ranking_decision(...)
dados produzidos ........ n_avaliadas, n_acima_do_piso, n_apos_filtro_sessao,
                          n_apos_filtro_recusa, n_entregues, min_score, top_k,
                          metodo, detalhe[{rank, score, fatores}] (20 primeiros)
formato ................. evento JSONL, com correlation_id
efeito no comportamento . NENHUM — só observa; com a flag OFF é um `if`
testes .................. test_ranking_telemetry.py,
                          test_ranking_telemetry_caminho_vivo.py
por que desligada ....... SEM_REGISTRO_ENCONTRADO — git log -S no arquivo e
                          na função não mostra commit dizendo "manter OFF
                          porque X"; só o commit que a introduziu
                          (1b022a6, 13/08, "a seleção de memórias para de
                          ser invisível") e o que a corrigiu (8f51663,
                          18/08, "estava em código morto")
dependências ............ pareto_store, correlation_id
potencial p/ MVP ........ ALTÍSSIMO — é o funil de retrieval
potencial p/ serviço .... base de "onde o contexto se perde"
risco ................... escrita adicional em disco por turno; volume NAO_MEDIDO
maturidade .............. TESTADO (não VALIDADO em produção)
```

**A docstring diz o que ela é:** *"por que estas memórias chegaram ao prompt, e
não aquelas"*.

### `EDP_REFLECTION_TELEMETRY`

```
arquivos ....... edp/meta_reasoner.py:73, pareto_store.py:835 (emit_reflection)
dados .......... confidence, hallucination_risk, n_conflitos, n_redundancias,
                 n_ctx_items, n_mem_entries, reweights
efeito ......... "NÃO aplica nada" (docstring do emissor)
testes ......... test_reflection_telemetry.py
maturidade ..... TESTADO
```

**Achado:** a docstring diz *"o que a reflexão concluiu no turno — que hoje
ninguém lê"*. É um **loop aberto** — sinal computado e nunca consumido, o que o
`edp_metodologia_v5.md §4.3` já cataloga como categoria.

### `EDP_CONTRADICTION_TELEMETRY`

```
arquivos ....... edp/runtime/contradiction_flagger.py:337, pareto_store.py:907
dados .......... n_resultados, n_pares, max_sim, n_acima_do_limiar,
                 n_flagados, limiar, abortou
efeito ......... "Não muda o que é flagado" (docstring)
testes ......... test_contradiction_telemetry.py
maturidade ..... TESTADO
```

Docstring: *"por que o detector de contradição não flagou nada"* — telemetria
de **negativo**, que é justamente o caso difícil de auditar.

### `EDP_TOKEN_TELEMETRY`

```
arquivos ....... edp/llm/providers/anthropic.py:213, pareto_store.py:974
dados .......... model, modo, usage (tokens REAIS do provedor), text_chars,
                 system_chars, payload_bytes, n_messages
efeito ......... "nunca altera a resposta"
testes ......... test_token_telemetry.py
maturidade ..... TESTADO
```

Par (chars enviados, tokens reais) — **base de custo real por chamada**.

### `EDP_SUMMARY_TELEMETRY`

```
arquivos ....... edp/session_summary.py:256, pareto_store.py:1078
dados .......... max_sim, n_anteriores, limiar, gravou, guarda_ativa,
                 topic_tag, n_chars
testes ......... test_summary_dedup.py
maturidade ..... TESTADO
```

Registra **a distância até a duplicata mais próxima** a cada escrita de resumo.

---

## Grupo B — Instrumentação de retrieval (exp017)

### `EDP_RETRIEVE_DEDUP` · `EDP_RETRIEVE_SHUFFLE` · `EDP_RETRIEVE_RANDOM_DROP`

```
arquivos ....... edp/memory/store.py:1538-1539, edp/llm_adapter.py:2473-2482
efeito ......... MUDA O CONJUNTO RECUPERADO. Não é telemetria.
testes ......... test_exp017_dedup_integration.py, test_exp017_shuffle.py,
                 test_flag_off_byte_identical.py
maturidade ..... TESTADO, com garantia de flag-off byte-idêntica
risco .......... ALTO para o MVP: mudar o retriever muda o objeto auditado
potencial ...... NÃO acoplar. É a opção B/C da DECISAO_RANKING, que segue
                 em branco.
```

**`test_flag_off_byte_identical.py` é a peça de engenharia mais reaproveitável
aqui** — o padrão "com a flag desligada, saída byte-idêntica" é exatamente a
garantia que um serviço de auditoria precisa dar sobre a própria
instrumentação.

---

## Grupo C — Comportamento

### `EDP_CORRELATION_PROPAGATION`

```
arquivos ....... edp/api/routes/websocket.py:631
efeito ......... propaga correlation_id através do WebSocket
testes ......... test_correlation_propagation.py
potencial ...... rastreabilidade fim-a-fim; relevante para PROVENIÊNCIA
maturidade ..... TESTADO
```

### `EDP_ANCHOR_COMPACT`

```
arquivos ....... edp/llm_adapter.py:1382
efeito ......... compacta âncoras no prompt — MUDA O PROMPT
testes ......... test_anchor_compact.py, test_token_telemetry.py
risco .......... altera comportamento do modelo
potencial ...... fora do escopo do diagnóstico de retrieval
```

### `EDP_SUMMARY_DEDUP`

```
arquivos ....... edp/session_summary.py:257
efeito ......... suprime escrita de resumo duplicado — MUDA O ESTADO
testes ......... test_summary_dedup.py
nota ........... o limiar 0,98 era INALCANÇÁVEL por incompatibilidade de
                 prefixo no embedding (duplicata exata media 0,769);
                 corrigido no bloco 4-bis
maturidade ..... TESTADO, com errata registrada
```

### `EDP_WIKI_CONVERSAS`

```
arquivos ....... edp/api/routes/wiki.py:11
efeito ......... expõe conversas na wiki — flag de SEGURANÇA
testes ......... test_wiki.py
risco .......... exposição de conteúdo; desligada por decisão de privacidade
potencial ...... NÃO acoplar
```

---

## Resumo

| grupo | flags | efeito | acoplável ao MVP |
|---|---|---|---|
| telemetria | 5 | nenhum (só observa) | **sim, é o caminho** |
| retrieval exp017 | 3 | muda o recuperado | não — muda o objeto auditado |
| comportamento | 4 | muda prompt/estado/exposição | não |

**Nenhuma das 12 está `VALIDADA` em produção.** Todas estão `TESTADAS`.
A distância entre as duas categorias é o que este documento existe para não
deixar apagar.

---

## Item 1.7 — arqueologia de por que cada flag continua OFF (Fase 3)

**Correção de contagem: 11, não 12.** `EDP_WIKI_CONVERSAS` já tinha motivo
registrado no corpo original deste documento — decisão de privacidade, e o
código a documenta como tal. Restam 11 sem motivo de desligamento explícito.

`git log -S"<FLAG>"` em todo o histórico do `edp_v5`, para as 11:

| flag | resultado da arqueologia |
|---|---|
| `EDP_RANKING_TELEMETRY` | `SEM_REGISTRO_ENCONTRADO` — 2 commits: introdução (13/08) e correção de bug (18/08). Nenhum fala em manter OFF |
| `EDP_REFLECTION_TELEMETRY` | `SEM_REGISTRO_ENCONTRADO` — 1 commit, introdução (13/08), docstring diz "que hoje ninguém lê" |
| `EDP_CONTRADICTION_TELEMETRY` | `SEM_REGISTRO_ENCONTRADO` — 1 commit, introdução (14/08) |
| `EDP_TOKEN_TELEMETRY` | `SEM_REGISTRO_ENCONTRADO` — 3 commits, todos de introdução/refactor (12/08) |
| `EDP_SUMMARY_TELEMETRY` | `SEM_REGISTRO_ENCONTRADO` — 1 commit, introdução (18/08) |
| `EDP_CORRELATION_PROPAGATION` | `SEM_REGISTRO_ENCONTRADO` — 1 commit, um FIX (18/08: "correlation_id não atravessava o executor") |
| `EDP_ANCHOR_COMPACT` | `SEM_REGISTRO_ENCONTRADO` — 4 commits, todos de construção (07/08–12/08) |
| `EDP_SUMMARY_DEDUP` | `SEM_REGISTRO_ENCONTRADO` — 2 commits, introdução + errata de comentário (18/08) |
| `EDP_RETRIEVE_DEDUP` | **`DECISAO_REGISTRADA` — parcial.** Ver abaixo |
| `EDP_RETRIEVE_SHUFFLE` | **`DECISAO_REGISTRADA` — parcial.** Ver abaixo |
| `EDP_RETRIEVE_RANDOM_DROP` | **`DECISAO_REGISTRADA` — parcial.** Ver abaixo |

### O trio exp017 é diferente dos outros 8

Não é "sem motivo" — é **decisão pendente, e a pendência está documentada**.

O commit `28e21da` (20/08, *"exp017: T5/T6 rodados — o 'PARAR' da Fase 1 foi
cumprido"*) fecha a rodada com todas as pernas do critério de H1 batendo, e diz
explicitamente:

> O VEREDITO fica em linha para assinatura — o pré-registro atribui a decisão
> ao pesquisador, não à conferência. Registrado junto o que a passagem NÃO
> autoriza: [...] não liga a flag em produção (promoção é etapa separada).

Isto é `NORTE §4.2`/`§4.12` funcionando como desenhado: o resultado passou, e
a promoção a produção foi **deliberadamente separada** da constatação
estatística, esperando assinatura. Essa assinatura é exatamente a mesma
decisão que `docs/auditor/DECISAO_RANKING.md` (no `lab_edp_novo`) está pedindo, do
outro lado — a mesma pergunta, dois documentos.

### O que isto muda na curadoria

Nenhum candidato de acoplamento muda de classe: as 8 flags de telemetria e
comportamento continuam sem qualquer registro de intenção de manter OFF — o
mais provável, por ausência de evidência em contrário, é que ficaram OFF
porque foram construídas para instrumentar a calibração da Fase 1
(12–18/08/2026) e ninguém tomou a decisão seguinte de promovê-las, não porque
alguém decidiu que deveriam continuar desligadas.

O trio exp017 já estava corretamente classificado como "precisa de
experimento" em `CANDIDATOS_ACOPLAMENTO_MVP.md` — a arqueologia confirma que
essa classificação é a mesma linha de decisão que o próprio kernel já registrou
como pendente.
