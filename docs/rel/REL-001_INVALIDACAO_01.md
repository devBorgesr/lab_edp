# REL-001 — Invalidação 01

**31/08/2026.** A coleta autorizada rodou e **está inválida**. Dois defeitos
independentes, os dois meus, encontrados ao investigar por que o caminho B
parou em 492 de 500.

Nada é apagado. Os artefatos inválidos ficam, marcados.

---

## Defeito 1 — o estrato `topo` nunca foi o top-5 de nada

`congela_pares.py`, primeira versão, montava o ranking assim:

```python
ranking = [i for i in txt if i != q["id_turno"]]
```

Isso é **todos os documentos em ordem de inserção do arquivo**, não a saída do
retriever. Consequência: o estrato `topo` eram os **cinco primeiros documentos
do `episodic.json`, iguais para as 50 queries** — e são justamente as saudações
e o timestamp que marcamos `SEM_TEMA` na pré-condição.

Os 492 julgamentos do caminho B avaliaram, como "top-5 do retriever", o mesmo
`"oi / Oi! Tudo bem?"` contra 50 queries diferentes.

**O retriever já tinha sido rodado de verdade** na viabilidade (`28cc991`,
*"50/50 queries devolvem 50 candidatos"*). O erro não foi não saber como. Foi
não ligar — e o smoke conferir formato sem nunca perguntar se o topo era o topo.

## Defeito 2 — o corpus não sustenta o `§3.2`, e a viabilidade errou

Com o retriever real ligado:

| | |
|---|---|
| ranking bruto | 48–49 slots |
| após dedup por id | **29–40 distintos**, mediana 36 |
| queries com ≥50 distintos | **0 de 50** |

O `§3.2` tira a `cauda` das posições 20–50 e exige 50 documentos **distintos**.
O retriever entrega no máximo 40.

A causa é o achado de `a434cdf`: os 61 ids de `semantic` também estão em
`episodic`, e o índice conta cada um duas vezes. Um top-50 de 198 entradas
colapsa para ~36 documentos reais.

**E o REL-001A declarou VIÁVEL.** Naquela checagem eu contei *slots* devolvidos
— 50/50 — e não *documentos distintos*. A lista de verificação do auditor
incluía "IDs únicos?"; eu conferi isso **depois**, encontrei os 637 duplicados,
e **não voltei para revisar o veredito de viabilidade**.

O achado estava escrito e o veredito não foi corrigido.

## O que foi invalidado

| artefato | estado |
|---|---|
| `pares_congelados.json` (07:22) | **INVÁLIDO** — topo é ordem de arquivo |
| `rotulos_llm.json` (492 rótulos) | **INVÁLIDO** — julgou os pares acima |
| `amostra_congelada.json` | válido — as 50 queries não dependem do ranking |
| `dominio_congelado_v2.json` | válido |
| `REL-001_CONFIG_CONGELADA.json` | válido — nada nele depende do pool |
| smoke (`790374a`) | válido como teste de infraestrutura; não media semântica |

O caminho A **não havia começado**. Nenhum julgamento humano foi perdido — é a
única boa notícia aqui, e é sorte de ordenação, não de desenho.

## O que isto NÃO é

Não é resultado do experimento. Nenhum κ foi calculado, nenhuma discordância foi
olhada, e a invalidação foi encontrada por **contagem** (492 ≠ 500), não por
inspeção de rótulo.

## O que fica bloqueado, e a decisão não é minha

O `§3.2` está congelado e **este corpus não o satisfaz**. As saídas visíveis
mudam coisas diferentes, e nenhuma é escolha de agente:

**Redesenhar a `cauda`** — tirar de 20–35 em vez de 20–50, ou reduzir
`N_DOCS_POR_QUERY`. Muda a régua, logo é o **REL-002**, com poder recalculado.

**Consertar o índice em produção** — deduplicar `_hybrid_index` por id devolveria
~50 distintos. Mas é `FORMAT_STATE_FLAGS`: muda o conjunto recuperado em todo
turno, exige flag, pré-registro e medição antes/depois. É outro experimento, e
mudaria o objeto sob o REL-001.

**Ligar `EDP_RETRIEVE_DEDUP` só para a coleta** — mesmo problema: o instrumento
passaria a medir um retriever diferente do de produção, e isso precisa ser
declarado como condição, não adotado por conveniência.

**Crescer o corpus** — 137 documentos distintos é pouco para um top-50. Não há
prazo para isso.

## O que eu deveria ter feito, e não fiz

O REL-001A existia exatamente para pegar isto. Ele tinha a informação — o
`a434cdf` mediu 637 ids duplicados **três dias** antes — e o veredito de
viabilidade não foi revisto à luz do achado.

A lição não é "verificar mais". É que **achado novo obriga releitura dos
vereditos anteriores que dependiam do que ele contradiz**, e nada no método
força isso hoje.
