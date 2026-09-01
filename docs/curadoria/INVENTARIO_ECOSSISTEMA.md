# Inventário e curadoria do ecossistema EDP

**01/09/2026.** Levantamento por medição — AST para importadores, contagem
real de linhas, cruzamento com testes e flags. Onde não medi, digo que não medi.

## Escopo

| repositório | linhas | testes | commits | papel |
|---|---|---|---|---|
| `edp_v5` (público) | **46.219** | 42 arquivos | 282 | kernel de memória/retrieval |
| `lab_edp_novo` (privado) | **21.752** | 25 arquivos | 126 | experimentos + serviço de diagnóstico |
| `sf_exportador` | **6.255** (JS) | — | não é repo git | extensão Chrome + copiloto |

`Synapse-Forge` está **vazio**.

Total ≈ **74 mil linhas**. O número sozinho não diz nada — o que segue é a
separação entre o que está vivo, o que está desligado e o que está morto.

---

## 1. `edp_v5` — 49 módulos de topo, 38.179 linhas em `edp/`

Medido por AST (importador real, não menção em docstring):

| estado | módulos | leitura |
|---|---|---|
| **vivo** (importado + testado) | **16** | 33% |
| **sem teste** (importado, não testado) | **27** | 55% |
| **sem importador** | **6** | 12% |

Os 6 sem importador: `api`, `profiles`, `types`, `analytics`, `reranker`,
`failsafe`. **`api` e `profiles` são pontos de entrada** — carregados por
uvicorn e por registro, não por `import` — então "sem importador" ali não
significa morto. `analytics`, `reranker`, `types` e `failsafe` precisam de
verificação caso a caso antes de qualquer afirmação.

> O repositório **já tem** `tests/test_catalogo_de_modulos_mortos.py`, que
> força por AST a lista de mortos do README. A lista já errou nas duas direções
> antes de existir esse teste. Este inventário é consistente com ele.

**55% sem teste é o número que mais limita reaproveitamento.** Um módulo sem
teste pode ser acoplado — mas não pode ser chamado de "pronto".

---

## 2. O achado principal: uma camada de telemetria construída e desligada

19 flags booleanas em `config.py`. **7 ligadas, 12 desligadas.** As desligadas
não são código abandonado — **todas as 7 que investiguei têm teste**.

Cinco delas são telemetria:

```
EDP_TOKEN_TELEMETRY · EDP_RANKING_TELEMETRY · EDP_REFLECTION_TELEMETRY
EDP_CONTRADICTION_TELEMETRY · EDP_SUMMARY_TELEMETRY
```

### `emit_ranking_decision` — o funil de retrieval

`store.py:765` emite, sob flag, a **cascata inteira de redução**:

```
n_avaliadas → n_acima_do_piso → n_apos_filtro_sessao
            → n_apos_filtro_recusa → n_entregues
```

mais `detalhe` com `{rank, score, fatores}` das 20 primeiras posições.

**Isto é diretamente acoplável ao MVP, e é o acoplamento de maior valor que
encontrei.** O `DIAGNOSTICO v1` hoje mede *o que saiu* do retriever. Esta
telemetria explica *onde os candidatos se perderam* — que é a pergunta seguinte
que qualquer cliente faz depois de ver "37 documentos distintos de 50 slots".

### `pareto_store.py` — 1.128 linhas de proveniência de eventos

Não é log: é infraestrutura de rastreabilidade.

```
set_current_correlation_id · new_correlation_id
hash_format_state              ← hash do estado de formato
FileParetoStore                 ← sink em arquivo
emit_memory_added / accessed / mode_switched
emit_task_started / completed / camara_outcome
emit_store_degraded / ranking_decision
```

`correlation_id` + `hash_format_state` são exatamente o que um serviço de
auditoria precisa para amarrar evidência — e o MVP já tem conceito equivalente
(`sha256_manifesto`, `audit_id`). **São dois vocabulários para o mesmo
problema, construídos separadamente.**

---

## 3. A Bancada — ~3.000 linhas de infraestrutura de experimento

`edp/lab/`, modelada em Burp Suite:

| módulo | linhas | o que é |
|---|---|---|
| `scorer` | 1.025 | análise pós-coleta |
| `run_once` | 499 | a porta: roda UM experimento contra o EDP real |
| `prontuario` | 366 | store longitudinal |
| `window_formats` | 316 | catálogo de formatos de janela |
| `sampler` | 240 | substrato estatístico; resolve não-determinismo |
| `isolation` | 222 | isolamento experimental |
| `repeater` | 176 | orquestrador (Repeater) |
| `rodizio` | 147 | varredura de variantes (Intruder) |

**Cobertura de teste: 2 arquivos.** Para 3.000 linhas. Este é o maior
descompasso entre volume e verificação do ecossistema.

`sampler` (não-determinismo) e `prontuario` (série longitudinal) são os dois
com uso plausível no MVP — o auditor hoje mede um instante; medir deriva ao
longo do tempo é produto adjacente óbvio. Mas **ambos precisariam de teste
antes de virar dependência.**

---

## 4. `edp/api` — 15 rotas e um dashboard que existe

`edp/api/routes/`: `cognitive_decisions`, `dashboard_state`, `flags`, `health`,
`lineage`, `live_feed`, `llm`, `memory`, `metrics`, `mode`, `providers`,
`websocket`, `_sidebar`.

E **`edp/dashboard/` existe**, com `static/` e `templates/`.

Isso importa para uma decisão que já foi tomada duas vezes: *"não construir
dashboard antes do piloto"*. A decisão continua certa — mas o inventário mostra
que **não seria construir do zero**. `lineage` e `live_feed` são
particularmente relevantes: proveniência e stream ao vivo.

---

## 5. `lab_edp_novo` — dois braços

**Serviço de diagnóstico** (`auditor/`, 32 arquivos): é o MVP, 408 testes,
documentado. Não repito aqui.

**Experimentos** (`sujeitos/`, 53 arquivos + 64 documentos): `edp/`, `rel/`,
`edi/`. O `ACERVO_EXPERIMENTOS.md` já é uma curadoria honesta — registra que a
disciplina de pré-registro começou no exp008 e **recusa reconstruir os
anteriores retroativamente**.

Reaproveitável para novos serviços: o `TEMPLATE_PREREGISTRO.md` (11 seções) e o
harness de coleta do `rel/` — que já tem juiz-LLM configurado, taxonomia de
falha e parser que devolve `None` em vez de `0`.

---

## 6. `sf_exportador` — outro produto, não uma feature

Extensão Chrome v4.2 (6.255 linhas JS) que captura conversas do claude.ai. E um
subsistema **copiloto** que eu não conhecia:

```
sandbox.js · terminal_ui.js · llm_adapter.js · llm_config.js
har_analyzer.js · debugger_capturer.js · chat_ui.js · panel.js
```

LLM **local por padrão (Ollama)**, provedor externo opcional com chave do
usuário. Análise de HAR e captura via `chrome.debugger`.

**Isto não acopla ao MVP** — é um produto diferente, com outro usuário e outro
risco. Registro porque é engenharia real que existe, não porque recomendo usar
agora. O `har_analyzer` seria o único candidato distante: um adaptador que lê
tráfego de um RAG atrás de API — e é exatamente o **caso B** do pré-registro do
piloto, aquele em que o retrieval está escondido e sem score.

---

## Curadoria — o que responde à pergunta

### Acoplável ao MVP com trabalho pequeno

| o quê | por que está pronto | o que falta |
|---|---|---|
| **`emit_ranking_decision`** | tem teste, emite cascata estruturada | ligar a flag num ambiente de medição; escrever o check que consome |
| **`pareto_store` (correlation_id, hash_format_state)** | 1.128 linhas, em uso sob flag | reconciliar vocabulário com `audit_id`/`sha256_manifesto` — hoje são dois nomes para o mesmo conceito |
| **`TEMPLATE_PREREGISTRO`** | 11 seções, usado em 4 experimentos | nada; é documento |

### Acoplável com trabalho médio, e exige teste antes

| o quê | risco |
|---|---|
| `sampler` (não-determinismo) | 240 linhas, cobertura de teste ~nula |
| `prontuario` (série longitudinal) | 366 linhas, idem |
| `edp/api/routes/lineage` | proveniência já existente; sem teste próprio medido |

### Não acoplável agora

Copiloto do exportador (produto distinto) · dashboard (decisão já tomada:
depois do piloto) · os 27 módulos sem teste, enquanto continuarem sem.

---

## O que este inventário NÃO diz

**Não medi qualidade de código**, só existência, importador, teste e flag. Um
módulo "vivo" aqui pode estar mal escrito; um "sem teste" pode estar correto.

**Não executei os 27 módulos sem teste** para saber se funcionam. "Sem teste"
é ausência de verificação, não presença de defeito.

**Não medi quanto custa acoplar.** As estimativas de "trabalho pequeno/médio"
são julgamento a partir de tamanho e cobertura — não são medição, e este
projeto já aprendeu duas vezes o que acontece quando se trata julgamento como
medida.

---

## Recomendação, que não é decisão

Se o objetivo é **acoplar ao MVP**: `emit_ranking_decision` é o único candidato
que eu chamaria de pronto. Ele responde a pergunta que o `DIAGNOSTICO v1`
deixa em aberto, tem teste, e não exige tocar na régua.

Se o objetivo é **serviço novo**: a Bancada é a base mais substancial que
existe — mas 3.000 linhas com 2 arquivos de teste não é fundação, é dívida com
forma de fundação.

E vale dizer o que o inventário mostrou de desconfortável: **55% dos módulos do
kernel não têm teste, e 12 flags de engenharia testada estão desligadas há
meses.** O ecossistema tem mais coisa construída do que decidida.
