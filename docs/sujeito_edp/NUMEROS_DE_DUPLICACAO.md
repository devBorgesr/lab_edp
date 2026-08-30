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

## RECONCILIADO — 30/08, a origem do 15,7% foi localizada

**Resultado: (A) reproduzido.** A fonte é `edp_v5/RELATORIO_DOGFOOD.md`:

```
Export analisado: 14 queries válidas, k considerado: 5
dup_rate@k por hash (média) ..... 15.7%
dup_rate@k por ID   (média) ..... 15.7%
pior query ...................... 40.0%
export: export_fase0.jsonl (67 KB, 22/07)
```

O rótulo da landing está **correto**: é duplicação intra-query.

**E reconcilia com o T6 pelo `k`.** O dogfood mede em `k = 5` fixo; o T6 mede
sobre o `retrieval_kept`, de tamanho variável. Dois valores corretos da mesma
família, em cortes diferentes — 15,7% em k=5 e 12,4% no kept.

O `15,4%` do T6 ficou perto por coincidência e **não** é comparável: é
sobreposição entre queries. O cross-query real do dogfood é **4,6%** (contínua)
e **0,0%** (binária), contra referência aleatória de 7,0%.

### Dois problemas que a reconciliação revelou

**A fonte não está versionada.** `RELATORIO_DOGFOOD.md`, `comercial/FUNIL.md` e
`comercial/PUBLICO_ALVO.md` estão **untracked**. A página promete *"arquivo,
data e linha por trás de cada métrica"*, e o arquivo não está no repositório —
some se a máquina sumir, e ninguém consegue auditar a partir do que foi
publicado.

**Três `15,7%` distintos convivem no projeto, medindo coisas diferentes:**

| onde | mede |
|---|---|
| `RELATORIO_DOGFOOD.md` | `dup_rate@k=5`, média de 14 queries — **intra-query** |
| `EXP017_FASE0.md:164` | censo de duplicatas na camada **semântica** (8 de 51) |
| `PRE_REGISTRO_EXP017.md:190` | o mesmo censo, citado no veredito da H3 |

Coincidência de valor, não de fenômeno. Um relatório que cite "15,7%" sem
referente pode estar falando de qualquer um dos três.

## O que faltava, e agora está fechado

O 15,7% aparece sem intervalo. Com n=14, ele é **[10,0% ; 21,4%]** — 11,4
pontos de largura. Fonte e intervalo são coisas distintas, e a página promete a
primeira enquanto omite a segunda.

## A regra que evita isto

Herdada do `NORTE §4.14`, que exige referente nomeado para número de acordo. Aqui
vale o mesmo para número de duplicação:

> **Todo número de duplicação sai com: o que conta, sobre qual conjunto, em qual
> store, com qual N, e com intervalo.**

`24,8%` sozinho não é informação. `24,8% dos slots entregues, IC [20,5; 29,7],
N=50 turnos do store vivo` é.
