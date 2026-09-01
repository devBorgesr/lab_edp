# Diagnóstico de Retrieval

**Medição técnica reproduzível do que seu sistema está recuperando — com
evidências, hashes e limites explícitos.**

Não usamos a palavra *auditoria* aqui. Auditoria promete qualidade,
conformidade e certificação; o que entregamos hoje é diagnóstico, e a palavra
deve caber no que a medição sustenta.

## O fluxo

```
1. você fornece acesso ao retrieval
2. validamos a integração          (check — segundos, sem processar)
3. rodamos o diagnóstico
4. entregamos relatório + manifesto
```

### 1. Acesso ao retrieval

Quatro métodos. O seu retriever precisa devolver `[(doc_id, score), ...]` na
ordem em que ele rankeou.

**O score não é opcional** — é a prova de que o ranking veio de um retriever e
não de uma lista qualquer de ids. Se o seu índice devolve *distância* (comum em
FAISS L2), a conversão é trivial e monótona, e nós a declaramos no manifesto.

Se o seu retriever não expõe score nenhum, **não conseguimos diagnosticar como
está** — e dizemos isso em vez de inventar um número.

### 2. Validação da integração

```bash
auditor check ...
```

Responde `READY` ou `BLOCKED` em segundos, sem processar nada. Serve para você
descobrir um problema antes do trabalho, não depois.

### 3. Diagnóstico

```bash
auditor run ...
```

Medido em corpus de 220 documentos e 40 perguntas: **segundos**, zero chamadas
a modelo de linguagem.

### 4. Entrega

Relatório executivo de uma página, relatório técnico com a evidência,
manifesto com `sha256` de tudo, e o registro de cada verificação.

## `COMPLETE` e `BLOCKED`

**`COMPLETE`** — a régua executou; você recebe as medições.

**`BLOCKED`** — *aquela régua* não pôde ser executada sobre *aquele sistema*.
Não é erro nosso e não diz que seu sistema é ruim ou inauditável: outra régua
pode se aplicar a ele. O relatório diz exatamente qual pré-condição falhou.

**Você ainda recebe as medições descritivas sob `BLOCKED`**, desde que o
ranking tenha procedência provada.

O único caso em que não há medição nenhuma é ranking sem procedência — porque
medir sobre ranking não verificado não mede nada.
