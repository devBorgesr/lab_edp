# Decisão pendente — qual ranking o serviço considera auditável

**31/08/2026. Nenhuma opção foi escolhida.** Este documento existe para que a
escolha seja humana, explícita e datada, e não emerja de um `default` que
alguém escreveu com pressa.

## A pergunta

O índice do EDP conta o mesmo documento duas vezes: a consolidação promove de
episódica para semântica **sem remover da origem**, e `_hybrid_index`
(`store.py:1616`) varre as duas camadas sem deduplicar. Medido nos **17 stores**
de `edp_data_todo/`: em todos, 100% dos ids semânticos também estão na
episódica.

Consequência medida: `top_k=50` devolve **50 slots** e **29–41 documentos
distintos**.

Deduplicar **renumera as posições**. A posição 30 do ranking deduplicado é ~45
no de produção. O `§3.2` do REL-001 diz *"posições 20–50 do mesmo retriever"* —
e sob dedup essa frase passa a apontar para outro conjunto de documentos, sem
que uma linha do pré-registro mude.

Não é uma questão de quanto material existe. É **de qual ranking o protocolo
fala**.

---

## A — auditar o retriever exatamente como está em produção

**O que está sendo medido:** o que o usuário do EDP recebe hoje, duplicação
inclusive. É o único dos três que mede o sistema real.

**Qual comportamento muda:** nenhum. O objeto fica intacto.

**Impacto no protocolo:** o `§3.2` precisa operar sobre um ranking cuja
cardinalidade efetiva é 29–41. Como está escrito, ele **não opera** — exige 50
distintos. Ou a janela da cauda muda, ou `N_DOCS_POR_QUERY` muda.

**Comparabilidade histórica:** total. Todas as medições anteriores sobre este
retriever continuam comparáveis.

**Novo experimento?** Sim — mudar a janela é mudar a régua, logo REL-002 com
poder recalculado.

**Comercial:** é o caminho mais honesto de vender. O cliente quer saber como o
sistema dele se comporta, não como se comportaria depois de um conserto que
ninguém fez.

---

## B — auditar um retriever explicitamente deduplicado

**O que está sendo medido:** um sistema que **não existe em produção**. A
duplicação continua lá para o usuário final.

**Qual comportamento muda:** o conjunto recuperado, só dentro da auditoria.

**Impacto no protocolo:** o `§3.2` volta a ser satisfazível — 112–132 distintos
por query. Mas "posições 20–50" passa a significar outra coisa, e isso precisa
ser **declarado como condição experimental congelada**, não adotado porque
resolve.

**Comparabilidade histórica:** quebrada. Nenhuma medição anterior é comparável
a esta, e um número desta condição ao lado de um número da condição A é
comparação entre coisas diferentes.

**Novo experimento?** Sim, e com a condição no nome.

**Comercial:** risco alto de leitura errada. Um relatório dizendo "seu
retrieval vai bem" sobre um retriever que o cliente não usa é, na prática, uma
afirmação falsa — mesmo com a condição escrita em nota de rodapé.

---

## C — corrigir o índice de produção antes da auditoria

**O que está sendo medido:** um sistema novo, depois da correção.

**Qual comportamento muda:** o conjunto recuperado **em todo turno**, para todo
usuário. É `FORMAT_STATE_FLAGS`.

**Impacto no protocolo:** o `§3.2` passa a caber. Mas o objeto sob o REL-001
teria mudado no meio.

**Comparabilidade histórica:** quebrada, e de forma mais séria que em B —
exp008, exp009, exp010 e exp017 mediram o retriever com duplicação.

**Novo experimento?** Dois. Um para a correção (flag, `flag-off` byte-idêntica,
medição antes/depois, per `NORTE §4.7`), outro para o REL sobre o objeto novo.

**Comercial:** o mais valioso a médio prazo — um retriever sem duplicação é
melhor produto. Mas é trabalho de engenharia com pré-registro próprio, e
misturá-lo com a auditoria contamina os dois.

---

## O que já está resolvido, e sai da discussão

**Expandir o corpus não é caminho.** Medido: consultando o ranking inteiro, cada
query tem 112–132 ids distintos e 98–118 textos distintos; 50 de 50 passam dos
50. O corpus tem material de sobra — a duplicação consome a janela.

Esta linha estava na matriz anterior como plausível. A medição a removeu.

## Recomendação do agente, que não é decisão

**A**, com REL-002 redesenhando a janela.

O serviço de auditoria vende medir o sistema do cliente como ele é. B mede um
sistema que não existe, e C é engenharia de produto disfarçada de metodologia.
Se a duplicação for um defeito grave — e a medição sugere que é — o caminho é
consertá-la **em experimento próprio**, e depois auditar o objeto novo.

Mas o custo de A está declarado e não é pequeno: o `§3.2` como está não opera, e
qualquer janela nova precisa de poder recalculado.

## Registro da decisão

```
decidido por ....... ____________________
data ............... ____________________
opcao .............. A / B / C
justificativa ...... ____________________
```

Enquanto estas linhas estiverem em branco, o REL-001 permanece **BLOQUEADO** e
nenhuma coleta é autorizada.
