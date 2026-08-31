# Relatório consolidado — fase de evidência

**31/08/2026.** Entrega parcial, e o que falta é a parte que decide.

---

## O que NÃO fiz, e não posso fazer

**O piloto externo não foi executado.** Ele exige recrutar organizações,
receber sistemas reais e entrevistar pessoas. Não tenho como fazer nenhuma das
três coisas.

Isso deixa **em branco** os itens que dependem de gente:

| critério | estado |
|---|---|
| 1. relatório do piloto externo | **não executado** |
| 2. evidência sobre compreensão de `BLOCKED` | **não coletada** |
| 5. custo humano por auditoria | **não medido** |

A pergunta nº 6 do protocolo — *"`BLOCKED` soou como 'o serviço falhou' ou como
'o serviço me disse algo'?"* — continua sem resposta, e ela é a que decide a
tese. Nada abaixo substitui isso.

Não vou estimar essas respostas. Um projeto construído sobre não fabricar dado
não começa a fabricar na hora em que o dado é inconveniente.

---

## O que fiz: medi o risco dos adaptadores contra sistemas reais

O item 2 **não depende de cliente**. Escrevi adaptadores de verdade e rodei o
serviço contra eles.

### Inventário de stacks disponíveis nesta máquina

```
faiss 1.14.3 · sentence-transformers · scikit-learn · numpy · redis
```

LangChain, LlamaIndex, Chroma, Qdrant, Weaviate, Elasticsearch e Haystack
**não estão instalados**, e **não afirmo o que eles expõem** — seria memória, não
verificação (`NORTE §4.1`). O inventário abaixo cobre o que rodei.

### O que cada sistema entrega, medido

| | id estável | lista ordenada | score | direção | snapshot |
|---|---|---|---|---|---|
| **FAISS `IndexFlatIP`** | **não** — posições internas | sim | sim | decrescente ✅ | do cliente |
| **FAISS `IndexFlatL2`** | **não** | sim | **distância** | **crescente ❌** | do cliente |
| **cosseno numpy** | sim | sim | sim | decrescente, mas **pode ser ≤ 0** | do cliente |
| **EDP** | sim | sim | RRF | decrescente ✅ | próprio |

Medido em `faiss 1.14.3`:

```
IndexFlatIP   [1.803, 1.657, 1.514]   não-crescente: sim   todos>0: sim
IndexFlatL2   [0.000, 0.525, 0.638]   não-crescente: NÃO   todos>0: NÃO
```

### Custo de adaptação

| adaptador | linhas de código |
|---|---|
| FAISS | **47** |
| cosseno | **33** |

Baixo — mas essas linhas foram escritas por quem **conhece o contrato**. O custo
que importa é o de alguém que não conhece, e esse continua não medido.

---

## Duas classes de incompatibilidade, medidas

### C1 — score que não é score

Um adaptador FAISS L2 ingênuo (repassa a distância) produz:

```
status BLOCKED · barreira ranking.veio_do_retriever
"score nao-positivo (min=0.0)"
medições entregues: 0
```

**O cliente não recebe nada.** Não é falso positivo: distância não é score no
sentido do contrato. Mas a conversão distância→similaridade é trivial
(`1/(1+d)`, monótona, preserva a ordem) e **um cliente que não souber disso
recebe um relatório vazio sem entender por quê**.

Frequência: 1 de 4 sistemas testados, e é a métrica **default** de boa parte
dos índices vetoriais.

### C2 — o controle negativo pode ser estruturalmente impossível

Este é o achado maior, e eu não o esperava.

O contrato pede `controle_para(query)` — documentos de outro domínio, fora do
ranking. Isso exige que **existam documentos que o retriever nunca alcança**.
Medido:

| corpus | queries | top_k | alcançados | nunca alcançados | viável |
|---|---|---|---|---|---|
| 140 | 60 | 10 | 123 | 17 | não |
| 140 | 60 | 50 | **140** | **0** | **não** |
| 400 | 60 | 50 | 391 | 9 | não |
| 1.000 | 50 | 50 | 801 | 199 | sim |
| 5.000 | 50 | 50 | 1.706 | 3.294 | sim |

Com corpus pequeno o retriever **alcança tudo**, e não sobra candidato legítimo
a controle. Taxa de colisão medida: **73% a `top_k=10`, 100% a `top_k=25` e
`top_k=50`** — os três sistemas bem adaptados bloquearam nisso, não no ranking.

**Consequência para o REL-001, que muda a matriz de decisão.** Medido no EDP
real: 133 documentos distintos no índice, **125 alcançados** pelas 50 queries,
**8 nunca alcançados** — para 100 slots de controle.

Ou seja: **consertar a duplicação do `_hybrid_index` não desbloquearia o
REL-001.** A cardinalidade passaria, e o controle falharia em seguida. Eu não
sabia disso quando escrevi a matriz, porque a cardinalidade bloqueia antes e
esconde o segundo problema.

---

## Classificação dos problemas (item 6)

| # | problema | classe | ação |
|---|---|---|---|
| 1 | L2 devolve distância crescente | **D** — limitação do sistema auditado | documentar no contrato; **não** inferir conversão |
| 2 | FAISS não devolve id do cliente | **D** | é trabalho do adaptador, e precisa estar dito |
| 3 | controle impossível em corpus pequeno | **C** — problema de contrato | **decisão do pesquisador** |
| 4 | cliente com L2 recebe relatório vazio | **B** — UX | mensagem deveria sugerir a conversão |
| 5 | custo de adaptação para quem não conhece o contrato | **F** — sem evidência | exige piloto |
| 6 | compreensão de `BLOCKED` | **F** | exige piloto |

**Nenhum bug (classe A) encontrado.** Os 276 testes seguem passando, e os três
adaptadores corretos produziram manifesto, medições e relatório sem defeito.

**Não implementei nada das classes B, C, E.** O item 5 é explícito: não relaxar
contrato, não inventar score, não inferir dado ausente. O problema #4 é
tentador — uma linha de mensagem — mas é UX baseada em um caso, e a instrução
diz para medir a frequência primeiro.

---

## O que pode ser decidido com evidência

1. **Distância vetorial precisa de conversão declarada.** Medido, não suposto.
   Cabe ao contrato dizer isso, não ao serviço adivinhar.
2. **`controle_para` é o método mais difícil do contrato**, e o único que pode
   ser impossível por tamanho de corpus. Os outros três dependem só da API do
   retriever.
3. **Consertar o `_hybrid_index` não desbloqueia o REL-001.** A opção C da
   matriz perde força — e isso é medição, não opinião.

## O que ainda não pode ser decidido

1. Se `BLOCKED` é entendido como diagnóstico ou como falha.
2. Se o custo de adaptação é aceitável para quem não escreveu o contrato.
3. Qual fração dos RAGs reais expõe score — 1 de 4 aqui não é amostra.
4. `DECISAO_RANKING.md` continua em branco, e agora com um dado a mais **contra**
   a opção C.

## Backlog priorizado

```
1  medir frequencia de "sem score" em stacks reais    exige instalar/pilotar
2  mensagem de erro que sugere a conversao (B)        depende de 1
3  decidir o destino de controle_para (C)             decisao do pesquisador
4  custo de adaptacao por terceiro (F)                exige piloto
5  custo humano por auditoria (F)                     exige piloto
```

---

## O que eu recomendaria como próximo passo

O gargalo é o piloto, e ele precisa de você. O menor experimento que produz a
evidência mais cara:

**Uma pessoa, um sistema, uma hora.** Alguém que não conheça esta arquitetura,
com qualquer RAG que já tenha, escrevendo o próprio adaptador com o
`SERVICE_CONTRACT.md` na mão. Cronometrar. Depois fazer a pergunta nº 6.

Se essa pessoa levar quatro horas para escrever 40 linhas, o custo de onboarding
é o produto — e a economia do negócio muda inteira. Se levar vinte minutos e
disser *"entendi, ele me disse que não dá para medir e por quê"*, a tese está de
pé e o resto é distribuição.
