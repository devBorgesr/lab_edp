# Matriz de claims — o que o serviço pode afirmar

**Normativo.** Divergência entre este documento e o que sai no relatório é
defeito do relatório, e há teste que reprova.

## Três níveis

```
NÍVEL 1  OBSERVAÇÃO    o que o retriever devolveu
NÍVEL 2  DIAGNÓSTICO   anomalia medida no material recuperado
NÍVEL 3  QUALIDADE     efeito sobre relevância ou resposta
```

O `DIAGNOSTICO v1` emite **NÍVEL 1**. Nunca NÍVEL 3.

### E NÍVEL 2 também não — isto não era o plano

Chamar 26% de duplicação de **anomalia** exige saber o que é normal. Não
sabemos: há **um** sistema real medido (o EDP) e três sintéticos que eu mesmo
escrevi. Sem distribuição de referência, "anômalo" é opinião com aparência de
medida.

NÍVEL 2 fica disponível quando houver linha de base, e não antes. O relatório
diz isso explicitamente ao cliente.

## A matriz

| claim | permitido | por quê |
|---|---|---|
| "37 documentos distintos por query (N=50)" | ✅ | observação, com referente |
| "26% dos slots foram ocupados por id repetido" | ✅ | observação, com referente |
| "Jaccard mediano 0,283 entre pares de queries (N=1.225)" | ✅ | observação, com referente |
| "26% de duplicação" sem N, sem k | ❌ | número sem referente é alegação |
| "há **alta** sobreposição entre queries" | ❌ | "alta" exige linha de base |
| "26% do contexto é desperdiçado" | ❌ | consequência não medida |
| "um quarto da janela **vai em** repetido" | ❌ | idem — afirma consumo |
| "a duplicação reduz a qualidade da resposta" | ❌ | NÍVEL 3, não medido |
| "Recall@K = X" | ❌ | fora do escopo do `DIAGNOSTICO v1` |
| "RAG certificado / aprovado / com selo" | ❌ | o serviço não certifica |
| "não certifica nada" | ✅ | negação de claim não é claim |

## Vocabulário

**Permitido:** repetido, duplicado, sobreposto, observado, associado, medido.

**Bloqueado como consequência causal:** desperdiçado, inútil, jogado fora,
custo causado, perda de qualidade, queda de precisão, prejudica, degrada.

Nada impede dizer que documentos se repetem. O que se bloqueia é dizer o que a
repetição **causa** — porque isso exigiria um experimento comparativo, o mesmo
sistema com e sem a repetição, com desfecho definido antes. Ele não foi feito.

## Por que isto é código, e não convenção

Eu já tinha escrito a regra em `docs/sujeito_edp/NUMEROS_DE_DUPLICACAO.md`:

> Nenhum é "X% do contexto do RAG é inútil". Todos medem repetição de slot. Que
> a repetição desperdice contexto é inferência plausível e **não medida**.

E a violei mesmo assim — **duas vezes**, no gerador de relatório
(`relatorio.py`, escopo diagnóstico) e no documento do MVP. Passou por revisão e
por 283 testes.

Saber a regra não impediu de quebrá-la. Por isso ela virou verificação sobre o
**texto gerado** — a grandeza certa é o que o cliente lê, não o que o código
comenta (`NORTE §4.15`). A barreira roda no mesmo ponto da redação de segredo,
e pelo mesmo motivo: é o último lugar antes de o texto virar entregável.

## Ressalvas obrigatórias

Um relatório de diagnóstico **não sai** sem dizer que não mediu: qualidade das
respostas, Recall@K, relevância (nenhum julgamento foi feito), conformidade.

Ausência de ressalva é tratada como violação, no mesmo nível de um termo
proibido: o leitor completa a lacuna sozinho, e completa para o lado otimista.

## Citação não é afirmação

O verificador ignora blocos de errata e de ressalva, e reconhece negação
inline. *"Não certifica nada"* contém "certifica" e afirma o oposto.

A primeira versão filtrava linha a linha e reprovou o próprio relatório — a
ressalva *"conformidade, certificação ou aprovação"* é item de lista sob um
cabeçalho de negação, e o item sozinho não carrega a negação. Um linter que
obriga a apagar a ressalva para passar está invertido: piora exatamente o texto
que deveria proteger.
