# Achado — a dominância das `session_summary` tem causa mecânica: elas estão duplicadas

**18/08/2026.** Primeira leitura da telemetria de ranking vinda do store **vivo**
(`C:\edp_data_todo\edp_data`, kernel do Windows). N=7 eventos, janela
14:32–15:05.

Tier **D (medido)** para a contagem de duplicatas e a composição por tipo.
Tier **C (argumentado)** para o elo causal com a dominância — o elo é forte e
mecânico, mas N=7 e uma sessão só.

---

## 1. O que apareceu na telemetria

**Todo** evento de ranking traz pares de posições adjacentes com componentes
`{bm25, vec}` byte-idênticos:

```
14:32  rank1, rank2  ->  bm25=0.5627  vec=0.2423
14:35  rank1, rank2  ->  bm25=1.0     vec=0.8473
       rank3, rank5  ->  bm25=0.3572  vec=0.654
15:05  rank1, rank2  ->  bm25=0.7341  vec=0.7013
       rank4, rank5  ->  bm25=0.6293  vec=0.6419
```

Dois rankers independentes não produzem escores idênticos por acaso. Componente
idêntico nos dois significa **texto idêntico**.

Efeito: dos 5 itens entregues, frequentemente só **3 são conteúdos distintos**.
O orçamento de contexto é gasto repetindo.

## 2. Confirmação no store

| | entradas | ids únicos | textos únicos | grupos repetidos | cópias extras |
|---|---|---|---|---|---|
| pré-merge (backup 13:42) | 140 | 140 | 126 | 5 | **14** |
| vivo (pós-merge) | 165 | 165 | 151 | 5 | **14** |

Composição dos 5 grupos:

| cópias | tipo | conteúdo |
|---|---|---|
| **9** | `llm_response` | "Q: oi / A: Oi! Tudo bem? Como posso ajudar?" |
| 3 | `session_summary` | "Substantivos concretos: …" |
| 3 | `session_summary` | "**Redis:** …" |
| 2 | `session_summary` | "Substantivos concretos: …" |
| 2 | `session_summary` | "Mapeia valores → linhas (índice invertido)" |

**Quatro dos cinco grupos são `session_summary`.**

## 3. Por que isto explica a dominância melhor que as hipóteses anteriores

Havia duas explicações em circulação, e as duas ficam para trás:

**"Privilégios de nascença"** (H1 do exp009) — o caminho vivo não lê `prioridade`
nem `src_weight` no ranking, e `epistemic_status` só como exclusão binária. Não
há privilégio a remover. Ver `preregistro_experimento_009.md` §8-bis e
`test_mecanismo_aposentado_e_no_op.py`.

**"Propriedades do texto"** (comprimento, genericidade, centralidade semântica) —
foi o que **eu** propus em 18/08 como hipótese para o sucessor do exp009. O dado
não a sustenta e não precisou dela.

A explicação mecânica é mais simples e verificável: **um resumo armazenado 3×
tem três bilhetes no sorteio do top-5.** Não precisa vencer por mérito de
ranking; precisa só estar presente várias vezes. Nenhum fator de ordenação
explica isso porque não é um fenômeno de ordenação — é de composição do índice.

Nota de método: eu tinha escrito, no mesmo dia, que a hipótese do sucessor
deveria sair do dado e não de palpite. O palpite foi meu e o dado o contradisse
na primeira leitura.

## 4. O merge de hoje NÃO é a causa

A chave de dedup de `scripts/funde_stores.py` é `"id"`, e eu havia reportado
"zero colisões" como boa notícia. Duas cópias do mesmo conteúdo com ids
regenerados passariam por essa chave — então suspeitei de mim.

A tabela do §2 fecha a questão: **14 cópias extras antes, 14 depois**, mesmos 5
grupos. As 25 entradas novas são conteúdo genuinamente novo (`textos_unicos`
126 → 151, exatamente +25). O merge foi limpo.

As duplicatas são **pré-existentes** e anteriores à telemetria — não há linha de
base anterior para datá-las.

## 5. O mecanismo de conserto existe e nunca foi ligado

`_dedup_pass_exp017` (`store.py:1148`) colapsa duplicatas do ranking antes da
entrega, com `DEDUP_THRESH = 0.75` (`config.py:19`). O modo resolvido em
produção é `_mode = "off"` (`store.py:1535`).

Ou seja: o exp017 construiu exatamente o instrumento que este achado pede, e ele
está desligado por padrão. Isto **não** é um bug — é um experimento não disparado.
Mas muda a prioridade dele: deixou de ser hipótese e passou a ter alvo medido.

**Limitação da telemetria (minha):** o campo `n_apos_dedup` que instalei hoje
espelha `n_entregues` quando o modo está off. Com dedup desligado o estágio não
informa nada — o valor não é falso, é vazio. Quem ler a cascata precisa saber
disso.

## 6. Achado lateral — a fusão RRF é média, não soma

Escores observados: `0.016393 = 1/61` para item bem colocado nos dois rankers, e
`0.008197 = 1/122` para item ausente de um deles — confirmado nos dois sentidos
(`bm25=1.0, vec=0.0` e `bm25=0.0, vec=0.6322` dão o mesmo valor).

Com `rrf_k=60`, soma daria `2/61 = 0.0328`. O observado é metade disso, então a
implementação **divide pelo número de rankers**.

Consequência para o sucessor do exp008: acrescentar `overlap` como terceiro
ranker **muda o denominador de 2 para 3**, e portanto reescala todos os escores
existentes. Eu havia descrito a fusão de um terceiro ranker como se fosse
aditiva e neutra para os dois já presentes. Não é.

## 7. O `trat_trivial` tem alvo real

A regra v2 do exp009 §3a (`<3` tokens úteis) captura o grupo de 9 cópias de
"oi / Oi! Tudo bem?". É a única condição daquele pré-registro que sobrevive ao
caminho híbrido — e tem objeto medido, não hipotético.

## 8. O que este achado NÃO autoriza

- **N=7 eventos, uma sessão, um store.** Não há base para número de dominância.
- Não há medição de **antes/depois de ligar o dedup** — o efeito de colapsar as
  duplicatas é previsto, não medido.
- Não se sabe **como** as duplicatas entraram (gravação repetida? consolidação
  reprocessando? merge anterior?). A causa da duplicação segue aberta, e é
  diferente do efeito dela no ranking.
- A janela é de 33 minutos num dia em que o store foi fundido. Não é regime
  estacionário.

## 9. Próximo passo indicado

Antes de qualquer desenho de experimento de retrieval: **contar duplicatas por
tipo ao longo do tempo** e descobrir a origem da duplicação. Consertar a entrada
é mais barato que compensar na saída, e o dedup de leitura (exp017) trata o
sintoma.

Fonte primária: `data/_telemetria_windows/events.jsonl` (cópia de leitura de
18/08 16:07, 544 eventos, 131.973 bytes).

---

## Adendo — 19/08/2026: a duplicação está sendo medida em produção há tempo, por instrumento que já existia

Log de quatro turnos reais (kernel Windows, `claude-haiku-4-5`, 00:48–00:57):

```
00:48:35  [exp017] dup_rate id=0/5 hash=4/5
00:49:37  [exp017] dup_rate id=0/5 hash=0/5
00:51:12  [exp017] dup_rate id=2/5 hash=2/5
00:56:48  [exp017] dup_rate id=1/5 hash=1/5
```

**7 de 20 slots entregues (35%) são duplicata por hash normalizado**, com um
turno chegando a **4 de 5 (80%)**. `hash` é a mesma normalização do
`_dedup_pass_exp017` — ou seja, é exatamente o que o dedup colapsaria se
estivesse ligado.

O turno de 80% é visível no prompt renderizado:

```
[há 2 meses, llm_response] Q: oi  A: Oi! Tudo bem?  Como poss...   ← ×5
```

Cinco cópias do mesmo cumprimento ocupando **cinco dos dez blocos** do
retrieval, para a query `"oi"`. A recuperação está correta (casamento exato); o
que falha é não colapsar.

### Por que este adendo importa mais que a contagem original

O corpo deste documento contou duplicatas **no store** (14 cópias extras em 5
grupos) e inferiu o efeito no ranking a partir de escores idênticos na
telemetria. Isso era indireto.

O `dup_rate` mede **o que foi entregue ao prompt**, turno a turno, e é emitido
por instrumento que **já existia e já rodava** — nenhuma flag precisou ser
ligada, nenhum experimento precisou ser desenhado. O dado estava no log.

**Consequência prática:** o efeito de ligar `EDP_RETRIEVE_DEDUP` é estimável
**sem rodar experimento** — `dup_rate` já diz quantos slots seriam liberados por
turno. O que ele não diz é se a memória que entraria no lugar é melhor, e essa
parte continua exigindo medição.

### Limites

- 4 turnos. A média de 35% tem incerteza enorme e não é um número para citar
  sozinho.
- Os quatro turnos são de uma sessão, num dia, com um padrão de conversa só.
- `dup_rate` conta o que o dedup **colapsaria**, não o que está sendo
  desperdiçado em sentido semântico — duas memórias distintas com o mesmo texto
  normalizado são raras, mas o inverso (conteúdo redundante com texto diferente)
  não é contado aqui de forma nenhuma.

---

## Adendo 2 — 19/08/2026: o gerador é a DESCONEXÃO, não o uso

Observação que fecha a cadeia causal deste achado e **muda a prioridade do
conserto**.

### A evidência

Log de uma sessão contínua, nove turnos entre 00:48 e 01:26, sem nenhum
`[WS] desconectado`:

```
00:48  00:49  00:51  01:00  01:13  01:17  01:20  01:23  01:26   → 0 summary_write
```

Os dois `summary_write` que existem no store vieram logo após os dois
disconnects anteriores, às 00:45:22 e 00:47:44.

`generate_session_summary` é chamado dentro de
`except WebSocketDisconnect` (`websocket.py:1376`). **Nove turnos de conversa
real produziram zero resumos; dois fechamentos de aba produziram dois.**

### O que isso corrige no entendimento anterior

O corpo deste documento tratava a duplicação como acúmulo. Não é.

> **O gerador de `session_summary` não é o volume de conversa — é a frequência
> de desconexão.**

Quem deixa uma aba aberta o dia inteiro produz **zero** resumos. Quem recarrega
a página cinco vezes produz **cinco**, todos sobre a mesma janela
`entries[-10:]`, todos praticamente idênticos.

Os 5 grupos com 2–3 cópias cada não são acúmulo gradual. São **rajadas de
refresh**.

Isso também explica a composição do store: **32 de 137 entradas (23%) são
`session_summary`** — desproporção que faz sentido para um gerador acionado por
evento de transporte, e nenhum para um acionado por conteúdo.

### Consequência prática — inverte a prioridade

Eu havia colocado a guarda de escrita e o dedup de leitura como duas frentes
paralelas. Não são equivalentes:

| conserto | o que faz | alcance |
|---|---|---|
| `EDP_SUMMARY_DEDUP` (escrita) | não grava resumo acima do limiar | **ataca a fonte** — sem cópia no store, nada a colapsar depois |
| `EDP_RETRIEVE_DEDUP` (leitura) | colapsa duplicata no ranking | trata o sintoma a cada turno, para sempre |

A guarda de escrita é **mais importante** do que eu disse, porque o gerador é
acionado por um evento que o usuário não controla conscientemente — queda de
rede, fechamento de aba, reconexão do navegador. É uma fonte que só cresce.

Nota: o dedup de leitura continua necessário para as duplicatas **já existentes**
e para as de `llm_response` (as 9 cópias de "oi"), que a guarda de escrita não
toca.

### Observação lateral — falha duplicada ocupa dois slots

No prompt de 01:17, duas cópias idênticas de um `camara_response` cuja resposta
é *"O contexto original que recebi está vazio — não há pergunta explícita à qual
responder."*

Uma **falha** armazenada, recuperada duas vezes, ocupando dois dos slots
entregues. E em 01:20/01:23, `retrieval_kept` traz `[..., 3122, 3122, ...]` —
6.244 caracteres gastos com o mesmo texto no mesmo prompt.

O `answer_class` tóxico (`not_found`, `disqualification`) já é excluído do índice
híbrido quando `EDP_TOXIC_GUARDS` está ligada (`store.py:1662`). Este caso
sugere que respostas de falha do caminho `camara_response` não estão sendo
classificadas — mas isso é **hipótese**, não verificado, e é outra investigação.

---

## Adendo 3 — 19/08/2026: a duplicação na entrega, medida com N útil

Substitui a estimativa de 35% do Adendo 1, que vinha de **4 linhas de log** e
era anedota. Agora são **50 turnos** de `ranking_decision` do store vivo,
janela 04/06 → 19/08.

Método: para cada turno, contar quantos itens entregues compartilham o par
`(bm25, vec)` com outro item do mesmo turno. Dois rankers independentes não
produzem escores idênticos por acaso — par idêntico significa texto idêntico.

### O número

```
itens entregues .......... 246
duplicados ...............  61
fração ................... 24,8%   IC 95% [20,5% ; 29,7%]
turnos com ≥1 duplicata ... 44/50 = 88%   IC 95% [78% ; 96%]
```

IC por **bootstrap de turno** (cluster), não binomial simples: itens do mesmo
turno não são independentes, e tratá-los como tal estreitaria o intervalo
indevidamente.

Distribuição:

| dup/entregues | turnos |
|---|---|
| 1/5 | 29 |
| 2/5 | 11 |
| **0/5** | **6** |
| 1/3 | 2 |
| 4/5 | 2 |

**Apenas 6 dos 50 turnos (12%) entregam contexto sem repetição.**

### O que isso autoriza, e o que não

**Autoriza:** dizer que **um quarto do orçamento de contexto entregue é
redundante**, com incerteza declarada, em regime de uso real. Ligar
`EDP_RETRIEVE_DEDUP` liberaria em média **1,22 slot de 4,9 por turno**.

**Não autoriza** dizer que a resposta melhora. O dedup libera slot; se a memória
que entra no lugar é melhor que a cópia que saiu, isto **não mede**. Essa é a
parte que ainda exige experimento, e é a única que sobrou.

### Correção da estimativa anterior

O Adendo 1 reportou **35%** a partir de 4 turnos (`dup_rate hash = 4/5, 0/5,
2/5, 1/5`). O valor real é **24,8%**, e 35% cai fora do IC. A amostra de 4
turnos pegou por acaso o turno de 80%, que a distribuição acima mostra ser raro
(2 de 50).

Foi exatamente o erro contra o qual o próprio Adendo 1 avisava — *"a média de
35% tem incerteza enorme e não é um número para citar sozinho"* — e eu o citei
sozinho no commit e na conversa. O aviso estava escrito e não impediu nada.
