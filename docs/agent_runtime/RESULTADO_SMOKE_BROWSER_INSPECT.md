# Resultado — `browser.inspect` contra Chrome real

**05/09/2026.** Executado no host Windows, Chrome com a extensão carregada sem
compactação. Pré-registro:
[`preregistro_smoke_browser_inspect.md`](preregistro_smoke_browser_inspect.md).

## Cronologia — UMA execução, não duas

Este resultado vem de **uma única sessão contínua**. Registrado explicitamente
porque um auditor lendo cortes do transcrito leu como duas rodadas
independentes, e concluiu que a segunda teria N2 reaberto e N3 ausente. Não
houve segunda rodada.

```
05:58-06:04  correcoes do procedimento (run.py serve, Invoke-RestMethod)
06:49        204 sem corpo          <- BLOQUEIO, achado tentando comecar
07:23        CORS de origem exata   <- BLOQUEIO, idem
             ---- so aqui o smoke pode rodar ----
11:32 (*)    positivo T-612fc612
11:53        N1 invalido (painel recarregado; alvo perdido)
11:59        N1 valido      "tab_id 999999 nao e o alvo"
12:00        N2 invalido (a aba nunca navegou)
12:04        N2 valido      "a aba alvo mudou de origem desde o registro"
12:08        N3 valido      "o debugger nao esta anexado ao alvo"
08:16        #T3 fechada, este documento escrito

(*) horarios 11:xx/12:xx sao do console do Windows; os 0x:xx sao dos commits
    na VM. Fusos diferentes, mesma sessao.
```

O `204` e o CORS **não são de uma rodada posterior**: são os bloqueios que
impediam o smoke de começar. E o ensaio com dois pollers concorrentes
(`buscado_em` sob HTTP real) rodou **antes** do Chrome, na VM, como preparação
— não é evidência posterior.

## Veredito: **H1**

Os oito critérios do positivo e os três negativos, todos verdadeiros. Nenhuma
linha do critério §6 foi reaberta depois de ver o dado.

---

## Ambiente

```
Runtime ......... python -m agent_runtime --propositor eco --porta 8010
                  --browser --origem-extensao chrome-extension://<id>
                  --raiz .\tarefas_smoke
dashboard ....... python run.py serve        http://127.0.0.1:8000/dashboard
extensao ........ claude-exporter-v4.2, carregada sem compactacao
aba-alvo ........ tab_id 1824677635
sessao .......... S-4c1j0y16
```

## Ciclo de vida do alvo

```
[bridge] alvo.registrado  {tabId: 1824677635, origin: 'http://127.0.0.1:8000'}
[bridge] alvo.anexado     {..., operacional: true}
```

`REGISTRADO → ANEXANDO → ANEXADO` contra `chrome.debugger.attach` real. A faixa
de depuração do Chrome apareceu sobre a aba do dashboard.

## Positivo — `T-612fc612`

```
[bridge] pedido    capability: browser.inspect · request_id: R-b89da848d223
                   target: {tab_id: 1824677635, origin: 'http://127.0.0.1:8000'}
[bridge] resultado request_id: R-b89da848d223 · aceito: true · status: 200
```

| critério (§6) | esperado | medido | |
|---|---|---|---|
| `status` | `CONCLUIDA` | `CONCLUIDA` | ✔ |
| `n_observacoes` | 3 | 3 | ✔ |
| `kinds` | page, dom, history | page, dom, history | ✔ |
| `url_bate` | `.../dashboard` | `http://127.0.0.1:8000/dashboard` | ✔ |
| `dom_nodes` | > 0 | **327** | ✔ |
| `fonte_bate` | `tab=<ID>` nas 3 | `chrome.debugger tab=1824677635` | ✔ |
| `persistiu` | sim | lido de `/resultado` | ✔ |
| `campos_extra` | vazio | vazio | ✔ |

```json
{"kind": "page", "url": "http://127.0.0.1:8000/dashboard",
 "title": "EDP v3.5 — Cognitive Runtime"}     hash 13d27dae77b67b07
{"kind": "dom", "dom_nodes": 327}             hash 79711f00913f6a9b
{"kind": "history", "history_len": 2}         hash f189d472a8b6e2bc
```

`iteracoes: 1` · `negadas: []` · `duracao_ms: 575.85` ·
`correlation_id: pagina-1788607967839`

`dom_nodes: 327` é a contagem real da árvore, de `DOM.getDocument` com
`depth: -1`. `history_len: 2` corresponde às duas navegações daquela aba.

## Negativos — os três rejeitaram, com motivos distintos

| | condição | mensagem medida |
|---|---|---|
| **N1** | `tab_id` 999999, alvo válido e anexado | `tab_id 999999 não é o alvo (1824677635)` |
| **N2** | aba navegada para `https://example.com` | `a aba alvo mudou de origem desde o registro` |
| **N3** | `chrome.debugger.detach` por fora | `o debugger não está anexado ao alvo` |

Cada uma nomeia seu próprio motivo. Se as três dissessem a mesma coisa, o
positivo não seria interpretável — não daria para saber por qual razão ele foi
aceito.

**N1 é o controle de validade do §3.** Ele rodou com alvo operacional, e
mesmo assim recusou sem que comando CDP nenhum saísse. Sem isso, as três
observações do positivo poderiam ter vindo de qualquer aba.

**N2** foi executado duas vezes. A primeira **não conta**: a aba nunca havia
navegado (`chrome.tabs.get(...).url` ainda era o dashboard), então o teste
mediu outra coisa e devolveu observação. Registrado aqui porque a primeira
leitura foi "N2 falhou" e a correção foi do *teste*, não do código — a
distinção importa para quem ler depois. A segunda execução, com
`chrome.tabs.update` e URL confirmada em `example.com`, rejeitou.

---

## O que este smoke encontrou, e nenhum teste tinha encontrado

### 1. `204` com corpo — `GET /v1/browser/solicitacoes`

`JSONResponse(None)` serializa `null`, 4 bytes, num status que exige corpo
vazio. O uvicorn levanta `Response content longer than Content-Length` e
**derruba a requisição**; no painel isso chega como `ERR_CONNECTION_REFUSED`.
O operador desligou o Runtime achando que o problema era ele.

`TestClient` fala ASGI direto — sem protocolo HTTP, sem `Content-Length`, sem
uvicorn. A classe inteira "válido como objeto ASGI, inválido como HTTP"
passava batida. Corrigido em `fe9aae9`, com `tests/test_http_real.py` subindo
uvicorn de verdade.

### 2. CORS ausente para a origem do painel

`DECISAO_TRANSPORTE.md` previu isto por escrito em 03/09 e mandou que fosse
decisão com nome e escopo. Eu construí o bridge dentro do painel e mandei
usá-lo lá, pulando a decisão. Sete `OPTIONS 401` no log: preflight nunca
carrega credencial, e o middleware exigia token antes de qualquer CORS existir.

Corrigido em `cd8f836`: preflight respondido antes da autenticação (sem
dispensar token na requisição real, com teste próprio), e CORS só para **uma
origem exata**, com `*` e padrões recusados no arranque.

### 3. Sessão do debugger pendurada após invalidação

Depois do N2, o Chrome continuava anexado. `conferirAlvo` chamava
`limparAlvo()` sem `detach`, e `desanexar()` retornava cedo porque `alvo` já
era `null`. O registro seguinte falhou com
`Another debugger is already attached to the tab`.

Uma sessão anexada que ninguém rastreia é uma capacidade viva fora do
registro — o oposto do que o escopo de aba existe para garantir. Corrigido com
`invalidaAlvo()`, mais três testes no arnês de node (18 checagens agora).

### 4. Duas guardas de usabilidade

`registrarAlvo()` antes de `start()` montava `null/v1/browser/alvo` e o erro
chegava como falha de rede; e `registrarAlvo("T-...")` com um `task_id` no
lugar do `tabId` morria dentro de `chrome.tabs.get`. Ambas recusam cedo agora,
com o motivo certo.

### 5. Um falso positivo do meu próprio diagnóstico

O `title` apareceu como `EDP v3.5 â Cognitive Runtime` no PowerShell, e eu
levantei suspeita de corrupção atravessando a fronteira da observação. Lido
pelo console do navegador, é `EDP v3.5 — Cognitive Runtime`. Era encoding do
console, não dado. Registrado porque a suspeita foi publicada.

---

## O que continua NÃO provado

```
browser.click e demais L1/L2 ..... nao implementadas; exige_implementada()
                                   recusa, e a assinatura de DECISAO_ATUACAO.md
                                   continua em branco
Juice Shop ....................... preregistro_juice_shop_inspect.md, nao
                                   executado. E o unico teste que separa
                                   "escopo por aba" de "escopo por ser local":
                                   aqui so havia uma aba loopback.
--propositor llm ................. recusa subir; o laco nunca rodou com modelo
                                   real
```

## Higiene

O token usado neste smoke foi exposto no transcrito da sessão e **deve ser
rotacionado**. Ver `DIVIDAS_TRANSPORTE.md` #T1 para o incidente anterior, de
mecanismo diferente e mesma consequência.
