# preregistro_experimento_018.md — Promoção tóxica pelo caminho automático

**Pergunta de pesquisa:** quais dos caminhos que alcançam `consolidate()`
promovem uma entry com `answer_class` tóxico a `SemanticMemory`, e o fix
óbvio — portar a guarda existente para dentro de `consolidate()` — fecha o
furo ou é cego para metade dos casos?

## 2. Régua / nota de método

Registrado ANTES de qualquer implementação ou medição. Nenhuma condição,
métrica ou corte pode ser alterada depois de ver o dado — mudar a régua
exige exp018b com pré-registro próprio. Predições do §4 são falsificáveis e
ficam registradas mesmo se refutadas.

**Natureza do experimento: PREVENTIVO, não forense.** A medição de 28/07
(§3 item 9) mostrou que o store de trabalho não tem carimbo `answer_class`
algum — os furos aqui investigados são DORMENTES nos dados e reais no
código. Este experimento prova antecipadamente o que o backfill de produção
ativaria. Quem ler isto esperando explicação de um vazamento já ocorrido vai
se decepcionar de propósito.

Sujeito: EDP em `788d7f5` (branch `exp017/fase1-dedup`), store CÓPIA, nunca
produção.

## 3. Motivação / Contexto provado (file:line verificado em 28/07/2026)

1. `consolidate_promote_only()` (`edp/consolidation.py:230`) TEM guarda de
   toxicidade, em `:290`: `if EDP_WRITE_PROVENANCE and e.get("answer_class")
   in TOXIC_ANSWER_CLASSES`. O docstring (`:242-243`) registra que ela nasceu
   do furo medido em 14/07/2026 (Fase 5).
2. `consolidate()` (`edp/consolidation.py:157-229`) promove por
   `acessos >= promote_threshold` (default **3**) e **não menciona
   `answer_class` em nenhuma linha**. Sem guarda.
3. Três caminhos alcançam `consolidate()` sem guarda:
   - `edp/cognitive_scheduler.py:171` — `apply_actions()`, ação
     `"consolidate"`, dentro de `not dry_run` (código vivo, não comentário)
   - `edp/consolidation.py:326` — `auto_consolidate()`, registrado como job
     de background no lifespan (`edp/api/main.py:211-213`)
   - `edp/api/routes/memory.py:492` — endpoint HTTP
   Em todos, `promote_threshold` fica no default 3.
4. `exp009` mediu acesso inflado de `session_summary`: **13,9 vs 4,2** —
   muito acima do threshold 3.
5. `E7` (28/07) mediu **27 de 133 entries (20,3%)** da episódica sendo
   `[session_summary]`.
6. `exp017` Fase 0 §5 registra a entry `31162822` (summary ecoado, modo de
   falha do exp009) promovida à semântica. **RESSALVA REGISTRADA (medida em
   28/07):** isso é promoção de conteúdo *semanticamente* ruim, NÃO de entry
   *carimbada* com `answer_class` tóxico — categorias distintas, e a guarda
   de `:290` só vê a segunda. A versão anterior deste pré-registro chamava
   isso de "caso confirmado"; era conflação, corrigida aqui.
7. `exp017` Fase 0: 100% da camada semântica é cópia por ID da episódica.
8. **`merge_cluster()` APAGA o marcador e AMPLIFICA o contador.** O dict de
   retorno (`edp/consolidation.py:142-153`) tem dez chaves e `answer_class`
   não é uma delas. No mesmo bloco, `:119` faz
   `total_acessos = sum(e.get("acessos", 0) for e in grupo)` — os acessos
   SOMAM. Logo duas entries que individualmente não cruzam o threshold
   (2 < 3) fundem numa que cruza (4 >= 3), sem rastro de toxicidade.
   `cluster_entries()` (`:22-54`) agrupa por cosseno puro, sem consciência
   de `answer_class`, e uma resposta de falha e uma de sucesso sobre o MESMO
   assunto tendem a ficar próximas no embedding.
   `consolidate_promote_only()` é imune por design (docstring `:232`:
   "NÃO-DESTRUTIVO... sem mesclar nada") — nunca funde, e é por isso que a
   guarda dela é segura hoje.
   **Precedente do fix correto no mesmo trecho:** `:117` faz
   `melhor_prio = max(grupo, key=lambda e: PRIO_ORDER.get(...))` — já existe
   propagação conservadora de campo pelo extremo do cluster. `answer_class`
   deveria seguir a mesma regra.
9. **O store de trabalho não tem carimbo algum** (verificado em 28/07 sobre
   `C:\edp_data_fase0`): episódica 133/133 e sprint 19/19 SEM
   `answer_class`; semântica 51/51 e 7/7 idem; `merged_from` = 0 em ambos os
   scopes — o merge nunca rodou aqui, e a promoção do `31162822` não veio
   por fusão. O `ESTADO_EXP012.md:92,122,163-164` explica: as 23 entradas
   carimbadas do arco vivem em `C:\edp_data_hybrid_test` e
   `C:\edp_data_exp016`, e o **backfill de produção está PENDENTE**.
   **Consequência (dependência de ordem, não registrada em documento algum
   antes desta medição):** hoje a maquinaria de toxicidade — piso
   `NOT_FOUND_FLOOR`, exclusão híbrida, guarda de `:290` — é inerte por
   falta de alvos. O backfill ativa ao mesmo tempo a proteção e a
   vulnerabilidade. Logo este experimento e o fix que ele justifica são
   **PRÉ-REQUISITO do backfill de produção**.

## 4. Hipótese(s) e predições

**H1 (vazamento por ausência de guarda):** entries com `answer_class` tóxico
e `acessos >= 3` são promovidas a `SemanticMemory` pelos caminhos que chamam
`consolidate()`, independentemente de `EDP_WRITE_PROVENANCE`.

**H2 (guarda acoplada a flag de rollback):** `consolidate_promote_only()`
NÃO promove tóxico com `EDP_WRITE_PROVENANCE=1`, mas **promove** com
`EDP_WRITE_PROVENANCE=0` — a proteção está atrás da mesma flag que serve de
rollback do feature de proveniência. Segunda ocorrência do padrão; a
primeira é `semantic.py:99-150` sob `EDP_HYBRID_RETRIEVAL=0`.

**H3 (fix ingênuo insuficiente):** portar a guarda de `:290` para dentro de
`consolidate()` NÃO fecha o furo, porque `merged.get("answer_class")` é
sempre `None` para entries fundidas. A guarda protegeria apenas o branch de
entries que ficaram sozinhas no cluster — subconjunto estrito do que
`consolidate()` promove.

**H0:** nenhuma entry tóxica aparece em `semantic` após as rodadas — existe
filtro anterior não visto na leitura, ou o caminho automático nunca atinge
`acessos >= 3` na prática.

**PREDIÇÕES PRÉ-DADO (arriscadas, podem falhar):**
- `consolidate()` promove tóxico em **100%** dos casos plantados com
  `acessos=3`, nas duas posições da flag (C1, C2).
- `consolidate_promote_only()` promove **0%** com flag ON (C3) e **100%**
  com flag OFF (C4).
- O controle negativo (`acessos=2`, C6) promove **0%** em todas.
- Em C7, a entry fundida É promovida, e inspecionando-a `answer_class` está
  AUSENTE e `merged_from == 2`. Se a fundida vier COM `answer_class`, H3
  está refutada e o fix ingênuo basta.
- As duas classes de `TOXIC_ANSWER_CLASSES` se comportam de forma idêntica
  em todas as condições (se divergirem, a guarda trata os membros do set de
  forma desigual — achado próprio, reportar).

## 5. Condições / Desenho experimental

Store sintético isolado (sessão `__lab__` própria por condição), entries
plantadas com forma conhecida.

| Cond. | função | entries plantadas | flag |
|---|---|---|---|
| C1 | `consolidate()` | tóxicas, `acessos=3` | 1 |
| C2 | `consolidate()` | tóxicas, `acessos=3` | 0 |
| C3 | `consolidate_promote_only()` | tóxicas, `acessos=3` | 1 |
| C4 | `consolidate_promote_only()` | tóxicas, `acessos=3` | 0 |
| C5 (controle +) | ambas | normais (`answer_class` ausente), `acessos=3` | 1 |
| C6 (controle −) | ambas | tóxicas, `acessos=2` | 1 |
| C7 (decisiva de H3) | `consolidate()` | A(tóxica, `acessos=2`) + B(normal, `acessos=2`), embeddings com cosseno > `EDP_CLUSTER_THRESH` (0.80, `config.py:122`) | 1 |

C5 prova que a promoção funciona (se não promover, o experimento não mede
nada). C6 prova que o threshold é respeitado (se promover com 2, o achado é
sobre o threshold, não sobre toxicidade). C7 é a única em que nenhuma entry
cruza o threshold sozinha — só a soma do merge cruza; **verificação
obrigatória de que a fusão ocorreu**: a entry resultante deve ter
`merged_from == 2`; se não tiver, o cluster não fundiu e C7 é INCONCLUSIVA
(ajustar a similaridade dos embeddings plantados, nunca o threshold do EDP).

A flag é lida no import de `config.py`, então **cada posição da flag exige
processo separado** — lição do exp017 Fase 0: alternância in-process mede a
mesma condição duas vezes e reporta "não move nada".

## 6. Critério de decisão (PASSA/FALHA)

- **H1 CONFIRMADA** se qualquer entry tóxica aparecer em `memory.semantic`
  após C1 ou C2 → dívida acionável: guarda dentro de `consolidate()`.
- **H2 CONFIRMADA** se C3 promover 0 e C4 promover ≥1 → dívida
  arquitetural nomeada: guarda de segurança não compartilha flag com
  rollback de feature.
- **H3 CONFIRMADA** se C7 promover a fundida e ela vier sem `answer_class`
  → a dívida passa de "uma linha copiada" para DUAS mudanças: (1) check
  pós-merge em `consolidate()`, E (2) `merge_cluster()` propagando
  `answer_class` conservadoramente, no molde do `melhor_prio` (qualquer
  tóxico no cluster ⇒ fundida tóxica).
- **H0** se C1..C4 e C7 promoverem 0 e C5 promover ≥1 → há filtro não
  mapeado; achar e documentar antes de qualquer fix.
- **INCONCLUSIVO** se C5 promover 0, ou C6 promover ≥1, ou C7 não fundir —
  nesses casos o instrumento está errado e nada se conclui sobre toxicidade.

Ordem de leitura obrigatória: C5 e C6 (validade do instrumento) ANTES de
qualquer interpretação de C1..C4 e C7.

## 7. Data de pré-registro

Escrito em 28/07/2026, antes de qualquer implementação do harness.
Emendado no mesmo dia, ainda pré-dado, com os itens 8 e 9 do §3, a H3, a
condição C7 e as correções de §8/§9 — todas derivadas de leitura de código
e de medição observacional do store, nenhuma de resultado do experimento.

## 8. Dataset (CONGELADO)

Entries sintéticas, texto fixo e distinto por condição (para rastrear qual
promoveu). Campos: `id` (uuid4 fixo, listado no relatório), `text`,
`answer_class`, `acessos`, `embedding` (determinístico por hash do texto,
nunca aleatório), `prioridade`, `timestamp`, `layer`.

**Ambas as classes tóxicas são plantadas:** `TOXIC_ANSWER_CLASSES` tem dois
membros (`{"not_found", "disqualification"}`, `config.py:95`) e testar um só
não valida o outro. Cada condição tóxica planta 2 entries de `not_found` e
2 de `disqualification` — 4 tóxicas por condição, mesmo custo.

**O dataset carrega `answer_class` de propósito**, o que significa que o
experimento mede o mundo PÓS-BACKFILL, não o store atual (§3 item 9). É a
escolha certa: o furo que interessa é o que vai existir, não o que está
dormente.

Nenhuma entry vem de store real — o experimento não depende do conteúdo de
produção, só da mecânica.

## 9. Métricas

- `promovidas`: contagem absoluta de entries plantadas presentes em
  `memory.semantic.entries` após a chamada, por condição e por classe
  tóxica.
- `merged_from` da entry resultante em C7 (prova de que a fusão ocorreu).
- `answer_class_presente`: booleano, na entry fundida de C7 — é o que
  decide H3.
- `leak_ok`: `verify_no_leak(fingerprint_antes, fingerprint_depois)` por
  condição. Se falso em qualquer condição, **nenhum resultado é reportado**.

Nota: a métrica `taxa_promocao_toxica` da versão anterior foi REMOVIDA. Com
N pequeno uma taxa não estima nada, e o §6 decide por presença/ausência —
métrica declarada-antes que não decide nada é ruído.

## 10. Anti-mock e Isolamento

**Anti-mock é obrigatório e não negociável:** roda `consolidate()` e
`consolidate_promote_only()` REAIS, importadas de `edp.consolidation`, e
`apply_actions()` REAL para o caminho do scheduler. Reimplementar a lógica
invalidaria o experimento — o furo de 14/07 só apareceu rodando o caminho
real, e a metodologia fundadora registra o Anti-Padrão de Mock exatamente
por isso (mock que aceitava kwargs onde produção usava dataclass).

Isolamento: `bancada/isolamento.py::experimental_session` com `purge=True`,
fingerprint antes/depois, `EDP_BASE_DIR` apontando para cópia. Nenhuma
condição escreve em produção; `verify_no_leak` é gate de reporte, não
verificação decorativa.

## 11. Constantes congeladas

| Constante | Valor |
|---|---|
| PROMOTE_THRESHOLD | 3 (default de `consolidate()`) |
| ACESSOS_TRATAMENTO | 3 |
| ACESSOS_CONTROLE_NEG | 2 |
| ACESSOS_C7_CADA | 2 (soma 4 no merge) |
| ANSWER_CLASS_TOXICO | `["not_found", "disqualification"]` |
| N_TOXICAS_POR_CONDICAO | 4 (2 de cada classe) |
| N_NORMAIS_C5 | 2 |
| CLUSTER_THRESH_ALVO | > 0.80 (`EDP_CLUSTER_THRESH`, `config.py:122`) |
| SCOPE | `cognitive` |
| EDP alvo | `788d7f5` |