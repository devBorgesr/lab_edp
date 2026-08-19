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
