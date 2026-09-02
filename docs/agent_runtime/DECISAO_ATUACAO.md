# Decisão pendente — o agente pode ALTERAR o ambiente?

**01/09/2026. Nenhuma opção foi escolhida.** Forma de
`docs/auditor/DECISAO_RANKING.md` e `docs/curadoria/DECISAO_ACOPLAMENTO.md`:
as opções e o custo de cada uma; a linha da decisão fica em branco.

## A fronteira que já existe, e que não foi acidental

`sf_exportador/claude-exporter-v4.2/copilot/debugger_capturer.js` carrega um
bloco intitulado **"O que este módulo NUNCA FAZ"**. Textualmente:

> Nunca envia nenhum comando CDP fora da lista usada abaixo
> (`Network.enable/disable`, `Network.getResponseBody`,
> `Runtime.enable/disable`) — em especial, **nunca `Input.*`, `Page.navigate`,
> `Page.reload` ou qualquer comando que ALTERE a aba. Só observa.**

E mais: nunca anexa a mais de uma aba, nunca envia o capturado para fora da
máquina, e redige `authorization`, `cookie`, `x-api-key` e outros por default.

Verificado no código (01/09): os únicos comandos CDP presentes são
`Network.enable`, `Network.getResponseBody` e `Runtime.enable`, mais os
eventos que eles habilitam. **A restrição é real, não aspiracional.**

`agent_runtime/capacidades.py` declara as capacidades L1/L2 e **recusa
executá-las**, apontando para este documento. Nada foi implementado.

## O que está em jogo

O ambiente é o navegador do usuário, **autenticado**. A aba onde o capturador
opera é a mesma onde ele está logado — em `claude.ai`, e no que mais estiver
aberto. Uma capacidade L1/L2 nesse contexto não é "clicar num botão": é agir
com a sessão de alguém.

```
act.javascript   executa na origem da página     → alcança a sessão inteira
act.navigate     leva a aba autenticada          → para onde o modelo decidir
act.network      emite requisição com os cookies → em nome do usuário
act.download     escreve no disco do host        → fora do sandbox
```

Nenhuma delas é reversível pelo próprio agente.

---

## A — manter observação apenas (estado atual)

**O que muda:** nada. O agente investiga sobre HAR e console já capturados.

**O que se perde:** todo loop que dependa de *provocar* o ambiente — repetir
uma query com parâmetro diferente, reproduzir um erro, testar hipótese por
intervenção. O agente observa o que aconteceu; não pode fazer acontecer.

**Risco:** nenhum novo. A superfície de ataque continua sendo leitura de
arquivo.

**Custo:** o "Research Agent" e o "Browser Agent" do desenho não existem.
Sobra o investigador passivo — que ainda é útil, e é o que os 23 testes
cobrem hoje.

---

## B — L1 com aprovação humana por ação

**O que muda:** `act.click`, `act.fill`, `act.reload` passam a existir, cada
chamada exigindo aprovação explícita. `Politica(aprovador=...)` já suporta
isso — o gancho está construído e testado; falta o executor CDP.

**O que se perde:** a autonomia real. Um loop de 20 iterações com aprovação
por ação é um loop que precisa de 20 aprovações — na prática, alguém clica
"sim" em série, e a aprovação vira formalidade. **Este é o modo de falha
previsível desta opção**, e ele não é técnico.

**Risco:** médio, e concentrado no humano que aprova sem ler.

**Custo:** implementar `Input.dispatchMouseEvent` e `Input.dispatchKeyEvent`
no capturador — rompendo o bloco "NUNCA FAZ", que precisaria ser reescrito
para dizer a verdade nova.

---

## C — L1 em aba dedicada, isolada da sessão do usuário

**O que muda:** o agente atua, mas nunca na aba do usuário — numa aba/perfil
próprio, sem os cookies dele.

**O que se perde:** a capacidade de investigar *o problema do usuário*, que
frequentemente só existe autenticado. Um 403 numa sessão limpa não é o 403
que o usuário viu.

**Risco:** baixo. É o desenho que separa o que observa do que atua.

**Custo:** o mais alto dos três — exige gestão de perfil/aba separada,
e o capturador hoje "nunca anexa a mais de uma aba ao mesmo tempo", outra
linha do mesmo bloco que precisaria mudar.

---

## O que NÃO está nesta decisão

**L2 não é opção aqui.** `act.navigate`, `act.download` e `act.network` ficam
fora das três opções de propósito: mesmo em C, emitir requisição com os
cookies do usuário ou escrever no disco do host é outra ordem de risco, e
mereceria decisão própria — não um item numa lista de três.

**O MVP de Diagnóstico não é afetado por nenhuma opção.** `auditor/` não
importa `agent_runtime/`, e o piloto externo continua sendo a prioridade
declarada. Esta decisão não bloqueia aquele, nem o contrário.

## Recomendação, que não é decisão

**A, até o piloto externo.** Não por conservadorismo: porque as três opções
custam trabalho de engenharia real, e nenhuma delas responde a pergunta que
está aberta há mais tempo — se alguém externo consegue e quer usar isto. O
investigador passivo sobre HAR já permite descobrir isso, e não pede que a
fronteira seja rompida antes de haver evidência de que vale.

Se a decisão for B ou C, o bloco "O que este módulo NUNCA FAZ" precisa ser
**reescrito no mesmo commit** que o rompe. Uma promessa de segurança que
sobrevive à própria violação é pior que não ter promessa.

## Registro da decisão

```
decidido por ....... ____________________
data ............... ____________________
opcao .............. A / B / C
justificativa ...... ____________________
```

Enquanto estas linhas estiverem em branco, `agent_runtime` observa e não atua,
e `exige_implementada()` recusa toda capacidade L1/L2.
