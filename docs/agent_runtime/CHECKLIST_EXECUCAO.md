# Checklist de execução — tudo que ficou pendente

**05/09/2026.** Varredura da conversa inteira, sem tirar nada. Cada item foi
conferido contra o código ou contra `git` no momento em que este documento foi
escrito; nenhum número é de memória.

Ordem: o que **destrava outros itens** vem primeiro. Itens que dependem só de
uma assinatura estão marcados `[ASSINATURA]` e não têm passo a passo de
implementação — passo a passo para eles seria fingir que a decisão é técnica.

**Estado medido em 05/09/2026:**

```
lab_edp_novo ......... 585 passed        55 commits nao enviados
edp_v5 ............... 448 passed, 1 desel.  11 commits nao enviados
sf_exportador ........ sem upstream configurado
decisoes em branco ... 3 (RANKING, ACOPLAMENTO, ATUACAO)
```

---

## BLOCO A — `browser.inspect` em Chrome real

O único item entre a frente do transporte e "fechada". Nada de capacidade nova
entra antes dele. Pré-registro:
[`preregistro_smoke_browser_inspect.md`](preregistro_smoke_browser_inspect.md).

### A.1 Higiene antes de armar

```
[ ] captura de trafego PARADA no painel, OU redacao de headers LIGADA
[ ] a captura nao esta apontada para a aba do Runtime (127.0.0.1:8010)
[ ] sessao sess_1788555910180 apagada (ela contem Bearer em claro — #T1)
[ ] chave sk-ant- revogada SE uma chave completa e valida foi colada no chat
```

### A.2 Subir o ambiente (host Windows — é onde há Chrome)

```
[ ] cd C:\Users\central\Downloads\lab_edp_novo
[ ] python -c "import fastapi, uvicorn; print('ok')"
[ ] $env:AGENT_RUNTIME_TOKEN = (python -c "import secrets;print(secrets.token_urlsafe(32))")
[ ] $env:AGENT_RUNTIME_TOKEN        <- anotar; nao atravessa terminais
[ ] python -m agent_runtime --propositor eco --porta 8010 --browser --raiz .\tarefas_smoke
[ ] o arranque imprime provedores=['chrome_debugger'] e "browser.inspect LIGADO"
[ ] outro terminal: python -m edp.serve   (dashboard em 127.0.0.1:8000)
[ ] curl.exe -s http://127.0.0.1:8010/health          -> ok:true
[ ] curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8000/dashboard -> 200
```

### A.3 Extensão e alvo

```
[ ] chrome://extensions -> modo desenvolvedor -> Carregar sem compactacao
    -> claude-exporter-v4.2/
[ ] abrir o painel do Copiloto (aba propria)
[ ] F12 na aba do PAINEL -> aba Console   (NAO o campo de chat do Copiloto)
[ ] CopilotBrowserBridge.onEvento((e,d) => console.log('[bridge]', e, d))
[ ] CopilotBrowserBridge.start('http://127.0.0.1:8010', '<AGENT_RUNTIME_TOKEN>')
[ ] (await chrome.tabs.query({url:'http://127.0.0.1:8000/*'})).map(t=>({id:t.id,url:t.url}))
[ ] await CopilotBrowserBridge.registrarAlvo(<TAB_ID>)
[ ] console mostra alvo.registrado e depois alvo.anexado com operacional:true
[ ] chrome://extensions mostra a faixa de depuracao sobre a aba do dashboard
[ ] GET /v1/browser/alvo -> {"estado":"ANEXADO","operacional":true}
```

**Se `operacional` for `false`, pare.** Tarefa submetida antes disso não
conclui — e esse é o comportamento correto, não um defeito.

### A.4 O positivo

```
[ ] POST /v1/tarefas com capacidades ["browser.inspect"]
[ ] status ................ CONCLUIDA
[ ] observacoes ........... 3
[ ] kinds ................. page, dom, history
[ ] page.url .............. http://127.0.0.1:8000/dashboard
[ ] dom.dom_nodes ......... > 0
[ ] fonte ................. contem "tab=<TAB_ID>"
[ ] .\tarefas_smoke\<TASK_ID>\tarefa.json existe
```

### A.5 Os três negativos

```
[ ] N1 alvo errado (tab_id 999999)     -> browser.error, /não é o alvo/
[ ] N1 nenhum comando CDP foi para 999999
[ ] N2 aba navegada para outra origem  -> browser.error, /mudou de origem/
[ ] N2 CopilotController.alvoAtual() === null
[ ] N3 debugger desanexado a mao       -> browser.error, /não está anexado/
```

### A.6 Correlação e segurança

```
[ ] duas tarefas seguidas: cada task_id com observacoes do proprio tarefa_id
[ ] nenhum request_id atendido duas vezes
[ ] no JSON do resultado: nenhuma chave fora de
    {kind,url,title,dom_nodes,history_len,erro}
[ ] nenhum cookie, authorization, storage ou chave de API
[ ] nenhum objeto Chrome cru (exceptionDetails, backendNodeId, ...)
```

### A.7 Registro

```
[ ] colar as saidas em docs/agent_runtime/RESULTADO_SMOKE_BROWSER_INSPECT.md
[ ] anotar data e versao do Chrome
[ ] atualizar #T3 em DIVIDAS_TRANSPORTE.md para FECHADA
[ ] atualizar CHECKLIST_TRANSPORTE.md §5 (smoke real)
```

**Enquanto `RESULTADO_SMOKE_BROWSER_INSPECT.md` não existir, a descrição
correta continua sendo "fechado em código e teste, aberto em Chrome real".**

---

## BLOCO B — Juice Shop com `browser.inspect` (L0, não precisa de assinatura)

Pré-registro:
[`preregistro_juice_shop_inspect.md`](preregistro_juice_shop_inspect.md).

O ponto que vale explicitar: **`browser.inspect` sobre o Juice Shop não pede
capacidade nova.** É a mesma capacidade L0 apontada para outra aba. O que muda
é o alvo — e é justamente aí que a restrição de escopo é testada contra uma
aplicação com DOM, rotas, formulários e erros de verdade.

```
[ ] Juice Shop rodando em 127.0.0.1:3000
    (docker AUSENTE nesta maquina; npm 9.2.0 presente -> instalar do fonte)
[ ] registrar a aba do Juice Shop como alvo
[ ] browser.inspect -> 3 observacoes, page.url do Juice Shop
[ ] NEGATIVO: com o Juice Shop registrado, pedir inspect na aba do dashboard
    -> REJEITADO (prova que o escopo e por aba, nao por "e local")
[ ] comparar dom_nodes do Juice Shop vs dashboard (ordem de grandeza diferente)
```

**O que NÃO fazer aqui:** clicar, preencher, navegar. Isso é o Bloco C.

---

## BLOCO C — `browser.click` e o resto de L1 `[ASSINATURA]`

Pré-registro:
[`preregistro_atuacao_L1_vertical.md`](preregistro_atuacao_L1_vertical.md).
**BLOQUEADO.** `exige_implementada()` recusa L1/L2 enquanto
`DECISAO_ATUACAO.md` estiver sem assinatura.

```
[ASSINATURA] DECISAO_ATUACAO.md — 5 linhas em branco:
             opcao (A/B/C/D)
             canal de volta (D1 polling / D2 WebSocket / D3 Native Messaging)
             alvo permitido
             primeira capacidade do vertical slice
             justificativa
```

Quando assinada, e **só depois do Bloco A fechado**, o passo a passo está no
pré-registro. Nada de L1 antes disso.

---

## BLOCO D — Dívidas do dashboard (edp_v5)

```
[ ] #54  render do runtime flow com LLM real
         precondicao MEDIDA (log de producao prova a cadeia no servidor);
         falta medir a TELA. Exige provider com chave.
[ ] #55  avg_top sem definicao fechada
         documentar a grandeza a partir do codigo que a produz: definicao,
         unidade, populacao, e o que uma queda pode e NAO pode significar.
         So entao decidir se vai ao dashboard, e com qual ressalva na tela.
[ ] #56  is_connected() faz round-trip de rede no caminho do turno
         medido: 21,782s = ~44% de um turno de 49,6s; 5 probes = 86,6s em ~5min
         correcao: cachear validate() com TTL, OU trocar por leitura de estado
         no caminho quente, deixando o probe para /connect e para o endpoint
         de providers. Caminho quente do kernel em repo PUBLICO -> decisao
         antes de codigo.
```

---

## BLOCO E — Dívidas do transporte (lab)

```
[x] #T1  token do smoke de 04/09 comprometido — FECHADA por rotacao
[ ] #T2  bearer de longa duracao no contexto do painel
         aceito para o MVP; nao e o estado final. Native Messaging resolve
         sem tocar no ChromeDebuggerProvider (CanalBrowser ja e Protocol).
         Custo: `nativeMessaging` no manifest + host nativo por maquina.
[ ] #T3  browser.inspect nao rodou contra Chrome real  -> BLOCO A
```

---

## BLOCO F — Itens do brief de transporte ainda abertos

`CHECKLIST_TRANSPORTE.md` foi de 19/39 para 38/39. O que resta:

```
[ ] §6  criterio de conclusao: Copilot -> transporte -> Runtime -> ... -> Copilot
        sem copiar JSON manualmente.
        Adiado POR DECISAO ("pagina separada primeiro"), nao por atraso.
        Consequencia a respeitar: a documentacao so pode afirmar "depois:
        transporte real Copilot -> Runtime" APOS esse teste. Ela nao afirma.
```

---

## BLOCO G — Assinaturas pendentes `[ASSINATURA]`

```
[ASSINATURA] docs/auditor/DECISAO_RANKING.md          3 linhas em branco
             a opcao C corresponde a assinatura pendente do exp017
[ASSINATURA] docs/curadoria/DECISAO_ACOPLAMENTO.md    3 linhas em branco
[ASSINATURA] docs/agent_runtime/DECISAO_ATUACAO.md    5 linhas em branco
[ASSINATURA] exp017 — promocao do tratamento a producao
             instrumento (log-only) ja emite em producao; o dado esta
             acumulando enquanto a assinatura espera
```

---

## BLOCO H — Publicação

```
[ ] lab_edp_novo    55 commits nao enviados   -> exige confirmacao explicita
[ ] edp_v5          11 commits nao enviados   -> repo PUBLICO; conferir que
                    nenhum texto de conversa foi commitado antes de enviar
[ ] sf_exportador   sem upstream configurado  -> decidir se tem remoto
```

Nunca enviados sem você dizer. `edp_v5` é público: antes do push, conferir
`git log -p` dos 11 commits contra a regra de não commitar texto de conversa.

---

## BLOCO I — Frentes paradas, fora do transporte

```
[ ] PILOTO_ZERO   8 documentos pre-registrados, 0 resultados
                  CLAIMS, INPUT_SCHEMA, PERGUNTAS, PREREGISTRO, PRIVACY,
                  QUICKSTART, README, SERVICE_CONTRACT
                  Pre-registrado e nao executado — a pergunta que ele responde
                  ("alguem externo consegue e quer usar isto?") continua aberta
                  e e a mais antiga do projeto.
```

---

## O que NÃO está neste checklist, e por quê

A visão comercial discutida em 05/09 — Agent Runtime as a Service, marketplace
de capacidades, observabilidade de produto inteiro, grafo de execução — **não
gera itens aqui**. Ela descreve para onde a infraestrutura *pode* ir, e o
checklist só registra o que tem passo a passo verificável hoje.

Transformar visão em item de checklist faria as duas coisas parecerem o mesmo
tipo de compromisso. Não são: uma tem critério de aceite, a outra tem
hipótese de mercado. A distinção é a mesma que o projeto mantém entre
`medido` e `inferido`, e ela vale também para roadmap.
