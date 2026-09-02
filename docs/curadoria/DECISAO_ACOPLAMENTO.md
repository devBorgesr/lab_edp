# Decisão pendente — o que acoplar do ecossistema EDP ao MVP

**01/09/2026. Nenhuma opção foi escolhida.** Este documento segue a forma de
`docs/auditor/DECISAO_RANKING.md`: a curadoria apresenta o custo de cada
caminho; ela não escolhe. Escolher pelo pesquisador é o erro que a Fase 2 da
própria curadoria nomeou — *"o ecossistema tem mais coisa construída do que
decidida"* — e uma curadoria que decide sozinha repete esse erro um nível
acima.

## A pergunta

`emit_ranking_decision` (`edp/memory/store.py:765`) emite, sob a flag
`EDP_RANKING_TELEMETRY` (default OFF), a cascata completa de redução do
retrieval: quantos candidatos foram avaliados, quantos passaram do piso,
quantos sobreviveram ao filtro de sessão, quantos ao filtro de recusa, e
quantos chegaram ao prompt — com os fatores de score das 20 primeiras
posições.

O `DIAGNOSTICO v1` do MVP mede **o que saiu** do retriever (cardinalidade,
duplicação, sobreposição). Esta telemetria explica **onde os candidatos se
perderam** — a pergunta que qualquer cliente faz depois de ver "37 documentos
distintos de 50 slots".

A tentação é ligar a flag e acoplar. As três opções abaixo dizem o que isso
custa, de fato.

---

## A — acoplar como está, contra o EDP como cliente de referência

**O que está sendo medido:** o funil de retrieval do EDP, exatamente como
implementado hoje, com a flag ligada só onde o auditor consultar.

**Qual comportamento muda:** nenhum no kernel — a telemetria é `if` puro com a
flag OFF (documentado no próprio emissor). Muda o **contrato do auditor**: um
novo método opcional (`telemetria_do_funil()`, por exemplo) em
`SistemaAuditavel`, com default vazio para quem não implementa.

**Impacto no `CLAIMS.md`:** nenhum se a nova seção do relatório ficar em
NÍVEL 1 (observação) — a cascata é fato sobre o processo, não avaliação de
qualidade. Precisa de revisão para garantir que a redação não desliza para
"o retriever descartou candidatos bons" (NÍVEL 3, não medido).

**Comparabilidade:** não há histórico prévio para comparar — a flag nunca
rodou fora de teste (medido: 395 eventos no store vivo, zero são
`ranking_decision`). O primeiro dado real seria também o baseline.

**Necessidade de novo experimento:** não, no sentido do `NORTE §4.2` — não é
medição de hipótese, é exposição de dado já calculado.

**Implicações comerciais:** só o EDP emite isso hoje. Um cliente com outro
RAG **não tem** essa telemetria a menos que exponha algo equivalente — o que
o caso B do pré-registro do piloto (`PILOTO_ZERO/PREREGISTRO.md`) já prevê
como comum. Não é capacidade universal; é capacidade do EDP como primeiro
cliente.

**Risco:** baixo tecnicamente, médio em expectativa — se o relatório de
diagnóstico passar a ter uma seção rica só quando o cliente é o próprio EDP,
isso precisa estar dito, não implícito.

---

## B — não acoplar; manter o MVP agnóstico do fornecedor

**O que está sendo medido:** nada muda. O `DIAGNOSTICO v1` continua medindo
só o que qualquer adaptador consegue expor pelos quatro métodos do contrato
público.

**Qual comportamento muda:** nenhum.

**Impacto no `CLAIMS.md`:** nenhum.

**Comparabilidade:** total — o relatório do EDP e o de qualquer outro cliente
continuam na mesma régua.

**Necessidade de novo experimento:** não.

**Implicações comerciais:** o produto continua vendendo a mesma promessa para
qualquer cliente, sem uma seção que só existe para um fornecedor específico.
Custo: a pergunta "por que só 37 de 50" fica sem resposta automática — o
cliente teria que instrumentar o próprio retriever para obtê-la, e hoje quase
nenhum contrato de RAG expõe isso (é a mesma lacuna que o **Serviço A** de
`CANDIDATOS_NOVOS_SERVICOS.md` registra).

**Risco:** nenhum técnico. O risco é de oportunidade — a telemetria já existe,
testada, e fica sem uso.

---

## C — acoplar como extensão declarada, não como parte do `DIAGNOSTICO v1`

**O que está sendo medido:** uma régua **nova**, com escopo próprio — algo como
`DIAGNOSTICO-FUNIL v1`, que exige o método opcional do contrato e é oferecida
só a clientes que o implementam. Não estende `DIAGNOSTICO v1`; coexiste com
ele.

**Qual comportamento muda:** nenhum no kernel. No MVP, uma nova entrada em
`PROTOCOLOS` (`auditor/cli.py`), com `escopo="diagnostico"` e `exposto`
decidido separadamente.

**Impacto no `CLAIMS.md`:** exige a mesma disciplina de A, mas isolada — um
erro na seção do funil não arrisca o relatório padrão que todo cliente recebe.

**Comparabilidade:** o `DIAGNOSTICO v1` fica intacto e comparável entre
clientes; a régua nova é comparável só entre clientes que a suportam — que
hoje é um: o EDP.

**Necessidade de novo experimento:** não para a exposição do dado; **sim** se
algum dia a seção passar a fazer afirmação de causa ("o filtro de sessão está
descartando candidatos relevantes") em vez de descrição do processo — aí vira
NÍVEL 2 ou 3, e a régua precisa da mesma disciplina que
`CANDIDATOS_NOVOS_SERVICOS.md` já exige do Serviço B.

**Implicações comerciais:** mais preciso que A — não infla silenciosamente o
que o `DIAGNOSTICO v1` promete a todo cliente, e deixa claro que a régua do
funil é dependente de fornecedor. Custo: mais uma régua para manter, testar e
explicar.

**Risco:** baixo. É o caminho que mais se parece com o resto do MVP —
`BASICO` e `DIAGNOSTICO` já coexistem como réguas com escopos distintos.

---

## O que já está resolvido, e sai da discussão

**Os outros dois candidatos "acoplar agora" não têm essa decisão pendente.**
O leitor de `events.jsonl` (candidato nº 2) **depende** desta decisão — sem
o funil gerando dado real, não há o que ler de interessante. O padrão
`test_flag_off_byte_identical` (candidato nº 3) é só um teste novo do lado do
auditor; não precisa de decisão, precisa de trabalho.

**O trio `exp017`** (`EDP_RETRIEVE_DEDUP`/`SHUFFLE`/`RANDOM_DROP`) não está
nesta decisão — tem a própria, já em andamento, em
`docs/auditor/DECISAO_RANKING.md`. As duas decisões são irmãs (mesma origem:
flag testada, promoção a produção pendente de assinatura), mas não a mesma
pergunta — uma muda o objeto auditado, esta não muda nada no kernel.

## Recomendação, que não é decisão

**C.** Pelas mesmas razões que o MVP já separou `DIAGNOSTICO v1` de `BASICO`:
uma régua nova, com escopo declarado, custa pouco a mais que estender a
existente, e não arrisca a promessa que já vale para todo cliente. A é mais
rápido e mais arriscado; B desperdiça engenharia testada sem necessidade.

Mas o custo de C não é zero: ele só compensa se houver expectativa real de um
segundo cliente que também exponha telemetria de funil — e isso é
exatamente o tipo de coisa que só um piloto externo responde, não esta
curadoria.

## Registro da decisão

```
decidido por ....... ____________________
data ............... ____________________
opcao .............. A / B / C
justificativa ...... ____________________
```

Enquanto estas linhas estiverem em branco, nenhuma flag de telemetria é
ligada para o MVP, e nenhum método novo entra em `SistemaAuditavel`.
