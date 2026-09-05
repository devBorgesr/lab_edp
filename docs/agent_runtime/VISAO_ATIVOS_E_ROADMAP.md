# Visão, ativos e roadmap

**05/09/2026.** Registro das direções arquiteturais e comerciais discutidas
nesta frente, para que não fiquem apenas no histórico de conversa.

## Natureza deste documento

**Nada aqui é critério PASS/FAIL, trabalho executado, ou evidência de
capacidade implementada.** O que tem critério de aceite está em
[`CHECKLIST_EXECUCAO.md`](CHECKLIST_EXECUCAO.md) e nos três pré-registros;
aquilo se mede, isto se decide.

A distinção que o projeto sustenta entre `medido` e `inferido` ganha aqui um
terceiro termo:

```
medido ...... existe evidencia reproduzivel     -> RESULTADO_*.md
inferido .... deduzido de codigo ou de medida   -> DIVIDAS, DECISAO_*
planejado ... direcao decidida ou discutida     -> ESTE DOCUMENTO
```

Confundir os três é o modo mais comum de um projeto acreditar que já construiu
o que só desenhou.

---

## 1. Agent Runtime as a Service

O ativo principal não é o agente — é a infraestrutura de execução. A camada
que já está de pé responde perguntas que um chatbot com ferramentas não
responde:

```
o que o agente pode fazer?
onde pode fazer?
em nome de quem?
com qual orcamento?
qual foi a decisao?
qual foi o resultado?
```

Essa camada é reutilizável, e a inversão comercial é possível: em vez de
construir um sistema *para* o Copiloto, fornecer a infraestrutura na qual
vários agentes de vários clientes executam.

```
                  SUA INFRAESTRUTURA
             ┌──────────────────────────┐
             │      Agent Runtime       │
             └────────────┬─────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
         Browser        RAG        Internal Apps
          Agent        Agent           Agent
            │             │             │
            ▼             ▼             ▼
         Chrome       Vector DB        APIs
```

Não é "vendemos um chatbot". É "fornecemos a infraestrutura operacional para
agentes executarem tarefas com capacidades controladas".

---

## 2. Capability Registry / marketplace de capacidades

Hoje o Registry tem 13 capacidades, das quais 6 implementadas e todas L0. A
estrutura permite que cada capacidade seja tratada como unidade vendável:

```
CORE           browser, memory, retrieval, files, telemetry
PRO            GitHub, databases, APIs externas, cloud
ENTERPRISE     private systems, SSO, audit, policy engine, isolated execution
```

E permite providers de terceiros: Salesforce, AWS, GitHub, Chrome, Postgres,
Slack, Browser QA, RAG Diagnostic. A separação Registry / Policy / Provider
existe justamente para que o modelo não alcance o mecanismo de execução — é
ela que torna "capacidade" um módulo, e não uma função.

---

## 3. Browser Agent Infrastructure

A diferença entre os dois desenhos abaixo é a tese inteira:

```
LLM -> texto

LLM -> intencao -> politica -> capacidade -> browser provider
    -> Chrome -> observacao -> nova decisao
```

O segundo é infraestrutura de agentes que operam software real. Produtos
possíveis sobre ela:

**Browser QA Agent** — recebe "teste o fluxo de cadastro"; abre, navega,
preenche, observa, detecta erro, reproduz, coleta evidência, gera relatório.

**RAG QA Agent** — abre painel, executa consultas, observa retrieval, compara
resultados, coleta métricas, identifica anomalias, gera diagnóstico.

**AI Debugging Agent** — reproduz erro, observa console e network, modifica
estado, reproduz de novo, compara.

O laço `Observe → Interpret → Decide → Act → Observe` é a base operacional dos
três.

---

## 4. Governança de agentes: `MODELO ≠ AUTORIDADE`

O ativo mais raro, e o que mais separa isto de "integrar um modelo ao Chrome".

```
o modelo PROPOE      browser.click
a Politica DECIDE    autoriza ou nega
o Provider EXECUTA   traduz capacidade em CDP
```

Isso permite que uma empresa declare escopo por agente:

```
agente de QA          browser.*        network.*
agente de suporte     browser.inspect  browser.click  browser.fill
agente financeiro     database.read    NAO database.write
```

O problema empresarial não é "a IA consegue fazer?" — é "a IA consegue fazer
**sem sair do escopo que a empresa autorizou?**". Essa é a pergunta que a
arquitetura atual responde por construção.

---

## 5. Task + Budget + Lifecycle + Audit

A tarefa não é um comando; é uma unidade operacional mensurável:

```
Task
 ├── objective        ├── observations
 ├── capabilities     ├── policy
 ├── budget           ├── parent
 ├── iterations       ├── state
 └── result
```

Isso é o que torna possível cobrar por tarefas/mês, ações/mês, tokens, tempo
de execução, capacidades ou agentes — e é o que já está implementado em
`servico.py` e `tarefa.py`.

---

## 6. Agent Operations

Um dashboard operacional sobre o que já é persistido: agentes, tarefas,
capacidades, execuções, falhas, custo, tempo, observações, ações, políticas.

---

## 7. Agent Operating Layer

A analogia útil: orquestradores de infraestrutura não valem por "rodar
processos", e sim por organizarem deployment, scheduling, resources,
isolation, health, lifecycle, observability e policy.

O que está sendo construído faz algo análogo para agentes:

```
                    AGENT PLATFORM
 ┌───────────────────────────────────────────┐
 │ Scheduler                                 │
 │ Router                                    │
 │ Policy Engine                             │
 │ Capability Registry                       │
 │ Memory                                    │
 │ Telemetry                                 │
 │ Audit                                     │
 │ Budgeting                                 │
 └───────────────────────────────────────────┘
          │          │           │
          ▼          ▼           ▼
      Browser      RAG        Enterprise
       Agent      Agents        Agents
```

---

## 8. Evolução do Retrieval Diagnostic

O auditor mede; o Runtime acrescenta o que o auditor sozinho não tem —
**experimentar e observar de novo**.

```
AUDITOR -> DIAGNOSTICO -> AGENT -> EXPERIMENTACAO -> OTIMIZACAO

Produto A   "seu retriever devolve isso"
Produto B   "seu agente investiga por que isso acontece"
Produto C   "seu agente testa mudancas e compara resultados"
```

Uma linha inteira de produtos sobre a mesma infraestrutura. E o auditor
continua sendo linha separada: `auditor/` não importa `agent_runtime/`.

---

## 9. Browser Provider como produto independente

`ChromeDebuggerProvider` foi feito para o EDP, mas tecnicamente é um Browser
Agent Runtime com API própria: `inspect`, `click`, `fill`, `screenshot`,
`network`, `console`, `evaluate`. Clientes possíveis: software houses, SaaS,
times de QA, times de segurança, vendors de RAG, startups de IA, TI
corporativa.

---

## 10. Do RAG para o produto inteiro

Com autorização explícita do cliente, o ecossistema pode observar muito além
do retrieval:

```
                    PRODUTO DO CLIENTE
 ┌─────────────────────────────────────────────────┐
 │ Frontend · API · Backend · Banco · Cache        │
 │ Filas · LLM · RAG/Retrieval · Observabilidade   │
 │ Integracoes externas                            │
 └───────────────────────┬─────────────────────────┘
                         ▼
                EDP / Agent Runtime
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
     Browser          Network          Backend
     Provider         Provider         Provider
        └────────────────┼────────────────┘
                         ▼
                  Observation Graph -> AI Analyst
```

Perguntas que passam a ser respondíveis: onde está a latência; se o frontend
faz chamadas redundantes; qual endpoint degrada; se a resposta do LLM diverge
do contexto recuperado; se o cache é usado; qual cadeia de eventos produziu
determinado erro.

**Mas "capturar tudo" não é a formulação certa.** É "capturar tudo que foi
autorizado, dentro de um escopo técnico definido" — e é a mesma propriedade
que `browser.inspect` já exercita com o escopo de aba.

---

## 11. `observe` ≠ `intercept` ≠ `act`

Três níveis com custos e riscos diferentes, que não podem ser tratados como
sinônimos:

```
1. OBSERVAR      ve trafego/eventos ja produzidos
2. INTERCEPTAR   fica no caminho, inspeciona/modifica fluxos
3. ATUAR         provoca eventos no sistema
```

O primeiro é relativamente simples. O segundo exige arquitetura de
instrumentação/proxy própria. O terceiro é onde entram click, fill, reload,
APIs e banco.

---

## 12. Futuras classes de capacidades

Nenhuma destas existe. Registro da direção, não da implementação:

```
observe.browser      observe.network     observe.api
observe.database     observe.llm         observe.queue

intercept.network    intercept.api

act.browser          act.api             act.database
```

Cada uma seria capacidade independente, com decisão, política e teste
próprios — pelo mesmo caminho que `browser.inspect` percorreu.

---

## 13. O laço de diagnóstico

```
OBSERVE -> CORRELATE -> ANALYZE -> HYPOTHESIZE
        -> EXPERIMENT -> OBSERVE AGAIN -> DIAGNOSE
```

Mais poderoso que um dashboard tradicional porque fecha o laço: o sistema não
só mostra, ele testa a própria hipótese.

---

## 14. Execution Graph

Cada execução já produz a cadeia `Task → Intention → Capability → Provider →
Action → Observation → Decision → Next action`. Acumulada, ela vira dado
estruturado sobre **como agentes resolvem problemas** — algo que um chatbot
comum não possui.

```
Tarefa #1827
├── inspect -> DOM
├── inspect -> network
├── click   -> selector X
├── inspect -> console error
└── conclude
```

Pode alimentar analytics, evaluation, benchmarking de agentes, otimização de
política, workflow mining, previsão de falha e treino.

---

## 15. Memória operacional do produto

```
Product └── Session └── Task
                     ├── Observation   ├── Result
                     ├── Capability    ├── Hypothesis
                     ├── Action        └── Evidence
```

Depois de milhares de execuções, isso é uma memória operacional do produto do
cliente — e habilita Anomaly Detection, Regression Detection, Root Cause
Analysis, AI QA, Agent QA, Performance Intelligence, RAG Intelligence, Product
Intelligence e Continuous Testing.

---

## 16. Arquitetura multi-provider e árvore de produtos

```
                    ┌─────────────────┐
                    │  AGENT RUNTIME  │
                    └────────┬────────┘
     ┌─────────────┬─────────┼─────────┬─────────────┐
     ▼             ▼         ▼         ▼             ▼
  Browser      Retrieval   Memory    GitHub     Enterprise
   Agent         Agent      Agent     Agent        Agent
     │             │         │         │             │
     ▼             ▼         ▼         ▼             ▼
  QA SaaS      RAG Audit   Memory    DevOps      Internal
                          Platform              Automation
```

Serviços ao redor: Agent Runtime SaaS, Capability Marketplace, Browser
Automation, RAG Diagnostics, Agent QA, Agent Observability, Product
Intelligence.

---

## 17. Princípio comercial central

Não se vende "deixe a gente interceptar tudo". Vende-se **"conceda ao Runtime
as capacidades necessárias para investigar seu produto"**.

```
Cliente A                        Cliente B
  browser.observe      OK          browser.observe      OK
  network.observe      OK          network.observe      OK
  rag.observe          OK          network.intercept    OK
  llm.observe          OK          browser.act          OK
  database.observe     NAO         database.read        OK
  browser.act          NAO         database.write       NAO
  network.intercept    NAO
```

A autorização deixa de ser "aceito os termos" e passa a ser um **capability
contract verificável** — que é exatamente o que Registry + Policy + Provider +
Task já implementam.

---

## 18. Estado real hoje, para não confundir com o acima

```
browser.inspect ....... L0, implementada, 585 testes, NAO executada em Chrome real
browser.click ......... L1, DECLARADA e RECUSADA, pre-registro preparado e BLOQUEADO
browser.evaluate ...... capacidade SEPARADA, com decisao propria — trocar
                        EXPR_PAGINA por string do modelo abriria
                        modelo -> JavaScript arbitrario -> pagina, e a
                        classificacao L0 deixaria de existir no mesmo instante
demais capacidades .... nao implementadas
observe.* / intercept.* / act.* ... nao existem
```

---

## 19. Duas fronteiras que a visão não pode apagar

**O Runtime não deve depender de um único produto.** O Copiloto é o primeiro
cliente da infraestrutura, não o dono dela. `CanalBrowser` ser `Protocol`
existe por isso.

**`chrome.debugger` é um provider/adaptador, não a arquitetura.** É o primeiro
demonstrador concreto de que o Runtime pode sair de "analisa dados" para
"observa e, sob autorização e escopo, experimenta sobre um produto real". Não
é o produto.

---

## Como este documento se relaciona com os outros

```
CHECKLIST_EXECUCAO.md ....... o que pode ser executado, com criterio
preregistro_*.md ............ experimentos congelados antes do dado
DECISAO_*.md ................ escolhas que aguardam assinatura
DIVIDAS_TRANSPORTE.md ....... o que esta quebrado ou pendente
ESTE DOCUMENTO .............. para onde isto pode ir, e por que
```

Nenhum item daqui vira tarefa sem passar por um dos quatro anteriores.
