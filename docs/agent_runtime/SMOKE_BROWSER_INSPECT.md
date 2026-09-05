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

## Antes de começar: desligue a captura de tráfego

O painel tem uma opção **"gravar Authorization/Cookie/tokens sem redigir"**. Se
ela estiver ligada e a captura apontada para a aba do Runtime
(`http://127.0.0.1:8010/`), o HAR grava o `Authorization: Bearer <token>` em
claro dentro do IndexedDB da extensão.

```
[ ] captura parada, OU redação de headers LIGADA
[ ] a captura não está apontada para a aba do Runtime
```

Isso já aconteceu uma vez neste projeto (04/09/2026): a captura ficou 294 s
sobre `127.0.0.1:8010` com redação desligada. Se acontecer, pare a captura,
apague a sessão, e **troque o token do Runtime** — ele está no HAR.

## Antes de começar: este smoke roda no Windows

A máquina que tem Chrome é o host Windows, e lá o shell é PowerShell. **`curl`
no PowerShell é alias de `Invoke-WebRequest`, que não aceita `-H`** — use
`curl.exe` (existe no Windows 10+) ou `Invoke-RestMethod`. Variável de
ambiente é `$env:NOME`, não `$NOME`.

Os comandos abaixo vêm nas duas formas. Erre isto e o sintoma é
`Não é possível associar o parâmetro 'Headers'` — que é erro de shell, não do
Runtime.

## Procedimento

### 1. Suba o Runtime com o provedor de navegador

**PowerShell** (no diretório do `lab_edp_novo`):

```powershell
$env:AGENT_RUNTIME_TOKEN = (python -c "import secrets;print(secrets.token_urlsafe(32))")
$env:AGENT_RUNTIME_TOKEN     # anote: o painel vai pedir
python -m agent_runtime --propositor eco --porta 8010 --raiz .\tarefas_smoke
```

**bash:**

```bash
export AGENT_RUNTIME_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
python3 -m agent_runtime --propositor eco --porta 8010 --browser --raiz ./tarefas_smoke
```

O Runtime ocupa o terminal. Abra **outro** para os passos seguintes — e nele
defina `$env:AGENT_RUNTIME_TOKEN` de novo com o mesmo valor, porque variável de
ambiente não atravessa terminais.

### 2. Suba o dashboard do EDP

```powershell
cd C:\Users\central\Downloads\edp_v5_main
python run.py serve      # http://127.0.0.1:8000/dashboard
```

**`run.py serve`, não `-m edp.serve`.** Não existe `edp/serve.py`; o ponto de
entrada é `run.py`, documentado na linha 5 do próprio arquivo
(`python run.py serve → inicia API FastAPI`). `serve` é o default, então
`python run.py` sozinho faz o mesmo.

Confirmação de que subiu:

```
[serve] usando edp.api.main:app
[serve] http://127.0.0.1:8000
[serve] dashboard:  http://127.0.0.1:8000/dashboard
```

### 2b. Confira que os dois estão de pé

```powershell
curl.exe -s http://127.0.0.1:8010/health
curl.exe -s -o NUL -w "dashboard %{http_code}`n" http://127.0.0.1:8000/dashboard
```

`/health` não exige token — se ele não responder, o Runtime não subiu, e nada
adiante vai funcionar.

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

**Onde colar:** no **console do DevTools** da aba do painel (`F12` → Console).
NÃO no campo de chat do Copiloto — o Copiloto é um LLM, não executa JavaScript,
e o que você colar lá vira texto guardado no log dele.

**Qual token:** o `AGENT_RUNTIME_TOKEN` que o passo 1 gerou — uma string de
`secrets.token_urlsafe(32)`, sem prefixo. **NÃO é a chave da Anthropic.** A
chave do provedor (`sk-ant-...`) não tem nenhuma relação com este transporte:
ela fica em `chrome.storage.local` para o Copiloto falar com o modelo, e o
Runtime nunca a vê nem a pede.

Se você colar uma chave `sk-ant-` aqui, ela não vai funcionar — e vai ter sido
exposta à toa.

```js
CopilotBrowserBridge.onEvento((e, d) => console.log('[bridge]', e, d));
CopilotBrowserBridge.start('http://127.0.0.1:8010', 'COLE_O_AGENT_RUNTIME_TOKEN');
await CopilotBrowserBridge.registrarAlvo(<TAB_ID>);
```

O ciclo é explícito, e o Runtime só considera o alvo operacional no fim dele:

```
REGISTRADO  ->  ANEXANDO  ->  ANEXADO
                       \->  FALHOU   (remove o alvo)
```

Esperado no console: `[bridge] alvo.registrado` e depois `[bridge] alvo.anexado`
com `operacional: true`. E `chrome://extensions` mostra a faixa "está depurando
este navegador" sobre a aba do dashboard.

Confira pelo Runtime:

```powershell
curl.exe -s http://127.0.0.1:8010/v1/browser/alvo `
  -H "Authorization: Bearer $env:AGENT_RUNTIME_TOKEN"
# {"estado":"ANEXADO","operacional":true}
```

Ou nativo, que já formata a saída:

```powershell
$h = @{ Authorization = "Bearer $env:AGENT_RUNTIME_TOKEN" }
Invoke-RestMethod http://127.0.0.1:8010/v1/browser/alvo -Headers $h | ConvertTo-Json
```

**Se `operacional` for `false`, pare aqui.** Uma tarefa submetida antes disso
não conclui — e é esse o comportamento correto.

### 6. Submeta a tarefa

**PowerShell** — nativo, porque escapar JSON em `curl.exe` no PowerShell é
fonte garantida de erro:

```powershell
$h = @{ Authorization = "Bearer $env:AGENT_RUNTIME_TOKEN"
        'Content-Type' = 'application/json' }
$body = @{ objetivo = "inspecionar o dashboard do EDP"
           capacidades = @("browser.inspect")
           max_iteracoes = 3 } | ConvertTo-Json

$r = Invoke-RestMethod http://127.0.0.1:8010/v1/tarefas -Method Post `
       -Headers $h -Body $body
$r.task_id
```

Depois, o resultado:

```powershell
Invoke-RestMethod "http://127.0.0.1:8010/v1/tarefas/$($r.task_id)/resultado" `
  -Headers $h | ConvertTo-Json -Depth 6
```

Enquanto a tarefa não terminar, esse endpoint devolve **409** — é o esperado, e
o PowerShell mostra isso como erro. Para acompanhar sem susto:

```powershell
Invoke-RestMethod "http://127.0.0.1:8010/v1/tarefas/$($r.task_id)" `
  -Headers $h | Select-Object status, terminal, iteracoes
```

**bash:**

```bash
curl -s -X POST http://127.0.0.1:8010/v1/tarefas \
  -H "Authorization: Bearer $AGENT_RUNTIME_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"objetivo":"inspecionar o dashboard do EDP",
       "capacidades":["browser.inspect"],"max_iteracoes":3}'

curl -s http://127.0.0.1:8010/v1/tarefas/<TASK_ID>/resultado \
  -H "Authorization: Bearer $AGENT_RUNTIME_TOKEN" | python3 -m json.tool
```

---

## Onde ler o motivo de uma falha

`erro` e `motivo_parada` são campos diferentes de propósito:

```
erro ............ o SERVICO quebrou (excecao que escapou do executor)
motivo_parada ... a TAREFA parou por um motivo (alvo ausente, orcamento,
                  politica negou)
```

Uma tarefa `FALHA` por falta de alvo traz `erro: null` e a explicação em
`motivo_parada`. Olhar só `erro` faz parecer que falhou sem razão — eu mesmo
caí nisso ao testar a flag. Verificação rápida:

```powershell
$t = Invoke-RestMethod "http://127.0.0.1:8010/v1/tarefas/$($r.task_id)" -Headers $h
$t | Select-Object status, motivo_parada, erro
```

Sem alvo registrado, o esperado é exatamente:

```
status        : FALHA
motivo_parada : AlvoNaoOperacional: nenhum alvo registrado para 'default'...
erro          :
```

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
