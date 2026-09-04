# Smoke real — `browser.inspect` com Chrome de verdade

**03/09/2026. NÃO EXECUTADO.** Este documento existe porque a etapa não pode
ser fechada nesta máquina, e escrever "fechado" sem a evidência seria a única
coisa que não dá para desfazer depois.

## Por que não foi executado aqui

```
google-chrome / chromium / chromium-browser  ->  ausentes do PATH
firefox                                      ->  presente
```

A extensão é MV3 e usa `chrome.debugger`, que o Firefox não implementa. **Não
há navegador nesta máquina capaz de rodar este smoke.** O ambiente do
pesquisador (host Windows, onde o EDP roda em `C:\edp_data_todo`) tem Chrome;
lá o procedimento abaixo roda.

## O que JÁ está provado, e por qual teste

| camada | evidência | onde |
|---|---|---|
| provedor: alvo, recusas, normalização | 24 testes | `tests/test_browser_provider.py` |
| mesa: correlação, concorrência, TTL | 21 testes | `tests/test_canal_browser.py` |
| endpoints + laço até tarefa persistida | 15 testes | `tests/test_canal_http.py` |
| **controller real**, sob `chrome` simulado | 15 checagens | `tests/js/test_controller.mjs` |

O arnês em node carrega o `debugger_controller.js` **real** do Exportador num
`vm` com um `chrome` falso, e cobre os três negativos obrigatórios: alvo
errado, origem mudada depois do registro, e debugger desanexado.

**O que nenhum deles prova:** que `chrome.debugger.sendCommand` de verdade
devolve o que o controller espera. É exatamente isso que o procedimento
abaixo mede.

---

## Procedimento

### 1. Suba o Runtime com o provedor de navegador

```bash
export AGENT_RUNTIME_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
python3 -m agent_runtime --propositor eco --porta 8010 --raiz ./tarefas_smoke
```

Guarde o token: o painel vai pedi-lo.

### 2. Suba o dashboard do EDP

```bash
python3 -m edp.serve      # http://127.0.0.1:8000/dashboard
```

### 3. Carregue a extensão e abra o painel

`chrome://extensions` → modo desenvolvedor → *Carregar sem compactação* →
`claude-exporter-v4.2/`. Depois abra o painel do Copiloto (aba própria).

### 4. Descubra o `tabId` do dashboard

No console do painel:

```js
(await chrome.tabs.query({url: 'http://127.0.0.1:8000/*'}))
  .map(t => ({id: t.id, url: t.url}))
```

`tabs.query` aqui é para **descobrir e mostrar a você** — não é o mecanismo de
segurança. Quem autoriza é o registro explícito do passo 5.

### 5. Registre o alvo e ligue a ponte

```js
CopilotBrowserBridge.onEvento((e, d) => console.log('[bridge]', e, d));
CopilotBrowserBridge.start('http://127.0.0.1:8010', 'SEU_TOKEN');
await CopilotBrowserBridge.registrarAlvo(<TAB_ID>);
```

Esperado: `chrome://extensions` mostra a faixa "está depurando este navegador"
sobre a aba do dashboard, e `[bridge] alvo.registrado` no console.

### 6. Submeta a tarefa

```bash
curl -s -X POST http://127.0.0.1:8010/v1/tarefas \
  -H "Authorization: Bearer $AGENT_RUNTIME_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"objetivo":"inspecionar o dashboard do EDP",
       "capacidades":["browser.inspect"],"max_iteracoes":3}'
```

Depois consulte com o `task_id` devolvido:

```bash
curl -s http://127.0.0.1:8010/v1/tarefas/<TASK_ID>/resultado \
  -H "Authorization: Bearer $AGENT_RUNTIME_TOKEN" | python3 -m json.tool
```

---

## Critério de aceite

### Positivo — tem de valer TODOS

```
[ ] status .................. CONCLUIDA
[ ] observacoes ............. 3
[ ] kinds ................... page, dom, history
[ ] page.url ................ http://127.0.0.1:8000/dashboard
[ ] dom.dom_nodes ........... > 0   (o dashboard tem DOM de verdade)
[ ] fonte ................... contem "tab=<TAB_ID>"
[ ] resultado persistido .... ./tarefas_smoke/<TASK_ID>/tarefa.json existe
```

### Negativo — os três, cada um tem de REJEITAR

**N1 — alvo errado.** Com o alvo registrado, no console do painel:

```js
await CopilotController.executar({
  protocol: 'edp.browser.v1', kind: 'capability.request', request_id: 'R-teste',
  capability: 'browser.inspect',
  target: { tab_id: 999999, origin: 'http://127.0.0.1:8000' }})
```
```
[ ] type === "browser.error"  e  error casa /não é o alvo/
[ ] nenhum comando CDP foi para a aba 999999
```

**N2 — a aba mudou de origem depois do registro.** Navegue a aba do dashboard
para `https://example.com` e repita `browser.inspect`:
```
[ ] type === "browser.error"  e  error casa /mudou de origem/
[ ] CopilotController.alvoAtual() === null   (o alvo foi invalidado)
```

**N3 — debugger desanexado.** Clique em *Cancelar* na faixa de depuração do
Chrome (ou `chrome.debugger.detach({tabId})`) e repita:
```
[ ] type === "browser.error"  e  error casa /não está anexado/
```

### Correlação — dois `request_id` simultâneos

Submeta duas tarefas seguidas e confira:
```
[ ] cada task_id recebeu observacoes com o proprio tarefa_id
[ ] nenhum request_id foi atendido duas vezes
```

### Segurança — nada além do contrato atravessa

No JSON do resultado:
```
[ ] nenhuma chave fora de {kind,url,title,dom_nodes,history_len,erro}
[ ] nenhum cookie, authorization, storage ou chave de API
[ ] nenhum objeto Chrome cru (exceptionDetails, backendNodeId, etc.)
```

---

## Como registrar o resultado

Cole a saída dos passos 6 e dos três negativos em
`docs/agent_runtime/RESULTADO_SMOKE_BROWSER_INSPECT.md`, com data e versão do
Chrome. **Enquanto esse arquivo não existir, `browser.inspect` está fechado em
código e teste, e aberto em Chrome real** — e é assim que deve ser descrito.

## O que este smoke NÃO fecha

O Registry não se expande com ele. `browser.click` e as demais continuam
recusadas por `exige_implementada()` e dependem da assinatura de
`DECISAO_ATUACAO.md`. Este procedimento mede **uma** capacidade, de leitura.
