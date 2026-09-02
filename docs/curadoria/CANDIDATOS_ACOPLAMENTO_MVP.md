# Candidatos de acoplamento ao MVP

**Nada foi acoplado.** Classificação com evidência, e a distinção obrigatória
entre *não altera a régua* e *muda a régua*.

---

## ACOPLAR AGORA (3)

### 1. `emit_ranking_decision` — o funil de retrieval

```
benefício ................. o auditor passa a explicar ONDE os candidatos se
                            perderam, não só quantos sobraram
pergunta do cliente ....... "por que só 37 documentos distintos de 50 slots?"
dado novo observado ....... n_avaliadas → n_acima_do_piso → n_apos_filtro_sessao
                            → n_apos_filtro_recusa → n_entregues, e os fatores
                            de score das 20 primeiras posições
arquivos .................. edp/memory/store.py:765,:1838
                            edp/runtime/pareto_store.py:707
flags ..................... EDP_RANKING_TELEMETRY (OFF)
testes .................... test_ranking_telemetry.py,
                            test_ranking_telemetry_caminho_vivo.py
mudança no contrato ....... SIM — novo método opcional no SistemaAuditavel
                            (ex.: `telemetria_do_funil()`), com default vazio
mudança no relatório ...... nova seção, NÍVEL 1 (observação)
mudança na régua .......... NÃO
risco de alterar resultado  NENHUM — a telemetria não muda o recuperado
                            (docstring: "com a flag OFF isto é um `if`")
maturidade ................ TESTADO, não VALIDADO em produção
```

**Por que é o melhor candidato:** responde a pergunta seguinte do cliente, não
toca na régua, e o dado já existe. O que falta é um `check` que o consuma e um
método opcional no contrato — nenhum dos dois altera `DIAGNOSTICO v1`.

**Ressalva:** um cliente que não seja o EDP **não tem** `emit_ranking_decision`.
Isto é acoplamento para o **adaptador do EDP**, e para qualquer cliente que
exponha telemetria equivalente. Não é capacidade universal.

### 2. Leitor de `events.jsonl` como fonte de evidência

```
benefício ................. o auditor lê a telemetria inteira sem tocar no
                            kernel nem no vocabulário dos dois lados
dado novo ................. 12 tipos de evento POSSÍVEIS; MEDIDO no store
                            vivo (Fase 3, 01/09): 395 eventos reais, só 6
                            tipos aparecem — memory_accessed (268),
                            memory_added (110), camara_outcome (8),
                            mode_switched (7), task_started (1),
                            task_completed (1)
arquivos .................. edp/runtime/pareto_store.py (FileParetoStore)
formato ................... JSONL append-only, rotação a 10 MB —
                            EXERCITADO EM PRODUÇÃO (não hipotético)
mudança no contrato ....... NÃO — é um adaptador novo, não uma mudança
mudança na régua .......... NÃO
risco ..................... MEDIDO, e é maior do que a Fase 2 registrou: os
                            5 tipos de evento mais interessantes para
                            diagnóstico — ranking_decision, reflection,
                            contradiction_scan, token_usage, summary_write —
                            NUNCA dispararam fora de teste. Estão atrás das
                            5 flags de telemetria OFF. Um leitor construído
                            hoje leria 395 eventos genéricos e ZERO
                            eventos do funil de retrieval.
maturidade ................ o FORMATO é EXECUTADO e TESTADO (não hipotético
                            — tem dado real, com data de 18/08); os DADOS
                            do funil de retrieval, que são o motivo de
                            interesse, existem só em teste. O leitor não
                            existe.
```

**Reclassificação (Fase 3).** Este candidato depende do candidato nº 1
(`emit_ranking_decision`) estar de fato ligado em algum ambiente de coleta —
sem isso, o leitor teria formato pronto e nada relevante para ler. Os dois
não são independentes: construir o nº 2 antes do nº 1 gerar dado real seria
construir consumidor para produtor que não roda.

### 3. Padrão `test_flag_off_byte_identical`

```
benefício ................. o MVP passa a provar que a PRÓPRIA instrumentação
                            não altera o que mede
arquivos .................. tests/test_flag_off_byte_identical.py (edp_v5)
mudança ................... só um teste novo no lado do auditor
risco ..................... nenhum
```

O auditor hoje prova que não altera o auditado **por cópia + hash**. Este
padrão prova por **saída byte-idêntica**. São garantias diferentes e
complementares.

---

## ACOPLAR DEPOIS DO PILOTO (4)

| candidato | por quê esperar |
|---|---|
| `emit_token_usage` — custo real por chamada | `UNIDADE_ECONOMICA.md` precisa disto, mas o piloto vai dizer se o custo dominante é modelo ou humano |
| `prontuario` — série longitudinal | "diagnóstico ao longo do tempo" é produto adjacente; sem cliente, não sabemos se alguém quer |
| `api/routes/flags.py` — ligar telemetria por HTTP | útil se o cliente hospedar o kernel; irrelevante se não |
| `emit_contradiction_scan` | telemetria de negativo é valiosa e ninguém pediu ainda |

---

## PRECISA DE TESTE ANTES (6)

Nenhum destes pode ser chamado de pronto. Todos têm **zero teste** medido:

```
sampler (240 L)            resolve não-determinismo
isolation (222 L)          verify_no_leak, production_contains
window_formats (316 L)     bateria de perturbação de contexto
observability/ (295 L)     logger e tracing
metrics (108 L)            22 importadores, 0 testes
context_builder (186 L)    montagem de contexto
```

`isolation` merece nota: `verify_no_leak` e `production_contains` resolvem
exatamente o problema que o MVP resolve por cópia. **São duas soluções para o
mesmo problema, e a do kernel não tem teste.**

---

## PRECISA DE EXPERIMENTO (2)

```
EDP_RETRIEVE_DEDUP     muda o conjunto recuperado -> MUDA O OBJETO AUDITADO
EDP_RETRIEVE_SHUFFLE   idem
```

São as opções B e C da `DECISAO_RANKING.md`, que segue **em branco**. Acoplar
qualquer uma sem decisão seria escolher pelo pesquisador.

---

## NÃO ACOPLAR

```
EDP_ANCHOR_COMPACT     muda o prompt
EDP_SUMMARY_DEDUP      muda o estado gravado
EDP_WIKI_CONVERSAS     flag de segurança/privacidade
reranker.py            0 importadores, 0 testes
retrieval.py cosine    caminho aposentado (exp008/exp009)
dashboard              decisão já tomada: depois do piloto
```

---

## OUTRO PRODUTO

O copiloto do `sf_exportador`. Ver `CANDIDATOS_NOVOS_SERVICOS.md`.

---

## A regra que estruturou esta classificação

```
não altera a régua   -> pode acoplar sem novo pré-registro
muda a régua         -> exige pré-registro e decisão do pesquisador
```

Os 3 de "acoplar agora" **não alteram a régua**: telemetria observa, não decide.
Os 2 de "precisa de experimento" **mudam o objeto auditado** — e essa é a
diferença que o REL-001 passou um mês descobrindo.
