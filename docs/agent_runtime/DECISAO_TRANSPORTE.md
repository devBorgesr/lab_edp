# Decisão pendente — o transporte Copiloto → Agent Runtime

**03/09/2026. Nenhuma opção foi escolhida. Nenhum código foi alterado.**

Inspeção antes de escolher, conforme a regra: manifest real, contextos JS,
onde o painel pode falar, e as restrições MV3 que valem — verificadas neste
código, não deduzidas da documentação do Chrome.

---

## 1. O que foi verificado

### O manifest (v4.10.0, MV3)

```
permissions               activeTab, scripting, downloads, tabs, storage,
                          alarms, debugger
host_permissions          ["https://claude.ai/*"]
optional_host_permissions ["http://*/*", "https://*/*"]     ← decisivo
background                { "service_worker": "background.js" }
options_ui                options.html (open_in_tab)
devtools_page             AUSENTE
nativeMessaging           AUSENTE das permissions
externally_connectable    AUSENTE
web_accessible_resources  AUSENTE
content_security_policy   AUSENTE (defaults do MV3)
```

### ERRATA de uma afirmação minha, de 01/09

`docs/agent_runtime/README.md` e o commit `a98b0bf` afirmam:

> HTTP local → exige `host_permission` nova = **mexe no Exportador (manifest)**

**Está errado.** Existe `optional_host_permissions: ["http://*/*", "https://*/*"]`.
Uma origem `http://localhost:<porta>/*` pode ser concedida **em tempo de
execução**, sem tocar no manifest. Eu olhei só `host_permissions` e concluí
demais.

Pior: **o padrão já está implementado duas vezes** nesta extensão —
`options.js:30` e `copilot/llm_adapter.js:124`, ambos
`chrome.permissions.request({ origins: [origin] })`.

### Os contextos JS, e quem pode iniciar comunicação

| contexto | arquivo | vida | pode iniciar? |
|---|---|---|---|
| service worker | `background.js` | **morre ocioso (MV3)** | sim, com ressalva |
| painel do Copiloto | `copilot/panel.html` | **aba própria, vive enquanto aberta** | **sim, sem ressalva** |
| content script | `content.js`, `interceptor.js` | vida da página claude.ai | sim, mas contexto errado |
| popup | `popup.js` | morre ao fechar | não serve |
| options | `options.html` | aba | serve, mas não é o Copiloto |

O painel **abre como aba própria** (`popup.js:123`,
`chrome.tabs.create(chrome.runtime.getURL('copilot/panel.html'))`) — é página
de extensão comum, **sem o problema de tempo de vida do service worker**.

O service worker tem o problema, e ele **já foi enfrentado**: `live_feed.js:24`
registra que não há conexão persistente "de verdade" em MV3, e mitiga com
`chrome.alarms` a cada minuto (`live_feed.js:350-353`).

### O painel já fala com `localhost` — verificado, não suposto

`panel.html:166` carrega `llm_adapter.js`, que faz `fetch()` cross-origin para
`http://localhost:11434` (Ollama) depois do `permissions.request`
(`llm_adapter.js:138, 278`). E `assertLocalOrigin()` (`llm_adapter.js:97-101`)
**recusa por código** qualquer host que não seja `localhost`, `127.0.0.1` ou
`[::1]`.

**Isto é prova neste código, nesta versão do MV3, de que o mecanismo funciona
— e de que a disciplina "só local" já é praticada aqui.**

### Já existe um canal Extensão → EDP, autenticado

```
live_feed.js:85     default  ws://localhost:8000/stream
live_feed.js:255    new WebSocket(url, [token])   ← Sec-WebSocket-Protocol
WEBSOCKET_API.md    EDP_LIVE_FEED_TOKEN, duas formas (query string ou
                    subprotocolo; o segundo é o preferível — não cai em log
                    de acesso HTTP)
edp/ingest/websocket_receiver.py   o lado que recebe
```

O problema de autenticação de WebSocket em navegador (não dá para mandar
header) **já está resolvido** neste projeto, e documentado.

---

## 2. A segunda fronteira deliberada

`edp/ingest/websocket_receiver.py`, no próprio docstring:

> Comunicação **estritamente unidirecional** (sensor → EDP): o único retorno
> do servidor é `pong` (heartbeat) ou `error` — **o EDP nunca envia comandos
> de volta ao sensor.**

O fluxo pedido exige **resultado voltando ao Copiloto**. Aproveitar `/stream`
significa romper essa unidirecionalidade — a mesma classe de decisão que o
`"O que este módulo NUNCA FAZ"` de `debugger_capturer.js`.

É a segunda fronteira de segurança escrita que este trabalho encontra. Ela não
é obstáculo acidental: um canal onde o servidor nunca manda comando é um canal
que não pode ser usado para dirigir o navegador de ninguém.

---

## 3. As alternativas reais

### A — HTTP request/response, painel → servidor local do Runtime

```
mecanismo ......... fetch() de copilot/panel.js para http://127.0.0.1:<porta>
manifest .......... NÃO muda (optional_host_permissions cobre)
permissão ......... chrome.permissions.request em runtime — padrão já usado 2x
MV3 ............... painel é aba própria; sem problema de service worker
prova ............. o painel JÁ faz exatamente isto com Ollama
toca no Exportador  código novo em panel.js. NÃO toca debugger_capturer.js,
                    NÃO toca live_feed.js, NÃO toca o manifest
toca no edp_v5 .... NÃO
autenticação ...... header comum (`Authorization`), trivial em HTTP
bidirecional ...... nativo (request/response)
```

Casa com a instrução explícita: *"Não crie streaming complexo ainda. Primeiro
faça request/response confiável."*

### B — WebSocket bidirecional novo, painel → Runtime

```
manifest .......... NÃO muda
autenticação ...... precisa do truque do subprotocolo (browser não manda
                    header) — já resolvido em live_feed.js, reaproveitável
bidirecional ...... nativo, com push
custo ............. maior: reconexão, heartbeat, ordenação, estado de conexão
                    — tudo que a instrução mandou adiar
```

Melhor que A **só quando houver streaming de progresso**. Hoje não há.

### C — reaproveitar o `/stream` existente

```
custo real ........ ROMPER a unidirecionalidade documentada do receiver
onde ............. edp_v5 (repositório PÚBLICO) e no lab
```

**Não recomendado.** O `/stream` é o canal do *sensor*; a submissão de tarefa
é outra coisa, com outra direção e outro risco. Misturar as duas apaga a
propriedade que torna o `/stream` seguro.

### D — Native Messaging

```
manifest .......... MUDA (precisa da permission `nativeMessaging`)
instalação ........ manifesto de host nativo em diretório do SO + caminho
                    absoluto do executável, por máquina
bidirecional ...... sim
```

Maior fricção de instalação de todas, e a única que exige mudar o manifest.
Só se justificaria se o transporte precisasse existir sem servidor HTTP.

### E — arquivo manual (estado atual)

```
custo ............. zero nos dois lados
limitação ......... o operador copia JSON à mão; não é integração
```

É o que `requisicao.py` implementa hoje, e continua sendo o piso.

---

## 4. Os requisitos de segurança, contra as opções

| requisito | A (HTTP) | B (WS) | C (/stream) | D (nativo) |
|---|---|---|---|---|
| handshake/autenticação | header, trivial | subprotocolo | herda | canal do SO |
| identificação do cliente | header | subprotocolo | herda | processo |
| validar `TarefaRequest v1` | igual em todas — é do Runtime, não do transporte |
| limite de tamanho | nativo no servidor | por frame | herda | por mensagem |
| timeout | nativo | precisa implementar | herda | precisa |
| rejeitar schema/campo desconhecido | igual em todas — `requisicao.valida` já faz |
| teto L0 | igual — `para_tarefa(teto_nivel)` já recusa |
| isolamento entre tarefas | `task_id` no Runtime, igual em todas |
| desconexão | irrelevante (stateless) | precisa | precisa | precisa |
| **não expor 0.0.0.0** | **bind 127.0.0.1** | idem | já é do EDP | N/A |

A maior parte dos requisitos **não é do transporte** — é do `TaskService`, e
vale igual para qualquer opção. O que o transporte decide é: autenticação,
timeout, desconexão e bind.

---

## 5. Recomendação, que não é decisão

**A — HTTP request/response, do painel para `127.0.0.1`.**

Três razões, em ordem de peso:

1. **É o único cujo mecanismo já está provado neste código.** O painel já faz
   `fetch` cross-origin para `localhost` depois de pedir permissão em runtime.
   Não é extrapolação de documentação do Chrome; é o que a extensão faz hoje.
2. **Não toca em nenhuma das duas fronteiras de segurança escritas** — nem o
   `NUNCA FAZ` do `debugger_capturer.js`, nem a unidirecionalidade do
   `/stream`. E não muda o manifest.
3. **É o que a própria instrução pede**: request/response confiável antes de
   streaming.

O custo honesto: **código novo em `copilot/panel.js`** — não dá para ter
transporte real sem tocar no Exportador em algum lugar. O que se escolhe é
*onde*, e `panel.js` é o lugar de menor consequência: não é o capturador, não
é o manifest, não é o canal do sensor.

`B` fica como caminho natural depois, se aparecer streaming de progresso. `D`
só se um dia o servidor HTTP for inviável. `C` eu não recomendaria em nenhum
cenário.

---

## 6. O que esta decisão NÃO resolve

**A porta.** `8000` é do EDP. O Runtime precisa da sua, e a escolha é do
pesquisador — colocá-la em `8000` misturaria dois serviços com contratos
diferentes no mesmo lugar.

**Onde o servidor vive.** `agent_runtime` é `lab_edp_novo` (privado). Um
servidor HTTP ali não é o mesmo que um endpoint no `edp_v5` (público), e a
escolha tem consequência de repositório, não só técnica.

**Se o Copiloto deve mesmo ser o cliente.** O painel é a interface natural,
mas nada impede que a primeira versão seja uma página separada — e isso
adiaria tocar no Exportador mais um passo.

## Registro da decisão

```
decidido por ....... Daniel Sousa (pesquisador)
data ............... 03/09/2026
opcao .............. A  — HTTP request/response
porta .............. 8010                      (8000 continua sendo do EDP)
servidor vive em ... lab_edp_novo              (privado)
cliente v1 ......... pagina separada           (o Exportador NAO e tocado ainda)
justificativa ...... e o unico transporte cujo mecanismo ja esta provado
                     neste codigo; nao muda o manifest; nao rompe nenhuma
                     das duas fronteiras de seguranca escritas.
```

## O que a assinatura autoriza, e o que não autoriza

**Autoriza:** servidor HTTP em `lab_edp_novo`, bind `127.0.0.1:8010`,
request/response, sem streaming. Cliente da primeira versão é uma **página de
teste separada** — o transporte é provado fim-a-fim antes de qualquer código
novo entrar no Exportador.

**Não autoriza:**

- tocar em `copilot/panel.js`, no manifest, ou em qualquer arquivo do
  Exportador. O painel vira o **segundo** cliente, em etapa própria;
- bind em `0.0.0.0` — a decisão é `127.0.0.1` e o teste tem de provar isso;
- streaming, push, ou conexão persistente (isso é a opção `B`, e o gatilho
  para reabrir a escolha é o aparecimento de progresso incremental);
- subir o teto de capacidade. O transporte carrega `Tarefa` como ela já é:
  `L0 OBSERVAR`, e `para_tarefa(teto_nivel)` continua sendo quem recusa.

**O que continua não decidido:** se o Runtime deve um dia falar com o EDP
diretamente. Nada aqui muda a unidirecionalidade de
`edp/ingest/websocket_receiver.py`, e a opção `C` segue não recomendada.
