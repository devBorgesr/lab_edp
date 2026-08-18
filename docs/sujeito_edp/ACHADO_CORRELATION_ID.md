# Achado — o `correlation_id` não atravessa a fronteira de thread

**2026-08-18.** Investigado a pedido de auditoria externa, que apontou
`correlation_id` nulo em 18/18 registros de lineage e sugeriu que isso
desfaria o argumento de valor da telemetria de 13/08.

**A sugestão está parcialmente certa, e a manchete correta é outra.**

---

## 1. O que foi medido

`data/pareto/events.jsonl`, 93 eventos:

| evento | total | com `correlation_id` |
|---|---|---|
| `token_usage` | 38 | **38** |
| `camara_outcome` | 2 | **2** |
| `memory_accessed` | 35 | 17 |
| `memory_added` | 18 | **0** |
| `ranking_decision` | **0** | — |

`data/sessions/default_cognitive/lineage.jsonl`, 18 registros:
**0/18** com `correlation_id`.

## 2. A correção da manchete

> **A junção não está quebrada. Ela nunca foi exercitada.**

O canal que eu construí em 13/08 popula o campo em **100%** dos casos
(`token_usage` 38/38). O que não existe é o **outro lado**:
`ranking_decision` tem **zero eventos**, porque `EDP_RANKING_TELEMETRY`
nunca foi ligada.

Portanto o que eu afirmei — *"no mesmo turno dá para ver quanto custou e por
que escolheu aquelas memórias, do mesmo lado da junção"* — descreve um
mecanismo **presente e demonstravelmente populado num dos lados**, e uma
junção **nunca testada de ponta a ponta**. A diferença importa: eu não posso
dizer que funciona, e não devia ter implicado que sim.

## 3. O defeito real, com mecanismo

O `correlation_id` nulo no lineage é problema **separado**, e tem causa
identificada:

```
llm_adapter.py:1594  set_current_correlation_id(_cid)   ← thread-local
                     ...
websocket.py:629     loop.run_in_executor(...)          ← FRONTEIRA
                     ...
websocket.py:1318    get_lineage_tracker().build(...)   ← outra thread
lineage.py:177       get_current_correlation_id()       ← devolve None
```

A chamada de LLM roda num **executor**; o `set_current_correlation_id` grava
num **thread-local** daquela thread. O lineage é montado no handler assíncrono,
em thread diferente, onde o thread-local está vazio.

`lineage.py:172` já documenta o campo como *"melhor esforço via thread-local"*
— então o comportamento é o previsto pelo autor. O que não estava previsto é
que o melhor esforço falha **sempre**, não às vezes.

Isso também explica `memory_added` em 0/18: a escrita ocorre fora da thread
que definiu o id.

E explica `memory_accessed` em 17/35: os retrieves de dentro da chamada de LLM
carregam o id; os disparados por outro caminho, não.

## 4. Consequência para o E10b

O E10b precisaria relacionar **custo semântico** (embeddings, e o E9c ensinou
a medir custo) com **resultado do turno**. Essa relação depende exatamente da
junção que não existe hoje.

Ordem que isso impõe: **consertar a propagação antes do E10b**, ou desenhar o
E10b sem depender de junção por turno — e declarar qual dos dois.

## 5. O que NÃO fazer

Trocar o thread-local por variável global consertaria o sintoma e criaria
condição de corrida entre turnos concorrentes. O caminho correto é
`contextvars`, que atravessa `run_in_executor` quando o contexto é copiado, ou
passar o `correlation_id` explicitamente como argumento do `build()`.

**Nenhuma das duas foi implementada aqui.** Este documento é achado, não
correção — e a correção mexe no caminho vivo do turno, portanto pede flag e
prova de flag-off byte-idêntico pelo `NORTE §4.7`.
