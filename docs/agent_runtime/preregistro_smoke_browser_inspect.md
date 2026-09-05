# Pré-registro — `browser.inspect` contra Chrome real

## `chrome.debugger`, dirigido pelo Agent Runtime através do canal do painel, produz observação estruturada da aba-alvo registrada — e recusa toda aba que não seja ela?

> **Régua da Bancada (método):** este documento declara hipótese, condições,
> critério de aceite e constantes **ANTES de qualquer execução em Chrome
> real**. A encarnação (`agent_runtime/provedores/browser.py`,
> `copilot/debugger_controller.js`, `copilot/browser_bridge.js`) já existe e
> está congelada nos commits citados na §3. **Congela ao primeiro disparo
> real.** Se um defeito invalidar o desenho, o certo é um pré-registro novo,
> não editar este depois de ver o resultado.

**Data de pré-registro: 2026-09-05** (antes do primeiro disparo em Chrome).

---

## 1. Motivação / contexto provado

Tudo abaixo é medição ou leitura de código com referência, não suposição.

**O que já está provado, e por qual teste:**

```
provedor: alvo, recusas, normalizacao ....... 24 testes  tests/test_browser_provider.py
mesa: correlacao, concorrencia, TTL ......... 21 testes  tests/test_canal_browser.py
endpoints + laco ate tarefa persistida ...... 23 testes  tests/test_canal_http.py
controller REAL sob `chrome` simulado ....... 15 checks  tests/js/test_controller.mjs
suite do lab inteira ........................ 585 passed (05/09/2026)
```

`tests/js/test_controller.mjs` carrega
`sf_exportador/claude-exporter-v4.2/copilot/debugger_controller.js` **real**
num `vm` do node com um objeto `chrome` falso, e cobre os três negativos.

**O que nenhum deles prova:** que `chrome.debugger.sendCommand` de verdade
devolve o que o controller espera. Todo o `chrome` desses testes é escrito por
mim; um erro de premissa sobre a API real passaria por todos eles.

**Por que não foi executado antes:** não há Chrome nem Chromium na máquina de
desenvolvimento (`command -v google-chrome chromium chromium-browser` → vazio);
o Firefox presente não implementa `chrome.debugger`. O host Windows tem Chrome.

**Commits que congelam a encarnação:**

```
079128a  browser.inspect: vertical slice
9158d2a  canal: mesa, endpoints, laco completo
33b8b8c  alvo: o registrado pelo endpoint passa a ser o que a tarefa usa
77db6d6  --browser no ponto de entrada
e709528  smoke: qual token, onde colar, captura desligada
```

---

## 2. Hipótese e predições

**H1 —** O caminho completo funciona contra Chrome real: uma `Tarefa` com
`capacidades: ["browser.inspect"]` produz **3 observações** (`page`, `dom`,
`history`) vindas de `chrome.debugger`, com `page.url` igual à URL da aba
registrada, e a tarefa termina `CONCLUIDA` com resultado persistido.

**H0 —** O caminho falha contra Chrome real por alguma premissa errada sobre a
API — formato de retorno de `DOM.getDocument`, `Runtime.evaluate` com
`returnByValue`, `Page.getNavigationHistory`, ou o comportamento de
`getTargets()`.

**H0 vencer é achado válido, e é o resultado mais informativo dos dois.** Ele
localiza exatamente onde o `chrome` simulado dos testes diverge do real — que é
a única informação que 585 testes não conseguem produzir. Nesse caso o
resultado vai para `RESULTADO_SMOKE_BROWSER_INSPECT.md` com a divergência
nomeada, e o arnês `test_controller.mjs` é corrigido para refletir a API
verdadeira **antes** de qualquer nova tentativa.

---

## 3. Condições / desenho

| rótulo | papel |
|---|---|
| `positivo` | aba do dashboard registrada e `ANEXADO`; espera-se observação |
| `N1_alvo_errado` | pedido com `tab_id` que não é o registrado |
| `N2_origem_mudou` | aba navegada para outra origem **depois** do registro |
| `N3_desanexado` | debugger desanexado à mão antes do pedido |
| `N4_sem_attach` | alvo `REGISTRADO` mas nunca `ANEXADO` |
| `correlacao` | duas tarefas seguidas, um painel só atendendo |

**Controle negativo de validade:** `N1`. Se `N1` **produzir observação**, o
escopo de aba não existe — e nesse caso **nenhum achado do positivo é
afirmado**, porque a observação do positivo poderia ter vindo de qualquer aba.
`N1` passar é pré-condição para o positivo significar alguma coisa.

---

## 4. Dataset (CONGELADO)

Não há dataset de queries: o "dado" é o estado de duas abas.

```
aba-alvo ......... http://127.0.0.1:8000/dashboard   (dashboard do EDP v3.5)
aba-intrusa ...... qualquer origem NAO-loopback, para N2
                   (ex.: https://example.com — escolhida por ser estavel
                    e sem login)
tab_id ........... descoberto em runtime; anotado no resultado
task_id .......... gerado pelo Runtime; anotado no resultado
```

**Pendência resolvida antes de armar:** o dashboard precisa estar servindo
antes do registro do alvo, senão `chrome.tabs.get` devolve URL `about:blank` e
o registro é recusado por não ser loopback — o que seria uma recusa **certa
pelo motivo errado**, e confundiria o resultado de `N2`.

---

## 5. Métricas

Não são estatísticas — são verificações binárias. Cada uma tem uma fonte
única e verificável.

| métrica | fórmula / origem | onde ler |
|---|---|---|
| `n_observacoes` | `len(resultado.observacoes)` | `GET /v1/tarefas/{id}/resultado` |
| `kinds` | `{o.dados.kind}` | idem |
| `url_bate` | `page.url == "http://127.0.0.1:8000/dashboard"` | idem |
| `dom_nodes` | `dom.dom_nodes` | idem |
| `fonte_bate` | `"tab=<TAB_ID>" in o.fonte` | idem |
| `persistiu` | existe `tarefas_smoke/<TASK_ID>/tarefa.json` | disco |
| `rejeitou_N` | `type == "browser.error"` e a regex da linha | console do painel |
| `sem_cdp_em_N1` | nenhum comando foi para a aba errada | console do painel |
| `campos_extra` | chaves fora de `{kind,url,title,dom_nodes,history_len,erro}` | JSON do resultado |

Agregação: **conjunção**. Todas as do positivo têm de valer, e todas as dos
negativos têm de rejeitar. Não há média, não há tolerância, não há "quase".

---

## 6. Critério de decisão (PASSA / FALHA)

**PASSA H1 se, e somente se, todas as linhas abaixo forem verdadeiras:**

```
POSITIVO
  status ............. == "CONCLUIDA"
  n_observacoes ...... == 3
  kinds .............. == {page, dom, history}
  url_bate ........... True
  dom_nodes .......... > 0
  fonte_bate ......... True para as 3
  persistiu .......... True

NEGATIVOS
  N1 ................. browser.error, /não é o alvo/, e sem_cdp_em_N1 == True
  N2 ................. browser.error, /mudou de origem/, alvoAtual() == null
  N3 ................. browser.error, /não está anexado/
  N4 ................. tarefa NAO conclui; motivo_parada cita AlvoNaoOperacional

CORRELACAO
  cada task_id recebeu observacoes com o proprio tarefa_id
  nenhum request_id atendido duas vezes

SEGURANCA
  campos_extra ....... vazio
  nenhum cookie/authorization/storage/chave no JSON
  nenhum objeto Chrome cru (exceptionDetails, backendNodeId, ...)
```

**Qualquer linha falsa ⇒ FALHA, e H0 é o resultado.** O critério não é
reaberto depois de ver o dado. Se um defeito invalidar o desenho, é um
pré-registro novo — não uma edição deste.

**O que PASSA autoriza:** fechar `#T3`, marcar `CHECKLIST_TRANSPORTE.md §5`, e
escrever `RESULTADO_SMOKE_BROWSER_INSPECT.md`. **Não autoriza** nenhuma
capacidade nova: `browser.click` continua dependendo da assinatura de
`DECISAO_ATUACAO.md`.

---

## 7. Anti-mock e isolamento

**O mecanismo é real, e é essa a razão de o smoke existir.** Nada de
`chrome` simulado aqui:

```
chrome.debugger.attach       chamado por copilot/debugger_controller.js:anexar
chrome.debugger.sendCommand  copilot/debugger_controller.js:comando
chrome.debugger.getTargets   copilot/debugger_controller.js:conferirAlvo
chrome.tabs.get              idem
ChromeDebuggerProvider       agent_runtime/provedores/browser.py
MesaDeSolicitacoes           agent_runtime/canal.py
TaskService                  agent_runtime/servico.py
```

**Isolamento — o que este smoke NÃO pode tocar:**

```
[ ] o store de producao do EDP        `--raiz .\tarefas_smoke`, diretorio proprio
[ ] a aba autenticada de claude.ai    registro recusa origem nao-loopback
[ ] qualquer aba fora do alvo         N1 existe para provar isso
[ ] a rede                            bind 127.0.0.1; `roda()` recusa outro host
```

**Verificação de no-leak:** ao fim, `tarefas_smoke/` contém **apenas** os
`task_id` gerados neste smoke, e nada foi escrito em `edp_data`. Conferir por
listagem, não por confiança.

**Higiene de credencial (aprendida em `#T1`):** captura de tráfego parada ou
com redação ligada durante todo o smoke. O token do Runtime é gerado para
**esta** sessão e descartado depois.

---

## 8. Constantes congeladas

| constante | valor | onde vive |
|---|---|---|
| `PROTOCOLO` | `edp.browser.v1` | `browser.py`, `debugger_controller.js` |
| `COMANDOS_INSPECT` | `Page.getNavigationHistory`, `DOM.getDocument`, `Runtime.evaluate` | `browser.py:COMANDOS_INSPECT` |
| `EXPR_PAGINA` | `({url: location.href, title: document.title})` | `debugger_controller.js` |
| `PROTOCOL_VERSION` (CDP) | `1.3` | `debugger_controller.js` |
| `TIMEOUT_MS` (controller) | `10000` | `debugger_controller.js` |
| `TETO_BYTES` | `65536` | `transporte.py` |
| `TETO_SEGUNDOS` | `300.0` | `transporte.py` |
| `MAX_PENDENTES` | `64` | `canal.py` |
| `TTL_S` (mesa) | `120.0` | `canal.py` |
| `POLL_MS` / `POLL_ERRO_MS` | `800` / `4000` | `browser_bridge.js` |
| porta do Runtime | `8010` | assinatura de `DECISAO_TRANSPORTE.md` |
| porta do dashboard | `8000` | do EDP |
| teto de nível | `L0 OBSERVAR` | `Politica(nivel_maximo=Nivel.OBSERVAR)` |
| `CAMPOS_OBS` | `{kind,url,title,dom_nodes,history_len,erro}` | `browser.py` |

**Mudou qualquer uma destas ⇒ é outro pré-registro.**

---

## 9. Procedimento

Passo a passo executável, com as duas formas de shell:
[`SMOKE_BROWSER_INSPECT.md`](SMOKE_BROWSER_INSPECT.md).
Checklist marcável: [`CHECKLIST_EXECUCAO.md`](CHECKLIST_EXECUCAO.md) Bloco A.

---

## 10. Onde o resultado vai

`docs/agent_runtime/RESULTADO_SMOKE_BROWSER_INSPECT.md`, com:

```
[ ] data e versao do Chrome
[ ] a saida de cada linha da secao 6, verdadeira ou falsa
[ ] o JSON do resultado da tarefa, integral
[ ] a saida do console para cada negativo
[ ] veredito: H1 ou H0
[ ] se H0: qual premissa sobre a API do Chrome estava errada, e a correcao
    correspondente em tests/js/test_controller.mjs
```

Enquanto esse arquivo não existir, a descrição correta de `browser.inspect`
continua sendo **"fechado em código e teste, aberto em Chrome real"**.
