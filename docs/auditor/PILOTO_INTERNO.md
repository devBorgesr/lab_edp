# Piloto interno — validação técnica antes de recrutar gente

**01/09/2026.** Isto **não é** o piloto externo. Nenhum usuário real
participou, e nada aqui responde às perguntas comerciais.

`PILOTO_EXTERNO = NÃO EXECUTADO`

## O que ele testa

Se o fluxo funciona ponta a ponta contra sistemas que **não são o nosso**, com
adaptadores que passam pelo contrato público, e se o serviço bloqueia quando
deve.

## Os sistemas

Três clientes simulados em `fixtures/customer_*`, como **dados em disco**
(`corpus.json`, `queries.json`, `config.json`) — não como classes do próprio
pacote. Uma fixture que é código interno testa o serviço contra si mesmo.

O EDP **não** foi usado: ele é o nosso sistema, e usá-lo como cliente externo
seria medir a integração contra a única integração que já existia.

| | corpus | perguntas | característica |
|---|---|---|---|
| `customer_a` | 220 | 40 | normal, score de similaridade |
| `customer_b` | 220 | 40 | **duplicação injetada de 0,55** |
| `customer_c` | 220 | 40 | **distância crua**, sem conversão |

## O fluxo, medido

| cliente | opção | `check` | `run` | status | medições | arquivos |
|---|---|---|---|---|---|---|
| `customer_a` | — | 1,93 s | 1,81 s | `COMPLETE` | 5 | 6 (19 KB) |
| `customer_b` | — | 1,68 s | 1,79 s | `COMPLETE` | 5 | 6 (19 KB) |
| `customer_c` | — | 0,17 s | 0,19 s | **`BLOCKED`** | **0** | 6 (13 KB) |
| `customer_c` | `converter_score` | 1,74 s | 1,80 s | `COMPLETE` | 5 | 6 (19 KB) |

Zero chamadas a modelo em todos. Custo em dólar: `null`, com o motivo — não há
tabela de preço registrada, e zero seria mentira.

**O caso bloqueado é 10× mais rápido**, e isso é a propriedade funcionando: ele
para na primeira etapa de ranking, antes de qualquer trabalho.

## O instrumento recupera o defeito injetado

Este é o resultado que mais importa:

| | `customer_a` | `customer_b` | injetado em B |
|---|---|---|---|
| documentos distintos por query | **50** | **22** | — |
| duplicação intra-query por id | **0,00** | **0,56** | **0,55** |

O `customer_b` foi construído com 0,55 de duplicação por um gerador que não
conhece o código de medição, e a medição devolveu **0,56**. O instrumento
detecta o defeito que afirma detectar.

É o mais perto de validação de instrumento que dá para chegar sem dado externo
— e **não substitui** dado externo: o gerador e o medidor foram escritos pela
mesma pessoa, o que é exatamente o viés que um piloto real elimina.

## O caso `customer_c` — a incompatibilidade C1, ponta a ponta

Distância crua (`0.0, 0.37, 0.74, …`) viola duas regras do contrato: cresce, e
começa em zero. Resultado: `BLOCKED` em `ranking.veio_do_retriever`, **zero
medições**, e o cliente não recebe número nenhum.

Com `converter_score` (`1/(1+d)`, monótona, declarada no manifesto): `COMPLETE`,
5 medições.

O serviço nunca aplica a conversão sozinho. Fazer isso seria adivinhar a
semântica do score do cliente.

## O que este piloto NÃO mediu

```
satisfação .................. NAO_MEDIDO
utilidade percebida ......... NAO_MEDIDO
disposição de pagar ......... NAO_MEDIDO
intenção de renovação ....... NAO_MEDIDO
tempo humano de integração .. NAO_MEDIDO
dificuldade percebida ....... NAO_MEDIDO
```

Todos exigem um usuário real. Continuam `NAO_MEDIDO` até alguém responder.

E há um limite que nenhum piloto interno resolve: **eu escrevi os três clientes
e escrevi o medidor.** Um sistema que eu construo tende a satisfazer o contrato
que eu escrevi. O primeiro usuário externo existe justamente para quebrar essa
circularidade.
