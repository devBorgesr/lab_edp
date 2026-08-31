# REL-001 — STATUS = BLOQUEADO

**31/08/2026.** Nenhum resultado de qualidade existe. Não há κ, não há Recall@K,
não há ground truth. O que segue é a caracterização do bloqueio.

Corpus medido: `~/Desktop/edp_data_todo/edp_data/sessions/default_cognitive/`
(`episodic` sha `d64fcc74a0c7e9b0…`, `semantic` sha `632a7f228045f89c…`), sobre
as 50 queries de `amostra_congelada.json`. Medido em cópia, não no store vivo:
`retrieve` incrementa `acessos`/`ultimo_acesso` e salva.

---

## 1. Dois problemas, e o primeiro não causou o segundo

**Problema A — execução.** O `congela_pares.py` passou os documentos em ordem de
inserção do arquivo como se fossem ranking. Erro de código, corrigido.

**Problema B — protocolo × corpus.** Com o retriever real e correto, o `§3.2`
continua insatisfazível: ele tira a `cauda` das posições 20–50 e exige 50
documentos distintos; o corpus entrega 29–40.

**B não é consequência de A.** B estava lá desde o começo e teria bloqueado a
rodada mesmo que A nunca tivesse existido. A ordem em que apareceram é acidente:
A escondeu B, porque ordem de arquivo tem 136 ids distintos e passava no guard.

## 2. Evidência — as três causas, medidas separadamente

Não bastava mostrar que falta; era preciso dizer de qual das três causas.

### Limitação do retriever — **descartada**

| | |
|---|---|
| `top_k` pedido | 50 |
| candidatos varridos internamente | 150 (`k = min(top_k*3, N)`) |
| slots devolvidos, nas 50 queries | **50, 50, 50** — sem exceção |

O retriever preenche todos os slots e varre o triplo. Não devolve menos do que
se pede.

### Duplicação de armazenamento — **é a causa, e explica 100%**

| | |
|---|---|
| entradas em `episodic` + `semantic` | 137 + 61 = 198 |
| documentos **distintos** | **137** |
| ids presentes nas duas camadas | **61** — 100% da camada semântica |
| entradas no índice híbrido | 192 (6 fora por `filtro_recusa`, Dívida #49) |
| ids distintos no índice | 133 |
| textos distintos no índice | **119** |

Por query, dentro do top-50: 8 a 19 slots são um documento que já apareceu.

**616 ids repetidos nas 50 queries. 616 deles — 100% — estão nas duas camadas.
Zero repetições sem essa causa.** A atribuição é medida, não inferida.

### Limitação do corpus — **descartada, e este é o dado que decide a matriz**

Pedindo o ranking inteiro (`top_k=192`) e deduplicando:

| | min | mediana | max | queries ≥50 |
|---|---|---|---|---|
| ids distintos | 112 | 132 | 132 | **50 de 50** |
| textos distintos | 98 | 118 | 118 | **50 de 50** |

**O corpus tem material distinto de sobra.** A duplicação não esgota o corpus —
ela consome slots *dentro da janela de truncamento*. Crescer o corpus não é
necessário, e isso passa de suposição a medida.

### Um segundo eixo de duplicação, menor mas real

133 ids distintos produzem apenas **119 textos distintos**: 14 documentos com id
próprio e texto idêntico a outro. Em 5 das 50 queries isso reduz a contagem
abaixo dos ids distintos. É a outra causa já conhecida — `session_summary`
regenerado por `WebSocketDisconnect`, mesmo texto, id novo. Não é o que bloqueia
o `§3.2`, mas quem redesenhar a `cauda` precisa contar textos, não ids.

## 3. Impacto

| artefato | estado |
|---|---|
| `pares_congelados.json` | **INVÁLIDO**, marcado no arquivo, recusado pelo loader |
| `rotulos_llm.json` (492) | **INVÁLIDO**, idem |
| `rel_001a_viabilidade.md` | **veredito contaminado** — ver §6 |
| `REL-001_SMOKE.md` | coluna `estrato` inválida; conectividade, formato, parse e latência valem |
| `amostra_congelada.json` | válido, **não reaberto** |
| `dominio_congelado_v2.json` | válido |
| `REL-001_CONFIG_CONGELADA.json` | válido |

Nenhum julgamento humano perdido — o caminho A não começou.

## 4. Alternativas — matriz, com a coluna que a medição corrigiu

| opção | muda o protocolo? | muda o retriever? | muda o corpus? | pode ser REL-001? |
|---|---|---|---|---|
| reduzir a janela da cauda (20–35) | **sim** | não | não | não → REL-002 |
| reduzir `N_DOCS_POR_QUERY` | **sim** | não | não | não → REL-002 |
| corrigir `_hybrid_index` | não no texto, **sim no sujeito** | **sim** | não | não → exige `FORMAT_STATE_FLAGS` + pré-registro |
| `EDP_RETRIEVE_DEDUP` só na coleta | não no texto, **sim no sujeito** | **sim** | não | não → mediria outro retriever |
| aumentar o corpus | não | não | sim | **desnecessário** — §2 mostra 112–132 distintos disponíveis |
| ranking com menos de 50 | **viola o §3.2** | não | não | não |

**Correção de leitura:** a versão anterior desta matriz listava "aumentar o
corpus" como caminho plausível. A medição do teto derruba isso — o corpus já
tem 112–132 distintos por query. Restam apenas alternativas que mexem no
protocolo ou no retriever, e nenhuma pode ser REL-001.

### O que a matriz sozinha não mostra

Deduplicar **renumera as posições**. Um documento na posição 30 do ranking
deduplicado está por volta da 45 no ranking de produção. O `§3.2` diz "posições
20–50 do mesmo retriever" — e sob dedup essa frase passa a apontar para outro
conjunto de documentos, sem que uma linha do pré-registro mude.

Ou seja: a escolha não é só "quanto material tem". É **de qual ranking as
posições do §3.2 falam** — o que produção entrega, ou o deduplicado. Os dois são
defensáveis; o que não se pode é trocar um pelo outro em silêncio.

## 5. Dependências

O bloqueio depende de uma única propriedade: a consolidação promove de episódica
para semântica **sem remover da origem**, e `_hybrid_index` varre as duas camadas
sem deduplicar por id (`store.py:1616`). Medido nos **17 stores** de
`edp_data_todo/`: em todos, 100% dos ids semânticos também estão na episódica.
Não é acidente de um corpus.

O defeito de produção fica **declarado e não consertado** neste ciclo.

## 6. O veredito de viabilidade estava errado, e dá para apontar onde

`rel_001a_viabilidade.md`, linha 22:

> `| documentos para ranking de 50 posições | 50 | 198 | OK |`

**198 é o número de entradas do índice, não de documentos.** Os documentos eram
137, e no índice 133. E a verificação empírica (linhas 83–85) contou *slots*
devolvidos — 50/50 — que é justamente a métrica que a duplicação deixa intacta.

As duas checagens usaram o número que a duplicação infla.

### O achado contraditório existia, e era mais explícito do que eu registrei

`ACHADO_MESMO_ID_INDEXADO_DUAS_VEZES.md` (`a434cdf`, **30/08 15:46**, 33 minutos
depois do último commit da viabilidade) já dizia, na §4:

> - o `topo` pode ter menos de 5 documentos distintos;
> - o **mesmo documento** pode cair em `topo` e em `cauda`

e prescreveu a correção:

> Correção no harness: deduplicar o ranking por id **antes** de fatiar. Isso não
> altera o protocolo.

Aplicar essa correção é **exatamente** o que produziu o `29–40 < 50`. A frase
"isso não altera o protocolo" estava errada: não altera o texto do `§3.2`, e o
torna insatisfazível.

O achado ficou a uma pergunta de distância: *se eu deduplicar, ainda existem 50
posições?* Ninguém a fez — nem quando o achado foi escrito, nem quando o dedup
entrou no `monta_pool`, nem quando a coleta foi autorizada no dia seguinte.

## 7. Dependências contaminadas — a contagem, antes de propor regra

O auditor pediu medir antes de mexer no NORTE. Medido:

| artefato | conclusão dependente | estado |
|---|---|---|
| `rel_001a_viabilidade.md` | "o corpus sustenta o protocolo" | **errada** |
| `ACHADO_MESMO_ID…md` §4 | "isso não altera o protocolo" | **errada** |
| `REL-001_SMOKE.md` | coluna `estrato` | **parcial** |
| `pares_congelados.json` | — | dado inválido |
| `rotulos_llm.json` | — | dado inválido |

**Cinco artefatos, dois deles documentos de veredito, um ciclo.**

Não escrevo regra de NORTE com isso. Cinco é pouco para dizer que o método tem
um buraco sistemático, e o `§4.4` já obriga a errata — o que faltou não foi a
obrigação de corrigir, foi um **gatilho**: nada avisou que um achado novo
contradizia um veredito fechado três dias antes.

A recomendação é medir isto de novo no próximo ciclo em que um achado invalidar
uma medição, e só então decidir. Uma regra escrita a partir de um caso descreve
o caso, não o método.

## 8. Decisão pendente

O trabalho para depois de decidir, uma variável por vez:

```
PROTOCOLO     redesenhar a cauda -> REL-002, poder recalculado
RETRIEVER     corrigir _hybrid_index -> pré-registro próprio, flag, antes/depois
CORPUS        descartado por medição (§2)
```

Nada prossegue sem decisão explícita. O harness agora recusa: ranking sem prova
de procedência, ranking com menos de 50 distintos, e artefato marcado inválido.
