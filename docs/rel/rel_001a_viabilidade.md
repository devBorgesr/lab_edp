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

---

## Verificação operacional — o retriever entrega o pool congelado?

**30/08/2026.** A checagem anterior contou documentos no índice; esta roda o
**retriever real** contra as queries reais, num clone do store.

```
queries testadas ........................ 50
tamanho do ranking: mín 50 | mediana 50 | máx 50
queries com >= 50 candidatos ............ 50/50
```

**Viável.** O `§3.2` exige ranking de 50 posições para o estrato `cauda`
(20–50), e todas as 50 queries entregam.

Com isto **encerra-se a fase de viabilidade.** Nenhuma outra checagem prévia
está planejada — o próximo passo é coleta, não desenho.

## Errata do controle negativo — validar o rótulo em vez de contornar

A limitação declarada acima (o domínio vem de `cognitive_decisions`, extraído
por LLM, e nunca foi validado) foi apontada em auditoria externa como cadeia
frágil:

```
LLM → rótulo de domínio → "outro domínio" → controle → REL-001
```

Correto pelo `§4.14`: *"o LLM disse que são domínios diferentes"* não é verdade.

### Por que NÃO trocar por corpus externo

A saída sugerida — controle vindo de coleção explicitamente separada — tem um
furo próprio: documento de outra coleção provavelmente tem **formato diferente**
(docstring, artigo, página). Os dois julgadores concordariam que é irrelevante
por reconhecerem o **formato**, não por aplicarem o rubric.

O controle ficaria fácil **pelo motivo errado** — e um controle que passa sem
exercitar o rubric não verifica nada. É pior que a dependência que ele resolve.

Fundo do ranking também não serve: depende do retriever que está sendo auditado.

### O que fica congelado

**Os 77 rótulos de domínio são verificados manualmente, uma vez, antes da
coleta, e congelados.** O pesquisador confere cada um; a lista corrigida vira
artefato versionado.

Três propriedades que isso preserva e a troca de corpus não preservava:

1. **Formato idêntico** ao dos estratos `topo` e `cauda` — o julgador não
   distingue o controle por aparência.
2. **A dependência do LLM some do caminho crítico** — o rótulo que entra no
   experimento é humano, não do extrator.
3. **Produz um número:** quantos dos 77 o LLM errou. Isso é `§4.14` aplicado —
   a concordância vira medida em vez de suposição.

`N_DOMINIOS_VERIFICADOS = 77` entra como pré-condição de armamento: sem a lista
verificada e congelada, o REL-001 não dispara.

### Limitação que permanece

Quem verifica é o **mesmo** que rotula relevância no caminho A. Para um controle
com predição de ~100% de acordo o risco de viés sutil é baixo, mas não é zero, e
fica escrito aqui em vez de omitido.

---

## Resultado da pré-condição — v1 e v2, e o que o número mede

**30/08/2026.** Os 77 rótulos foram revisados. Duas rodadas, e a diferença entre
elas é o achado.

| | discordâncias | `taxa_erro_llm` |
|---|---|---|
| **v1** — revisão sem critério explícito | **0** de 77 | 0,000 |
| **v2** — revisão com o critério do `§`abaixo | **13** de 77 | **0,169** |

### O critério que mudou tudo

Entre as duas rodadas foi formulada uma pergunta única, aplicável item a item:

> **Este documento poderia ser a resposta certa para alguma pergunta futura?**

Os 13 que falham: **11 saudações** (`oi`, `bom dia`), **2 instantes datados**
(*"que dia é hoje"* → 31 de maio; → 2 de junho). Todos marcados `SEM_TEMA`.

Os dois comandos `/modo` **não** foram marcados: a resposta descreve princípios
com conteúdo próprio, e o revisor os manteve. Fronteira decidida, não ignorada.

### O que os 16,9% NÃO significam

**Não é "o extrator errou 17% dos rótulos".** Ele não errou sobre o que o texto
dizia: `conversação geral` descreve corretamente uma saudação, e
`datetime handling` descreve corretamente uma resposta com data.

O erro é de **categoria**: tratar *ausência de assunto* como se fosse um
assunto. Para descrever um documento, `conversação geral` está certo. Para
servir de eixo do controle negativo, não existe.

**E o número mede o critério tanto quanto o extrator.** A v1 deu zero porque o
revisor não tinha pergunta para aplicar — os mesmos 77 documentos, o mesmo
revisor, os mesmos rótulos. Só a régua mudou.

É o `NORTE §4.14` aplicado à própria pré-condição: a concordância de v1
(0 discordâncias) não media a qualidade do extrator. Media a ausência de
critério.

### Estado do pool

```
77 documentos verificados
  13 SEM_TEMA (fora do controle)
  64 com domínio real, em 47 domínios canônicos
pool para uma query típica: 58 documentos  →  folga de 29× sobre os 2 exigidos
```

`dominio_congelado.json` (v1) **não foi reescrito** — o v2 é sucessor, e os dois
ficam. Quem auditar vê a diferença que o critério fez.

### Limitação que permanece

O revisor é o mesmo que rotulará relevância no caminho A, e foi ele quem
formulou — junto com o agente — o critério que produziu os 13. Um segundo
revisor com outro critério produziria outro número. Isso não invalida o
artefato; delimita o que ele sustenta.
