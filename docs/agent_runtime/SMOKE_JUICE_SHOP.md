# Smoke real — `browser.inspect` sobre o OWASP Juice Shop (Bloco B)

**05/09/2026. NÃO EXECUTADO** — este documento é o procedimento; o resultado
vai em `RESULTADO_JUICE_SHOP_INSPECT.md`.

Pré-registro congelado: [`preregistro_juice_shop_inspect.md`](preregistro_juice_shop_inspect.md).
Nada aqui altera hipótese, condições, controle ou critério. Isto é só o **como
armar**, escrito antes para que os erros de procedimento não sejam descobertos
com o Chrome aberto.

## Pré-condição do §1: ATENDIDA

```
node --version   ->  v22.14.0        exigido "22 - 26"   OK   (05/09/2026)
```

A errata do pré-registro dizia para conferir isto **antes de clonar**. Conferido.
Se tivesse dado menor, o bloco pararia aqui — trocar o alvo por um servidor mais
leve seria pré-registro novo, não adaptação.

---

## O que muda em relação ao smoke do Bloco A

`SMOKE_BROWSER_INSPECT.md` é de 03/09 e **precede** dois achados de 05/09. Três
correções, todas medidas:

```
1. --browser NA LINHA DO POWERSHELL
   O documento do Bloco A traz `--browser` só na versão bash. A linha
   PowerShell nao tem. Sem a flag, browser.inspect nao liga e o sintoma so
   aparece la na frente, como alvo que nunca fica operacional.

2. --origem-extensao PASSOU A SER OBRIGATORIA  (decisao de 05/09, 965085f)
   O painel e uma origem chrome-extension://; o Runtime esta em
   http://127.0.0.1:8010. Sem a flag NAO HA CORS e o preflight do painel
   morre. Default continua sendo sem CORS, e `*` continua recusado.

3. A ORDEM DOS PASSOS INVERTEU POR CAUSA DISSO
   `--origem-extensao` e flag de INICIALIZACAO e exige o ID da extensao. O ID
   so existe depois de carregar a extensao. Entao: extensao PRIMEIRO, Runtime
   DEPOIS. O documento do Bloco A faz o contrario.
```

O resto das lições continua valendo e está repetido abaixo para não obrigar a
abrir dois documentos com o Chrome na tela.

---

## Antes de começar

```
[ ] captura de trafego PARADA, ou redacao de headers LIGADA
[ ] a captura NAO aponta para a aba do Runtime (127.0.0.1:8010)
[ ] --raiz proprio: .\tarefas_juice   (separado do Bloco A, exigencia do §7)
```

A captura sobre a aba do Runtime com redação desligada já gravou um
`Authorization: Bearer` em claro neste projeto (04/09). É a lição de #T1.

**Sobre o token exposto:** o `AGENT_RUNTIME_TOKEN` é gerado a cada execução por
`secrets.token_urlsafe(32)` e vive só na variável de ambiente — o servidor
recusa subir sem ele (`transporte.py:180`). Não há token persistido para
"rotacionar": **gerar um novo no passo 2 já é a rotação**, e o valor que
apareceu no transcrito morre por não ser mais usado.

---

## Procedimento

> **UM PASSO POR VEZ, CADA UM NO SEU TERMINAL.** Os passos 1, 2 e 4 sobem
> processos que ocupam o terminal; nenhum deles devolve o prompt. Colar os
> quatro de uma vez faz o `npm start` rodar antes de o build existir, e o
> `run.py serve` e o `agent_runtime` rodarem no diretório errado — foi
> exatamente o que aconteceu em 05/09. Cada passo tem seu `cd`, e ele importa.

### 1. Juice Shop de pé, ANTES de tudo

**FORA da árvore do lab.** Um clone do Juice Shop tem ~850 pacotes em
`node_modules`; dentro do repo ele vira 850 pastas não rastreadas. Já aconteceu
em 05/09 (o `cd` foi esquecido num bloco colado de uma vez) e está coberto por
`juice-shop/` no `.gitignore` do lab — mas a rede de segurança não substitui
instalar no lugar certo.

#### Via oficial: pacote pronto (RECOMENDADA)

Não precisa de build, de npm, nem de compilador. A OWASP publica o binário
empacotado por plataforma e por versão de Node:

```powershell
cd C:\Users\central\Downloads
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
$u = "https://github.com/juice-shop/juice-shop/releases/download/v20.2.0"
Invoke-WebRequest "$u/juice-shop-20.2.0_node22_win32_x64.zip"     -OutFile js.zip     -UseBasicParsing
Invoke-WebRequest "$u/juice-shop-20.2.0_node22_win32_x64.zip.md5" -OutFile js.zip.md5 -UseBasicParsing
```

**A linha do TLS não é supersticão.** O Windows PowerShell 5.1 usa o default do
`ServicePointManager`, que é TLS 1.0/1.1; o GitHub recusa. Sintoma exato,
medido em 05/09: `A solicitação foi anulada: Não foi possível criar um canal
seguro para SSL/TLS`. `$ProgressPreference = 'SilentlyContinue'` é performance
— com a barra de progresso ligada, o 5.1 leva minutos para baixar 120 MB.

Conferência do md5, **em bloco separado**:

```powershell
if (-not (Test-Path js.zip)) {
  "FALHOU: js.zip nao baixou"
} else {
  "tamanho: {0:N1} MB  (esperado ~120,4)" -f ((Get-Item js.zip).Length / 1MB)
  $a = (Get-FileHash js.zip -Algorithm MD5).Hash.ToLower()
  $b = ((Get-Content js.zip.md5 -Raw) -split '\s+')[0].ToLower()
  if ($a -and $b -and $a -eq $b) { "MD5 OK  $a" }
  else { "MD5 FALHOU  local='$a'  publicado='$b'" }
}
```

> **Por que o `-and $a -and $b`, e não só `$a -eq $b`.** A primeira versão
> deste bloco fazia a comparação direta. Com os dois downloads falhados, `$a` e
> `$b` ficaram nulos, `$null -eq $null` deu verdadeiro, e a checagem **imprimiu
> `MD5 OK` sem ter medido nada**. Gate degenerado: passa justamente quando não
> há evidência. O `Test-Path` e os dois testes de não-vazio existem por isso.

Se o TLS continuar recusando (proxy corporativo, .NET antigo), **baixe pelo
navegador** — o Chrome já está aberto de qualquer forma:
`https://github.com/juice-shop/juice-shop/releases/tag/v20.2.0`, asset
`juice-shop-20.2.0_node22_win32_x64.zip`. Depois só a conferência de md5 acima.

Extrair. **Use `tar`, não `Expand-Archive`:**

```powershell
cd C:\Users\central\Downloads
tar --version                       # vem no Win10 1803+, mesma ressalva do curl.exe
mkdir juice_shop_pkg | Out-Null
tar -xf js.zip -C juice_shop_pkg
```

O pacote traz o `node_modules` inteiro — dezenas de milhares de arquivos
pequenos. O `Expand-Archive` do PowerShell 5.1 processa entrada por entrada com
overhead de pipeline e leva **dezenas de minutos**; o `tar` faz o mesmo em uma
fração disso. Medido em 05/09: a primeira tentativa foi de `Expand-Archive` e
travou o passo.

Para ver se está andando, de outro terminal:

```powershell
(Get-ChildItem C:\Users\central\Downloads\juice_shop_pkg -Recurse -File | Measure-Object).Count
```

Se `tar` não existir nesta máquina, o caminho lento funciona igual:

```powershell
cd C:\Users\central\Downloads
Expand-Archive js.zip -DestinationPath juice_shop_pkg -Force
```

Subir, em qualquer um dos dois casos:

```powershell
cd C:\Users\central\Downloads
if (Test-Path juice_shop_pkg\package.json) { cd juice_shop_pkg }
else { cd (Get-ChildItem juice_shop_pkg -Directory | Select-Object -First 1).FullName }
Get-Location
npm start
```

**md5 conferido em 05/09**, contra o publicado pela OWASP:
`1191bb6ed1ab696507bb0b50b27bb7a5`, 120,4 MB.

`node22_win32_x64` casa exatamente com esta máquina (Node v22.14.0, Windows
x64). São 120 MB.

**Por que esta via é melhor aqui, e não só mais fácil:** o repositório do Juice
Shop traz `.npmrc` com `package-lock=false`, na raiz **e** no `frontend`. Sem
lockfile, cada `npm install` resolve a árvore de dependências do zero — duas
instalações da mesma tag podem produzir alvos diferentes. O pacote da release é
um artefato fixo, com md5 publicado. Para um experimento pré-registrado, o
artefato verificável é a escolha certa.

#### Via do fonte (fallback, e o que ela custou)

```powershell
cd C:\Users\central\Downloads
git clone --depth 1 --branch v20.2.0 https://github.com/juice-shop/juice-shop.git
cd juice-shop
npm install        # o postinstall roda o build do frontend + tsc
npm start
```

Tentado em 05/09 nesta máquina e **falhou**. A instalação da raiz foi (846
pacotes), e o `postinstall` morreu no install aninhado do frontend:

```
> cd frontend && npm install && cd .. && npm run build:frontend && ...
npm error Cannot read properties of null (reading 'edgesOut')
```

É bug do arborist do npm (10.9.2), e o `package-lock=false` do projeto o torna
mais provável: sem lock, a árvore é resolvida inteira a cada vez. Se for
insistir por aqui, decomponha o `postinstall` para ver onde quebra de verdade:

```powershell
npm cache clean --force
cd frontend; npm install; cd ..
npm run build:frontend
npm run build:server
```

**Sintoma derivado, para não confundir:** `npm start` depois de um install
falho dá `Cannot find module '...\build\app'`. Não é outro defeito — é a
ausência do build, consequência do erro acima.

**Anote a versão que subir de fato** — ela entra no resultado.

Confirme antes de seguir:

```powershell
(Invoke-WebRequest http://127.0.0.1:3000 -UseBasicParsing).StatusCode   # 200
```

Abra `http://127.0.0.1:3000/#/` numa aba e **espere a página inicial carregar**.
Registrar com a aba ainda em `about:blank` seria recusa certa pelo motivo
errado (§4).

**Sem login.** Autenticar criaria sessão e cookie, e a observação passaria a
poder carregar estado de sessão — fora do que `CAMPOS_OBS` foi desenhado para
levar.

### 2. Dashboard do EDP de pé

```powershell
cd C:\Users\central\Downloads\edp_v5_main
python run.py serve          # http://127.0.0.1:8000/dashboard
```

`run.py serve`, **não** `-m edp.serve` — não existe `edp/serve.py`.

### 3. Extensão carregada, e o ID anotado

`chrome://extensions` → modo desenvolvedor → *Carregar sem compactação* →
`claude-exporter-v4.2/`. Abra o painel do Copiloto.

No console do painel (`F12` → Console):

```js
chrome.runtime.id        // anote: vai na flag do passo 4
```

### 4. Runtime, com as duas flags

```powershell
cd C:\Users\central\Downloads\lab_edp_novo
$env:AGENT_RUNTIME_TOKEN = (python -c "import secrets;print(secrets.token_urlsafe(32))")
$env:AGENT_RUNTIME_TOKEN     # anote: o painel vai pedir

python -m agent_runtime --propositor eco --porta 8010 --browser `
  --origem-extensao chrome-extension://COLE_O_ID_DO_PASSO_3 `
  --raiz .\tarefas_juice
```

Sem barra no fim da origem — o parser recusa o que não casar exatamente.

O Runtime ocupa o terminal. Abra **outro** e redefina
`$env:AGENT_RUNTIME_TOKEN` com o mesmo valor: variável de ambiente não
atravessa terminais.

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health      # nao exige token
```

### 5. Descubra os dois tabId

No console do painel:

```js
(await chrome.tabs.query({url: ['http://127.0.0.1:3000/*',
                                'http://127.0.0.1:8000/*']}))
  .map(t => ({id: t.id, url: t.url}))
```

Anote os dois: `TAB_JS` e `TAB_DASH`. Os dois são necessários — o desenho exige
o cruzamento nos dois sentidos.

### 6. Registre o Juice Shop como alvo

**Onde colar:** console do DevTools da aba do painel. **NÃO** no campo de chat
do Copiloto — ele é um LLM, não executa JavaScript, e o que for colado lá vira
texto guardado no log.

**Qual token:** o `AGENT_RUNTIME_TOKEN` do passo 4, string sem prefixo.
**NÃO é a chave da Anthropic.** Uma `sk-ant-` colada aqui não funciona e terá
sido exposta à toa.

```js
CopilotBrowserBridge.onEvento((e, d) => console.log('[bridge]', e, d));
CopilotBrowserBridge.start('http://127.0.0.1:8010', 'COLE_O_AGENT_RUNTIME_TOKEN');
await CopilotBrowserBridge.registrarAlvo(TAB_JS);
```

Esperado: `[bridge] alvo.registrado` → `[bridge] alvo.anexado`, e a faixa "está
depurando este navegador" sobre a aba do **Juice Shop**.

```powershell
$h = @{ Authorization = "Bearer $env:AGENT_RUNTIME_TOKEN"
        'Content-Type' = 'application/json' }
Invoke-RestMethod http://127.0.0.1:8010/v1/browser/alvo -Headers $h
```

Tem de vir `ANEXADO` / `operacional: True`, com a origin do Juice Shop.
**Se `operacional` for `false`, pare.** Tarefa submetida antes disso não conclui
— e esse é o comportamento correto (`AlvoNaoOperacional: alvo em REGISTRADO`).

### 7. `js_positivo`

```powershell
$body = @{ objetivo = "inspecionar a pagina inicial do Juice Shop"
           capacidades = @("browser.inspect")
           max_iteracoes = 3 } | ConvertTo-Json

$r = Invoke-RestMethod http://127.0.0.1:8010/v1/tarefas -Method Post -Headers $h -Body $body
$r.task_id

Invoke-RestMethod "http://127.0.0.1:8010/v1/tarefas/$($r.task_id)/resultado" `
  -Headers $h | ConvertTo-Json -Depth 6
```

Enquanto não terminar, `/resultado` devolve **409** — esperado, e o PowerShell
mostra como erro. Para acompanhar sem susto:

```powershell
Invoke-RestMethod "http://127.0.0.1:8010/v1/tarefas/$($r.task_id)" -Headers $h |
  Select-Object status, terminal, iteracoes, motivo_parada, erro
```

`erro` é o serviço ter quebrado; `motivo_parada` é a tarefa ter parado por um
motivo. Olhar só `erro` faz parecer falha sem razão.

### 8. `js_cruzado` — o controle que o Bloco A não conseguiu fazer

Com o **Juice Shop** ainda registrado, no console do painel:

```js
await CopilotController.executar({
  protocol: 'edp.browser.v1', kind: 'capability.request', request_id: 'R-cruz-1',
  capability: 'browser.inspect',
  target: { tab_id: TAB_DASH, origin: 'http://127.0.0.1:8000' }})
```

Esperado: `type === "browser.error"`, mensagem casando `/não é o alvo/`.

### 9. `dash_cruzado` — o mesmo, ao contrário

```js
await CopilotBrowserBridge.registrarAlvo(TAB_DASH);
// esperar alvo.anexado
await CopilotController.executar({
  protocol: 'edp.browser.v1', kind: 'capability.request', request_id: 'R-cruz-2',
  capability: 'browser.inspect',
  target: { tab_id: TAB_JS, origin: 'http://127.0.0.1:3000' }})
```

Esperado: `browser.error`, `/não é o alvo/`.

**Por que os dois sentidos:** os dois alvos são loopback e os dois são "locais".
Se qualquer um passar, o escopo é por "é local" e não por aba — e aí **nenhum
achado do positivo é afirmado**, a restrição é reescrita antes de qualquer
outra coisa.

---

## Critério de aceite — §6 do pré-registro, sem reinterpretação

```
js_positivo
  [ ] status .............. CONCLUIDA
  [ ] n_observacoes ....... 3
  [ ] kinds ............... page, dom, history
  [ ] url_bate ............ page.url comeca com http://127.0.0.1:3000
  [ ] dom_nodes_js ........ > 0
  [ ] razao_dom ........... dom_nodes_js / 327 > 2   ou seja  > 654 nos
                            (327 = dom_nodes do dashboard, Bloco A, T-612fc612)
  [ ] tempo_inspect ....... < 10000 ms
  [ ] campos_extra ........ vazio  (nada fora de
                            {kind,url,title,dom_nodes,history_len,erro})
  [ ] persistido .......... .\tarefas_juice\<TASK_ID>\tarefa.json existe

js_cruzado    [ ] REJEITADO  /nao e o alvo/
dash_cruzado  [ ] REJEITADO  /nao e o alvo/
```

**Qualquer rejeição cruzada que falhe ⇒ FALHA, e o positivo é descartado junto.**

**`razao_dom <= 2` não é FALHA automática, é INVESTIGAÇÃO.** Pode ser o SPA
renderizando pouco antes do carregamento completo. Registra-se o número e a
hipótese, nenhum achado sobre tamanho é afirmado, e as demais linhas continuam
valendo.

**H0 é resultado provável e válido.** `depth: -1` pede a árvore inteira; num SPA
real pode estourar tempo, memória ou algum limite do canal. Se estourar, o
achado é que `browser.inspect` precisa de teto de profundidade ou tamanho — e
esse teto vira constante congelada de um pré-registro **novo**, não ajuste
silencioso deste.

---

## O que este procedimento NÃO autoriza

Clicar, preencher, navegar, executar JS, ou exercitar qualquer vulnerabilidade
do Juice Shop. Isso é L1, está em `preregistro_atuacao_L1_vertical.md`, e
depende da assinatura de `DECISAO_ATUACAO.md`.

`browser.inspect` continua L0 pela mesma razão de sempre: a expressão enviada a
`Runtime.evaluate` é **fixa no provider** (`EXPR_PAGINA`, constante em
`debugger_controller.js`). No dia em que ela virar string vinda do modelo, a
classificação muda no mesmo commit.
