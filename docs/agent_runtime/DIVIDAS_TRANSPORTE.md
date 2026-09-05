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

## #T4 — a assinatura ainda não é autoridade em runtime

**Status:** ABERTA. É decisão, não tarefa — e tem uma tensão de desenho que
precisa ser resolvida antes, não durante.

### O que existe hoje
`tests/test_governanca_capacidades.py` (7 testes, 05/09/2026) liga a
assinatura de `DECISAO_ATUACAO.md` ao catálogo: enquanto houver linha em
branco, nenhuma capacidade acima de L0 pode estar `implementada=True`.
Verificado por mutação — com `act.click` marcado implementado, o teste falha.

**Mas isso é guard rail de suíte, não barreira de runtime.** Alguém pode
editar `capacidades.py`, não rodar a suíte, e executar. O que existe é uma
condição objetiva para *detectar* a violação quando os testes rodarem.

### A tensão que a solução óbvia cria
O caminho direto — `exige_implementada()` lê `DECISAO_ATUACAO.md` no import e
recusa L1/L2 se a assinatura estiver em branco — **acopla o runtime a um
arquivo de `docs/`**. E isso colide com uma propriedade que o projeto já
declara em `pyproject.toml`:

```
packages = ["auditor", "auditor.checks", "auditor.adaptadores"]
# fixtures/ e examples/ NAO entram: [...] O pacote instalado precisa
# funcionar sem eles.
```

`agent_runtime` nem sequer está na lista de pacotes instaláveis hoje, mas o
princípio já está escrito: **o runtime funciona sem o material do
laboratório.** Um runtime que se recusa a subir porque não achou um `.md` é um
runtime que não pode ser distribuído sem os documentos — e isso é uma
consequência de empacotamento, não uma decisão de segurança.

### As formas de resolver, com o custo de cada uma

**T4a — o runtime lê o `.md`.** Mais simples, uma fonte só de verdade.
Custo: acopla runtime a `docs/`, e a ausência do arquivo passa a ser
indistinguível de "não assinado" — o que é o default seguro, mas quebra
qualquer distribuição sem docs.

**T4b — a assinatura gera um artefato legível por máquina** (uma linha em
config, um `.json` versionado dentro do pacote). O `.md` continua sendo o
registro humano; o artefato é a autoridade. Custo: duas coisas para manter em
sincronia, e um teste que prove que não divergiram.

**T4c — a autoridade vira configuração explícita de quem sobe o serviço**
(`AGENT_RUNTIME_TETO_NIVEL`, default `0`). Custo: tira a assinatura do caminho
e a substitui por quem opera — o que pode ser certo ou errado dependendo de
quem se quer que decida, e é exatamente isso que a decisão precisa dizer.

Nenhuma é obviamente melhor. A escolha depende de uma pergunta que ainda não
foi feita: **a assinatura autoriza o repositório, ou autoriza cada instância
que roda?** As duas respostas são defensáveis e levam a desenhos diferentes.

---

## #T3 — `browser.inspect` não foi executado contra Chrome real

**Status:** ABERTA. É o único item que separa esta frente de "fechada".

Ver `SMOKE_BROWSER_INSPECT.md`. Enquanto
`RESULTADO_SMOKE_BROWSER_INSPECT.md` não existir, a descrição correta é
**"fechado em código e teste, aberto em Chrome real"**.

Nenhuma capacidade nova entra antes disso. `browser.click` e as demais
continuam recusadas por `exige_implementada()` e dependem da assinatura de
`DECISAO_ATUACAO.md`.
