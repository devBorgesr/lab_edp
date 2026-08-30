# REL-001A — Viabilidade do corpus para o protocolo congelado

**30/08/2026.** Checagem de viabilidade, rodada **antes** de armar o REL-001 e
**sem alterar nenhuma constante congelada**.

Pergunta única:

> O corpus disponível satisfaz o desenho do REL-001 sem mexer no `§8`?

Existe por causa do exp019: lá o pré-registro foi congelado, o harness escrito,
os testes passaram — e só então se descobriu que o estrato `alvo` tinha 6 dos 40
pares exigidos. A ordem certa é **pré-registro → viabilidade → armar**.

---

## Corpus medido

`edp_data/sessions/default_cognitive`, snapshot de 18/08 12:14.

| requisito do protocolo | exigido | disponível | veredito |
|---|---|---|---|
| documentos para ranking de 50 posições | 50 | **198** | OK |
| sobrevivem à governança de índice | 50 | **198** | OK |
| queries únicas | `N_QUERIES = 50` | **75** | OK |
| queries com domínio marcado | 50 | **66** | OK |
| docs fora do domínio da query (controle) | `N_CONTROLE = 2` | mín. **69** | OK |

**66 de 66 queries** com domínio conseguem fornecer os 2 documentos de outro
domínio. Zero descartados por falta de embedding.

**Veredito: o corpus sustenta o protocolo. Nenhuma constante precisa mudar.**

## Um erro meu, no meio da própria checagem

A primeira rodada imprimiu:

> *"os domínios são todos sub-tópicos da MESMA conversa (o próprio EDP)"*

**Isso era uma conclusão escrita dentro do `print`, não uma medição.** Ao medir,
os 51 domínios marcados incluem `postgresql indexing`, `física acústica`,
`cálculo de datas`, `java resilience patterns` — genuinamente distintos.

O erro teria **bloqueado o REL-001 por um obstáculo inexistente**, e num relatório
apressado viraria *"o corpus não tem segundo domínio"*.

É o mesmo padrão que este projeto já registrou quatro vezes: **afirmação escrita
antes da verificação, no lugar onde ela parece resultado.** Aqui saiu barato
porque a rodada seguinte mediu.

## Limitações declaradas

**O domínio vem do `cognitive_decisions`, extraído por LLM.** Só 77 dos 198
documentos têm domínio marcado — os outros 121 não podem servir de controle,
porque não se sabe a que domínio pertencem. O pool de controle é de 77, o que
sobra com folga para 2 por query, mas o rótulo de domínio **não foi validado** e
herda a confiabilidade do extrator.

Isso é o `§4.14` aplicado a este documento: o controle negativo depende de um
rótulo produzido por modelo, e ninguém mediu a concordância dele com nada.

**O snapshot é de 18/08.** O store vivo cresceu desde então; a amostra final deve
declarar a data do corpus usado.

**Ranking de 50 é possível, não verificado.** O índice tem 198 entradas, então
`search(top_k=50)` pode devolver 50 — mas isso não foi executado contra o
retriever real. O harness estoura se vier menos, o que é o comportamento certo,
mas a primeira rodada real pode encontrar queries com ranking curto.

## O que isto NÃO autoriza

Não autoriza dizer que o REL-001 vai dar certo. Autoriza dizer que ele **pode
ser executado** sem afrouxar o protocolo — que é uma pergunta diferente, e a
única que esta checagem faz.
