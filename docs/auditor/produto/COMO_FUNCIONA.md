# Diagnóstico de Retrieval

**Medição técnica reproduzível do que seu sistema está recuperando — com
evidências, hashes e limites explícitos.**

Não usamos a palavra *auditoria* aqui. Auditoria promete qualidade,
conformidade e certificação; o que entregamos hoje é diagnóstico, e a palavra
deve caber no que a medição sustenta.

## O fluxo

```
1. você fornece acesso ao retrieval
2. validamos a integração          (check — milissegundos)
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

Responde `READY` ou `BLOCKED` em **milissegundos**. Ele valida o schema e os
limites, confere o snapshot e pede **uma** consulta ao seu retriever para
verificar a procedência do ranking.

Não copia o seu corpus, não calcula medição, não grava relatório e não chama
julgador. O que ele **não** decide — cardinalidade em todas as perguntas,
estratos, pré-condições estatísticas — está dito na resposta, em vez de deixar
você supor que foi verificado.

*Errata 01/09: até esta data o `check` rodava o pipeline inteiro (medido: 1,81 s
contra 1,74 s do `run`) enquanto esta página prometia "sem processar nada".
Agora são 0,009 s.*

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
