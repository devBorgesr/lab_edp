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


---

# Atualização 03/09/2026 — a direção mudou, e A/B/C não a cobrem

O pesquisador decidiu: **`chrome.debugger` deixa de ser camada de observação e
passa a ser camada de atuação do Copiloto, dentro do próprio dashboard, com
acesso às features e módulos do EDP nas páginas.**

Isso não é a opção B nem a C. É uma quarta, e ela muda um pressuposto que as
três anteriores tratavam como fixo. Registrada abaixo como **D**, com a
inspeção que ela exige.

## O que a inspeção de 03/09 estabeleceu

### O manifest já permite; o que falta é decisão, não permissão

```
manifest_version ........... 3
permissions ................ activeTab, scripting, downloads, tabs,
                             storage, alarms, DEBUGGER      <- ja esta la
host_permissions ........... ["https://claude.ai/*"]
optional_host_permissions .. ["http://*/*", "https://*/*"]  <- cobre 127.0.0.1
nativeMessaging ............ AUSENTE
devtools_page .............. AUSENTE
externally_connectable ..... AUSENTE
web_accessible_resources ... AUSENTE
```

`chrome.debugger` **já está disponível hoje**. A fronteira que impede a
atuação é o bloco `"O que este módulo NUNCA FAZ"`, escrito em
`debugger_capturer.js` — texto, não trava do navegador. Atacar a atuação não
exige mudar o manifest; exige assumir por escrito que aquela promessa mudou.

Para anexar a `http://127.0.0.1:8000/dashboard` basta a permissão de host
opcional concedida em runtime — padrão já implementado duas vezes na extensão
(`options.js:30`, `copilot/llm_adapter.js:124`).

### `chrome.debugger` roda no PAINEL, não no service worker

```
copilot/debugger_capturer.js .. 14 chamadas chrome.debugger.*
copilot/panel.js ............... 1 chamada
copilot/panel.html:162 ......... <script src="debugger_capturer.js">
```

O capturador é carregado por `panel.html`. O contexto que fala CDP é a **aba
do painel** — escolha coerente com o que `DECISAO_TRANSPORTE.md` já havia
registrado: o painel é aba própria, sem o problema de tempo de vida do service
worker do MV3.

## O achado que decide a arquitetura: a DIREÇÃO se inverte

O Python **não pode** chamar `chrome.debugger`. Só um contexto de extensão
pode. Então uma capacidade `browser.click` executada pelo Runtime é,
necessariamente, o Runtime **mandando um comando para a extensão** e esperando
o resultado.

E é exatamente isso que o transporte assinado não faz:

```
assinado (opcao A) ....  painel  --HTTP-->  Runtime      (painel e o CLIENTE)
atuacao exige .........  Runtime  ------>   painel       (direcao que NAO existe)
```

Não há `externally_connectable`, não há `web_accessible_resources`, e o painel
não escuta em porta nenhuma. **Hoje o Runtime não tem como iniciar nada em
direção à extensão.** Este é o item que precisa ser resolvido antes de
qualquer `ChromeProvider`, e nenhum dos três desenhos discutidos até aqui o
resolve sozinho.

### As três formas de resolver, com o custo real

**D1 — o painel busca comandos pendentes (polling).**
```
manifest ......... NAO muda
transporte ....... o de sempre; o painel ja e cliente HTTP
mecanismo ........ GET /v1/tarefas/{id}/comandos  ->  POST .../comandos/{i}/resultado
latencia ......... um intervalo de poll por acao
custo ............ o menor dos tres. Nenhuma peca nova de infraestrutura.
```

**D2 — WebSocket bidirecional (a opção `B` de `DECISAO_TRANSPORTE.md`).**
```
manifest ......... NAO muda
mecanismo ........ push do Runtime para o painel, sem espera
custo ............ reconexao, heartbeat, ordenacao, estado de conexao —
                   tudo que a assinatura de 03/09 mandou adiar
gatilho .......... a propria assinatura diz que `B` volta a mesa quando
                   houver progresso incremental. Atuacao E esse gatilho.
```

**D3 — Native Messaging.**
```
manifest ......... MUDA: exige a permission `nativeMessaging`
contexto ......... `connectNative` vale para paginas de extensao E para o
                   service worker — entao o PAINEL pode usar, e o painel e
                   quem ja tem a sessao do debugger. Encaixa.
identidade ....... `allowed_origins` amarra ao ID exato da extensao; e
                   autenticacao de fronteira, nao segredo em JavaScript
custo ............ instalacao de host nativo por maquina, com caminho
                   absoluto. A maior friccao das tres.
bidirecional ..... nativo
```

Nenhuma das três é bloqueada por engenharia ausente. A escolha é de fricção
contra limpeza de fronteira.

---

## D — atuação plena, governada pelo Registry, dentro do dashboard

**O que muda:** o modelo propõe `browser.*` e `memory.*`/`retrieval.*`/
`graph.*`/`flags.*` como capacidades; a `Politica` decide; um
`ChromeProvider` traduz capacidade em CDP. O Copiloto **nunca** emite comando
CDP direto — ele submete tarefa e recebe observação, como qualquer cliente.

**O que esta opção corrige em A/B/C:** as três assumiam que o alvo é *a aba
autenticada do usuário*, e daí vinha o peso do risco (`act.javascript` alcança
a sessão inteira; `act.network` emite requisição com os cookies dele). **O
alvo declarado agora é o dashboard do próprio EDP, em `127.0.0.1`.** Isso não
elimina o risco, mas muda-o de categoria: agir sobre a própria ferramenta não
é agir sobre a sessão de terceiros. A opção `C` existia justamente para
comprar essa separação a alto custo — e o novo alvo a entrega de graça,
**desde que o escopo de aba seja imposto e não apenas pretendido.**

**O que se perde:** a promessa escrita. O bloco `"O que este módulo NUNCA
FAZ"` passa a ser falso no instante em que o primeiro `Input.*` for enviado.

**Risco, nomeado:**
```
escopo de aba .... se o provider anexar a qualquer aba, o argumento acima cai
                   junto. A restricao "so 127.0.0.1:<porta do dashboard>"
                   precisa estar NO CODIGO, nao na intencao.
act.evaluate ..... executa na origem da pagina. Na origem do dashboard, isso
                   alcanca o que o dashboard alcanca — inclusive o campo de
                   API key. Merece tratamento proprio, nao "mais uma da lista"
irreversibilidade  nenhuma acao L1/L2 e desfeita pelo proprio agente
```

**Custo:** `ChromeProvider` (Python), `debugger_controller.js` (extensão), o
canal de volta (D1/D2/D3), e a reescrita do bloco `NUNCA FAZ` **no mesmo
commit** que o rompe.

### O primeiro passo que esta opção pede, e não é a atuação inteira

Um *vertical slice* com **uma** ação real, ponta a ponta:

```
Copiloto -> Task -> Router -> Modelo -> Intencao: browser.click
         -> Politica -> ChromeProvider -> chrome.debugger -> Observacao
```

`RoteadorFixo` + `ClienteFake` primeiro, como no smoke que já existe. Uma
capacidade só, um alvo só, escopo de aba imposto no código. Só depois expandir
o Registry.

**Uma linha de aviso, e sigo:** D é a única das quatro que torna falsa uma
promessa de segurança já publicada no código. Isso não é motivo para não
fazer — é motivo para que a reescrita daquele bloco entre no mesmo commit, e
para que o escopo de aba seja teste, não comentário.

## Implementação iniciada — 03/09/2026

O primeiro *vertical slice* de `D` foi construído **antes** da assinatura, e
isto não é atalho: **`browser.inspect` é L0**. Ela só lê — url, título,
histórico e contagem de nós do DOM — e a única `Runtime.evaluate` do caminho é
uma constante escrita no próprio controller, não expressão vinda do modelo.
`exige_implementada()` recusa L1/L2; não recusa observação. A assinatura
abaixo continua sendo o que libera `browser.click` e o resto.

```
agent_runtime/capacidades.py .............. browser.inspect, L0, implementada
agent_runtime/provedores/browser.py ....... ChromeDebuggerProvider + CanalBrowser
tests/test_browser_provider.py ............ 23 testes
copilot/debugger_controller.js ............ o componente que atua
copilot/debugger_capturer.js .............. cabecalho delimitado: so observacao
copilot/panel.html ........................ carrega o controller
```

`CanalBrowser` é `Protocol`: o transporte é detalhe substituível, e Native
Messaging vira **uma implementação de canal**, não uma decisão de arquitetura
a tomar antes do slice.

Falta para o slice fechar: a implementação de canal sobre o transporte real, e
o smoke com o dashboard aberto de verdade.

## Registro da decisão

```
decidido por ....... ____________________
data ............... ____________________
opcao .............. A / B / C / D
se D, canal de volta D1 polling / D2 WebSocket / D3 Native Messaging
se D, alvo permitido ____________________   (ex.: so 127.0.0.1:8000)
se D, primeira capacidade do vertical slice ____________________
justificativa ...... ____________________
```

Enquanto estas linhas estiverem em branco, `agent_runtime` observa e não atua,
e `exige_implementada()` recusa toda capacidade L1/L2.
