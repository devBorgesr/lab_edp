# Dívidas do transporte e da atuação

Escopo desta frente. As dívidas do kernel continuam em
`edp_v5/docs/DIVIDAS.md`; misturar as duas listas faria a numeração de lá
significar duas coisas.

---

## #T1 — Token do smoke de 04/09/2026: COMPROMETIDO

**Status:** FECHADA por rotação (o token não vale mais). Registro mantido
porque o mecanismo que a causou continua existindo.

### O que aconteceu
Durante a primeira tentativa real do smoke, a captura de tráfego do painel
ficou **294 s apontada para `http://127.0.0.1:8010/`** — a própria página do
Runtime — com a opção *"gravar Authorization/Cookie/tokens sem redigir"*
ligada.

Três requisições foram gravadas em
`/copilot_workspace/traffic/2026-09-04/sess_1788555910180.har`:

```
GET  /                        sem token
POST /v1/tarefas              Authorization: Bearer <AGENT_RUNTIME_TOKEN>
GET  /v1/tarefas/T-51d1131b   Authorization: Bearer <AGENT_RUNTIME_TOKEN>
```

Duas das três em claro, dentro do IndexedDB da extensão.

### Por que aconteceu
Duas causas, e nenhuma é do Runtime:

1. **O documento não mandava conferir a captura antes de começar.** Corrigido
   em `e709528`: `SMOKE_BROWSER_INSPECT.md` agora abre com esse checklist.
2. **`SEU_TOKEN` era ambíguo.** O operador tinha uma chave `sk-ant-` à mão — o
   "token" mais visível na tela — e a colou no chat do Copiloto, que é um LLM
   e guardou o texto. Corrigido no mesmo commit: o documento agora diz que é o
   `AGENT_RUNTIME_TOKEN`, que a chave do provedor não tem relação com este
   transporte, e **onde** colar (console do DevTools, não o chat).

### O que NÃO aconteceu
A chave da Anthropic **não está nesse HAR**. A captura é escopada a uma aba, e
a aba era `127.0.0.1:8010`; o tráfego para `api.anthropic.com` sai de outro
contexto. As duas exposições são independentes — a do chat é uma questão
separada, e a regra é simples: se a chave completa foi colada e era válida,
revogar.

Repositórios verificados: nenhum `sk-ant-` real versionado. As 4 ocorrências
no lab são fixtures `"A" * 40` nos testes do próprio sanitizador.

### O que fica de lição verificável
Um HAR de tráfego local com redação desligada é uma superfície de exposição do
**próprio serviço que está sendo testado**. Isso vale para qualquer capacidade
futura que o Runtime exponha por HTTP, não só para este smoke.

---

## #T2 — Bearer de longa duração no contexto do painel

**Status:** ABERTA. Aceita para o MVP; não é o estado final.

### O problema
`copilot/browser_bridge.js` recebe o `AGENT_RUNTIME_TOKEN` em `start()` e o
põe no header de cada `fetch`. Enquanto a ponte roda, o token está em memória
do painel e viaja em toda requisição — logo, é capturável por qualquer coisa
que observe aquela aba, que foi exatamente o mecanismo de `#T1`.

Para o smoke serve. Para a versão operacional — o Copiloto controlando módulos
do EDP — não serve: quanto mais capacidades o Runtime expõe, mais caro fica um
bearer de longa duração num contexto que o próprio produto sabe capturar.

### O caminho, e por que ele já está barato
Native Messaging resolve isto sem tocar em `ChromeDebuggerProvider`: a
identidade passa a vir de `allowed_origins` (o Chrome amarra o host nativo ao
ID exato da extensão), e não de um segredo que o JavaScript carrega.

O provedor já está desacoplado por `CanalBrowser` (`Protocol`), então a
mudança é **uma implementação de canal nova**, não um redesenho. Foi por isso
que o canal foi construído assim.

Custo real: `nativeMessaging` no manifest (ausente hoje) e instalação de host
nativo por máquina, com caminho absoluto.

### Mitigações que valem enquanto isto não muda
```
[ ] o token e gerado por sessao (`secrets.token_urlsafe(32)`), nao fixo
[ ] `stop()` do bridge zera o token — ele nao sobrevive ao stop
[ ] a pagina de teste nao persiste o token: type=password, sem localStorage
[ ] captura desligada, ou redacao ligada, durante qualquer operacao
```

Os três primeiros já valem em código. O quarto é procedimento, e é o que
falhou em `#T1`.

---

## #T3 — `browser.inspect` não foi executado contra Chrome real

**Status:** ABERTA. É o único item que separa esta frente de "fechada".

Ver `SMOKE_BROWSER_INSPECT.md`. Enquanto
`RESULTADO_SMOKE_BROWSER_INSPECT.md` não existir, a descrição correta é
**"fechado em código e teste, aberto em Chrome real"**.

Nenhuma capacidade nova entra antes disso. `browser.click` e as demais
continuam recusadas por `exige_implementada()` e dependem da assinatura de
`DECISAO_ATUACAO.md`.
