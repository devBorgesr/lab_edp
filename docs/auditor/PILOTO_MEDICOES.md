# Piloto — folha de medição

**Vazia de propósito.** Preencher **durante** o piloto, com fato observado.
Reconstruir de memória depois é a forma mais fácil de ouvir o que se queria
ouvir.

`PILOTO_EXTERNO = NÃO EXECUTADO` — e o EDP **não** substitui cliente externo.

## Integração — só fato objetivo

| campo | piloto 1 | piloto 2 | piloto 3 |
|---|---|---|---|
| data | | | |
| stack de retrieval | | | |
| retriever expõe score? | | | |
| tipo de score (similaridade / distância / nenhum) | | | |
| precisou converter? qual conversão? | | | |
| ids estáveis? | | | |
| snapshot reproduzível? | | | |
| **tempo até o primeiro `check`** | | | |
| **linhas do adaptador** | | | |
| quem escreveu o adaptador | | | |
| erros encontrados | | | |
| intervenções nossas | | | |
| tempo de execução | | | |
| tempo até o primeiro relatório | | | |
| status final | | | |

**Não preencher "satisfação" nem "valor percebido" aqui.** Isso vem da
entrevista, e só depois de perguntado.

## Folha de decisão comercial — respostas coletadas, nunca inferidas

| | piloto 1 | piloto 2 | piloto 3 |
|---|---|---|---|
| A — conseguiu rodar? | | | |
| B — recebeu relatório? | | | |
| C — entendeu o relatório? | | | |
| **C2 — `BLOCKED` soou como "falhou" ou como "me disse algo"?** | | | |
| D — encontrou achado útil? | | | |
| E — faria de novo? | | | |
| F — pagaria? Quanto? | | | |
| G — pagaria de novo em um mês? | | | |

**C2 é a que decide a tese.** F e G só valem depois dela: quem não entendeu o
que recebeu não sabe dizer se pagaria.

## Unidade econômica — por execução

| | medido pelo serviço | piloto 1 | piloto 2 |
|---|---|---|---|
| tempo total (s) | ✅ automático | | |
| tempo por etapa | ✅ automático | | |
| chamadas ao modelo | ✅ automático | | |
| tokens | ✅ automático | | |
| armazenamento | ❌ | | |
| **tempo humano de preparação** | ❌ | | |
| **tempo humano de análise** | ❌ | | |
| **tempo humano do cliente (adaptador)** | ❌ | | |

Os três últimos são o provável dominante e **nenhum é medido automaticamente**.

Referência do que o serviço já mede sozinho, no EDP: **18,1 s, zero chamadas ao
modelo** — mas é uma auditoria que bloqueou cedo. Não serve de base para
projetar custo de auditoria completa.

## Separação obrigatória

```
custo direto por auditoria   =  computação + modelo + armazenamento
custo humano por auditoria   =  preparação + análise + suporte
custo de onboarding          =  adaptador do cliente   (NÃO diluir no operacional)
```

O adaptador é **custo de onboarding**, pago uma vez por cliente. Diluí-lo no
custo operacional faria a margem parecer melhor do que é no primeiro cliente e
pior do que é no décimo.

## Preço

**Fora do código.** O serviço produz custo técnico; preço é decisão comercial,
e `auditor/custos.py:PRECO_POR_MTOK` está vazio de propósito. Ao preencher,
registrar `modelo · preço entrada · preço saída · fonte · data`.
