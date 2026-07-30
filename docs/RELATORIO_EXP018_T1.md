# RELATÓRIO — exp018 T1 (leitura obrigatória, antes do harness)

Fonte: `/mnt/edp_v5_main` (mesmo conteúdo de `/media/sf_edp_v5_main`),
confirmado em `788d7f58f3c6571c97839e3ba82a523a36b587b5`, branch
`exp017/fase1-dedup` — bate com o sujeito declarado no pré-registro (§2).
Só leitura, nada escrito nesse mount.

## a) `cluster_entries()` — algoritmo de agrupamento

`edp/consolidation.py:22-54`. Confirmado: **greedy single-pass, ANCORADO no
primeiro elemento não-visitado, ordem de índice do array `entries`** — não é
single-linkage transitivo nem completo:

```python
for i in range(n):
    if visited[i]: continue
    cluster = [i]; visited[i] = True
    for j in range(i + 1, n):
        if not visited[j] and sim_matrix[i, j] >= threshold:
            cluster.append(j); visited[j] = True
    clusters.append(cluster)
```

Cada `j` entra no cluster se `cosseno(i, j) >= threshold` **com o âncora `i`**
— membros não são comparados entre si (ex.: B e C podem ter cosseno baixo
entre si e ainda cair no mesmo cluster que A, se ambos passarem no cosseno
com A). Isso é MAIS permissivo que "todo par > threshold", não menos — logo
**não ameaça C7**: bastam 2 entries (A, B) com `cosseno(A,B) >= threshold`
para garantir merge, é exatamente o par âncora-vizinho do laço acima.

**Sem condição de tamanho mínimo de cluster.** `CONSOLIDATION_CLUSTER_MIN`
(`config.py:160`, env `EDP_CLUSTER_MIN`, default 2) é **importado em
`consolidation.py:16` e nunca usado no arquivo** (confirmado por grep —
zero outras ocorrências no pacote `edp/`). Import morto; a única guarda de
tamanho que existe é o `if len(cluster) > 1` dentro de `consolidate()`
(decide merge vs. passthrough), não um mínimo pré-cluster.

**Discrepância de citação (não bloqueia nada):** o pré-registro (§5, §11)
cita `EDP_CLUSTER_THRESH (config.py:122)`. Na fonte, `EDP_CLUSTER_THRESH` é
o nome da ENV VAR lida pela constante Python `CONSOLIDATION_SIM_THRESH`,
definida em **`config.py:161`**, não 122 (linha 122 hoje é comentário do
exp017/Fase 1, assunto não relacionado — o arquivo cresceu desde a citação
original). Valor confirmado: `0.80` (default). Dataset/harness usam
`CONSOLIDATION_SIM_THRESH` (o nome real importável), citando `EDP_CLUSTER_THRESH`
só como nome de env var, igual ao código-fonte.

**GATE avaliado: NÃO disparado.** C7 é atingível como escrito.

## b) `consolidate()` — os dois branches de promoção

`edp/consolidation.py:157-212` (pré-registro cita `157-229`; a função
termina em `:212` — meros 17 linhas de folga na citação original, sem
efeito em nenhuma hipótese).

- **Branch pós-merge** — `:186-189`, dentro de `if len(cluster) > 1:`:
  ```python
  if merged.get("acessos", 0) >= promote_threshold:
      memory.semantic.promote(merged)   # :188
  ```
- **Branch de entry sozinha** — `:193-196`, dentro do `else:` (cluster de
  tamanho 1):
  ```python
  if entry.get("acessos", 0) >= promote_threshold:
      memory.semantic.promote(entry)    # :195
  ```

Nenhum dos dois branches menciona `answer_class` — confirma item 2 do §3.
`promote_threshold` default = `3` (assinatura da função, `:160`) — confirma
§11.

## c) `merge_cluster()` — dict de retorno e soma de acessos

`edp/consolidation.py:95-153`. Dict de retorno (`:142-153`), **dez chaves**
confirmadas: `id, text, embedding, timestamp, score_inicial, acessos,
ultimo_acesso, prioridade, layer, merged_from`. **`answer_class` NÃO está
entre elas** — confirma item 8 do §3 e a predição de H3.

`total_acessos = sum(e.get("acessos", 0) for e in grupo)` está em **`:119`**
(citação do §3 item 8 exata). `melhor_prio = max(grupo, key=...)` está em
**`:117`** (citação exata do "precedente do fix correto"). Ambos batem
byte a byte com o pré-registro.

**GATE avaliado: NÃO disparado — H3 não é refutada na leitura.** `answer_class`
ausente do merge confirma a predição pré-dado; segue para medição.

## d) `SemanticMemory.promote()`

`edp/memory/semantic.py:63-86`. `entry = dict(entry)` está em **`:81`** —
confirmado, cópia rasa preservando todos os campos recebidos (não filtra
nem whitelist de chaves); depois seta `entry["layer"]="semantic"` (`:82`) e
`entry["prioridade"]="alta"` (`:83`), `append` em `self.entries` (`:84`) e
`self.save()` (`:86`) — grava em `<session>_<scope>/semantic.json` (path
montado no `__init__`, `:44-46`).

**Achado extra, não previsto no pré-registro, relevante para o dataset do
T2:** `promote()` tem um guard ANTERIOR (`:69-80`, Dívida #49) que chama
`echo_chamber.detectar_auto_sinal_de_limite(entry.get("text",""))` e, se
`confianca == "alta"`, **retorna sem promover** — nenhuma das chaves acima é
setada, a entry nunca entra em `semantic.entries`. As frases-gatilho de
confiança "alta" (`echo_chamber.py:189-196`) são um conjunto fechado e
específico: `"não consigo responder"`, `"além do que posso afirmar com
honestidade"`, `"esgotei o método disponível"` (e variantes sem acento).
**Ação no T2:** os textos sintéticos de C1-C7 NÃO podem conter essas frases
literais, senão o não-promover observado seria confundido com a Dívida #49
em vez de medir a ausência de guarda de toxicidade — confound que
invalidaria o experimento silenciosamente. Os textos usam o prefixo
`[exp018-C{n}]` seguido de linguagem neutra de "não encontrado"/
"desqualificado" que não cruza esse regex (verificado por inspeção; o
harness não depende de `echo_chamber`, mas o dataset foi escrito evitando
as frases exatas listadas acima).

## e) `apply_actions()` / `_consolidate()` — caminho do scheduler

`edp/cognitive_scheduler.py:234-265` (`_consolidate`, gera as
`CognitiveAction` do tipo `"consolidate"`) exige, por cluster:
`len(valid) >= CONSOLIDATE_MIN` (`:37`, = 2) via `_valid_episodes()`
(`:93-110`, filtra por presença de `embedding` 1-D não vazio) **e**
`sim[i,j] >= CONSOLIDATION_SIM_THRESH` para os pares que entram no cluster
pelo mesmo algoritmo âncora do item (a).

Mas o branch relevante de `apply_actions()` (`:169-172`):
```python
elif a.action == "consolidate" and not dry_run:
    from .consolidation import consolidate
    consolidate(memory, threshold=CONSOLIDATION_SIM_THRESH)
    res["consolidate"] += 1
```
**ignora `a.target_ids`** — ao contrário dos branches `forget`/`deepen`/
`archive` (que iteram os ids da ação), o de `consolidate` simplesmente
chama a MESMA `consolidate(memory, ...)` já analisada nos itens (b)/(c)
sobre TODA a `memory.episodic`, não sobre o cluster específico que
disparou a ação.

**Decisão de escopo (autorizada pelo próprio §T1 do prompt):** montar o
estado para `CognitiveScheduler.evaluate()` emitir a ação (episódios no
formato que `_valid_episodes` aceita, mais o `MemoryStore` correspondente
para `apply_actions`) é aparato extra que o dataset do §8 não prevê — e,
como o branch de aplicação ignora o cluster e chama `consolidate()` puro,
**testar o caminho do scheduler não mede nada que C1/C2 (chamada direta a
`consolidate()`) já não meçam**: é a mesma função, mesma ausência de guarda,
mesmo resultado. Caminho do scheduler fica para exp018b (se algum dia
interessar testar side-effects específicos do `evaluate()`, como priorização
de ações, não a promoção em si). **C1/C2 se limitam à chamada direta de
`consolidate()`**, exatamente como o pré-registro previu como saída válida.

## Dimensão do embedding

`config.py:22-24`: `EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"`,
`EMBED_DIM = 384` (default, env `EDP_EMBED_DIM`). Dataset do T2 usa 384,
não chutado.

## Resumo dos GATEs do T1

Nenhum GATE disparado: (a) não ameaça C7, (c) não refuta H3. Segue para T2.
