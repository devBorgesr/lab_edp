# Os quatro números de duplicação — qual mede o quê

**30/08/2026.** Existem quatro medições de "duplicação" neste projeto, elas
medem **fenômenos diferentes**, e duas já estão numa página comercial.

Este documento existe para que ninguém cite o número errado — inclusive eu, que
já atribuí a duplicação inteira a uma causa quando eram duas.

---

## A tabela

| valor | IC | o que mede | fonte | fenômeno |
|---|---|---|---|---|
| **24,8%** | [20,5 ; 29,7] | slots **entregues** (top-5) com `(bm25, vec)` idêntico a outro | `ranking_decision`, N=50 turnos, store **vivo** | conteúdo duplicado na entrega |
| **25,5%** | — | slots do **ranking** (top-50) com **id** repetido | retriever real, 50 queries, snapshot 18/08 | mesmo doc indexado 2× (epi+sem) |
| **12,4%** | — | `dup_rate` id/hash no `kept` | exp017 T6, store `edp_data_fase0` | intra-query, no conjunto entregue |
| **15,4%** | — | `repeat_rate` binário **entre** queries | exp017 T6, mesmo store | queries **diferentes** devolvendo o mesmo |

## As três confusões possíveis

**Entrega ≠ ranking.** O 24,8% é sobre os 5 que chegam ao prompt; o 25,5% é sobre
os 50 que o retriever ordena. Um slot repetido no ranking pode nem ser entregue.

**Intra-query ≠ entre queries.** O 15,4% **não** é duplicação dentro de uma
resposta. É sobreposição entre queries **distintas** — a matriz par-a-par do T6,
onde `q00 × q01 = 0,75` significa que 75% dos resultados delas coincidem. É
fenômeno diferente, com implicação diferente.

**Id repetido ≠ conteúdo repetido.** O 25,5% conta o mesmo documento devolvido
duas vezes (causa: consolidação promove sem remover). O 24,8% conta textos
iguais com ids diferentes (causa: resumo regravado por disconnect). Ver
`ACHADO_MESMO_ID_INDEXADO_DUAS_VEZES.md`.

## O que nenhum deles significa

**Nenhum é "X% do contexto do RAG é inútil".** Todos medem repetição de slot.
Que a repetição desperdice contexto é inferência plausível e **não medida** — o
efeito na qualidade da resposta não foi testado em lugar nenhum deste projeto.

## Um número que eu não consigo reconciliar

A landing traz *"15,7% — Duplicação intra-query (média)"*, com a distribuição
`4 queries 0% · 9 em 20% · 1 em 40%`, n=14. A média dessa distribuição é
exatamente 15,7%, e a distribuição **é** intra-query em k=5.

Mas o T6, **no mesmo corpus de 14 queries**, reporta intra-query como
`dup_rate = 12,4%` — e reporta 15,4% para outra coisa (entre queries).

**Não consigo reconciliar os dois a partir do que está nos repositórios.** Pode
haver uma rodada com k diferente que eu não vi. O ponto é outro: a página afirma
*"todo número tem fonte — arquivo, data e linha por trás de cada métrica"*, e
esse é justamente o número cuja fonte eu não localizo.

Vale checar antes que um cliente técnico peça.

E o 15,7% aparece sem intervalo. Com n=14, ele é **[10,0% ; 21,4%]** — 11,4
pontos de largura. Fonte e intervalo são coisas distintas, e a página promete a
primeira enquanto omite a segunda.

## A regra que evita isto

Herdada do `NORTE §4.14`, que exige referente nomeado para número de acordo. Aqui
vale o mesmo para número de duplicação:

> **Todo número de duplicação sai com: o que conta, sobre qual conjunto, em qual
> store, com qual N, e com intervalo.**

`24,8%` sozinho não é informação. `24,8% dos slots entregues, IC [20,5; 29,7],
N=50 turnos do store vivo` é.
