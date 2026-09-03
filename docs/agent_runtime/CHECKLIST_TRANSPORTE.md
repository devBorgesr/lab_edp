# Checklist — o que falta no transporte, e o que falta em volta

**03/09/2026.** Medido contra o brief da etapa de transporte, item por item,
depois do commit `98269ed`. Não é estimativa: cada linha marcada `[x]` tem
teste ou medição por trás, e cada `[ ]` foi conferida como ausente no código.

**Estado do brief: 19 de 39 feitos, 3 parciais, 17 ausentes.**

> **Atualização 03/09/2026, commit desta rodada.** §1 a §5 fechados:
> **38 de 39**. O único aberto é §6, o critério de conclusão, que exige o
> painel do Copiloto como cliente — adiado pela própria assinatura. Fora do
> brief (§7), nada mudou: continuam 10 itens, e nenhum deles é meu para
> fechar. Ver §9, no fim, para o que cada linha virou.

Somando as pendências fora do brief (§7): **50 itens no total — 20 feitos,
3 parciais, 27 abertos.** Os dois números medem coisas diferentes e por isso
aparecem separados: 39 é a etapa de transporte; 11 é o que ficou acumulado em
volta dela e não pertence a esta etapa.

---

## 0. A causa raiz de 7 dos 17

O brief pede `submit_task(request) -> task_id`, depois `get_task(task_id)`,
`get_result(task_id)`, `cancel_task(task_id)`. Isso é **assíncrono por
construção**: submete, recebe um id, consulta depois.

Eu li *"não crie streaming complexo ainda; primeiro faça request/response
confiável"* como **execução síncrona** — a tarefa roda dentro da requisição e
o resultado volta na mesma resposta. Não é a mesma coisa: "request/response"
descreve o formato do transporte, não onde a tarefa executa.

Como nenhuma tarefa é guardada, não há o que consultar. Isso sozinho derruba
`get_task`, `get_result`, `cancel_task`, idempotência, isolamento entre
tarefas, consulta de estado e consulta de resultado.

**Persistir a tarefa é a peça que destrava sete itens de uma vez.**

---

## 1. API mínima — 1 de 4

- [x] `submit_task(request) -> task_id` — `POST /v1/tarefas`, **202** +
      `task_id` + header `Location`. Não devolve resultado: naquele instante
      não há.
- [x] `get_task(task_id) -> estado` — `GET /v1/tarefas/{id}`
- [x] `get_result(task_id) -> resultado` — `GET /v1/tarefas/{id}/resultado`,
      **409** enquanto não terminal ("ainda não há resultado" é fato
      diferente de "o resultado é vazio")
- [x] `cancel_task(task_id) -> estado` — `POST /v1/tarefas/{id}/cancelar`;
      cancelar tarefa já terminal não é erro e não muda nada

## 2. TaskService com resultado persistido — 0 de 1

- [x] `TarefaRequest → validação → Tarefa → Executor → resultado persistido`
      — `agent_runtime/servico.py`. Máquina de estados própria (`TRANSICOES`,
      terminal não volta), `confere()` antes de gravar, escrita atômica
      `tmp + os.replace`. Padrão do `auditor/jobs.py`, **reimplementado e não
      importado**: `agent_runtime/__init__.py` declara que esta linha de
      produto não toca no auditor, e importar criaria a dependência que
      aquela frase existe para negar. A duplicação está anotada nos dois
      lados.

## 3. Requisitos de segurança — 8 de 12, 2 parciais

- [x] handshake / autenticação local — `Bearer` + `hmac.compare_digest`;
      servidor recusa subir sem `AGENT_RUNTIME_TOKEN`
- [x] **identificação do cliente** — `AGENT_RUNTIME_TOKENS` = `id:token`
      separados por vírgula; sem ela, `AGENT_RUNTIME_TOKEN` vale como cliente
      `default`. O `client_id` autenticado filtra toda leitura.
- [x] validação de `TarefaRequest v1` — `requisicao.valida`
- [x] limite de tamanho da mensagem — `TETO_BYTES` = 64 KiB, 413
- [x] timeout — `TETO_SEGUNDOS` = 30, recusado na entrada
- [x] rejeição de schema desconhecido
- [x] rejeição de campos desconhecidos
- [x] rejeição de capacidades acima do teto L0
- [x] **isolamento entre tarefas** — tarefa de outro cliente responde
      **404**, não 403: 403 diria que aquele `task_id` existe em algum lugar,
      e `task_id` não é segredo. `task_id` hostil (`../outro`) é recusado
      antes de compor caminho.
- [x] **correlation / task ID** — `X-Correlation-Id` em header, não no
      corpo: `TarefaRequest v1` recusa campo desconhecido de propósito, então
      pôr no corpo obrigaria a mudar o contrato ou a devolver 422 a quem
      mandasse rastreio.
- [x] **tratamento de desconexão** — a execução deixou de morar dentro da
      requisição, então o cliente sumir não leva a tarefa junto; um cliente
      novo lê o mesmo registro, e outro `TaskService` sobre a mesma raiz lê o
      que o primeiro gravou.
- [x] não exposição para `0.0.0.0` — `roda()` recusa host fora de loopback,
      medido: `curl 10.0.2.15:8010` recusa, `127.0.0.1:8010` responde 200

## 4. Testes obrigatórios — 8 de 16, 1 parcial

- [x] request válido
- [x] schema inválido
- [x] campo desconhecido
- [x] capacidade desconhecida
- [x] capacidade L1 recusada
- [x] payload acima do limite
- [x] cliente não autenticado
- [x] task_id / correlation_id — volta em toda consulta, e há teste de que
      mandá-lo no corpo dá 422
- [x] desconexão
- [x] duas tarefas simultâneas sem mistura de estado — 4 em paralelo,
      objetivos e observações distintos
- [x] consulta do estado
- [x] consulta do resultado — 200 e 409
- [x] cancelamento — em execução e já terminal
- [x] idempotência / reenvio — por `X-Request-Id`, e o mesmo id de
      clientes diferentes não colide
- [x] transporte indisponível — porta fechada falha alto
- [x] bridge não exposto além do necessário

## 5. Smoke test real — 2 de 5

- [x] iniciar o Python Runtime — `python3 -m agent_runtime --propositor eco`
- [x] enviar `TarefaRequest v1` pelo transporte real — Firefox headless,
      mesma origem, token certo → 200, `CONCLUIDA`, observação com hash
- [x] **usar um Router fake primeiro** — `tests/test_smoke_transporte.py`
      monta `PropositorLLM(ClienteFake, RoteadorFixo)`. Um teste separado
      confere a **trilha** do propositor, para que o smoke não possa passar
      com o Router curto-circuitado.
- [x] **executar tarefa L0 contra HAR** — `ProvedorHAR` sobre HAR real no
      formato do Exportador. Um teste prova que o `Bearer` e o `set-cookie`
      do HAR **não** chegam ao cliente pelo endpoint HTTP.
- [x] **consultar o resultado pelo mesmo canal** —
      `GET /v1/tarefas/{id}/resultado`, exercitado em teste e no navegador

## 6. Critério de conclusão — 0 de 1

- [ ] `Chrome Copilot → transporte → Runtime → Router → modelo → Policy →
      HAR → resultado → Chrome Copilot`, sem copiar JSON manualmente.

**Não atingido, e não é atraso:** a assinatura de 03/09 escolheu "página
separada primeiro", o que adia deliberadamente tocar no Exportador. A
consequência a respeitar: o brief manda a documentação só afirmar
*"depois: transporte real Copilot → Runtime"* **após** esse teste — e ela
não afirma. `DECISAO_TRANSPORTE.md` continua dizendo que o painel vira o
segundo cliente em etapa própria.

---

## 7. Fora do brief — pendências acumuladas

### 7.1 Decisões em branco (cada uma trava uma frente)

- [ ] `docs/auditor/DECISAO_RANKING.md` — 3 linhas de assinatura em branco.
      A opção C corresponde à assinatura pendente do `exp017`.
- [ ] `docs/curadoria/DECISAO_ACOPLAMENTO.md` — 3 linhas em branco
- [ ] `docs/agent_runtime/DECISAO_ATUACAO.md` — 3 linhas em branco.
      Enquanto estiver assim, L1/L2 seguem declaradas e recusadas.
- [x] `docs/agent_runtime/DECISAO_TRANSPORTE.md` — assinada em 03/09/2026
- [ ] `edp_v5/docs/DECISAO_probe_por_turno.md` — **nova**, preparada em
      03/09/2026, aguardando assinatura (dívida #56)

### 7.2 Commits não enviados

- [ ] `lab_edp_novo` — **43** commits à frente de `origin/main`
- [ ] `edp_v5` — **9** commits à frente de `origin/feat/telemetria-ranking`

Nunca empurrados sem confirmação explícita. `edp_v5` é repositório **público**.

### 7.3 Dívidas abertas

- [ ] **#54** — render do runtime flow com LLM real. Precondição medida (log
      de produção prova a cadeia de eventos no servidor); falta medir a tela.
- [~] **#55** — `avg_top`: **definição fechada** em
      `edp_v5/docs/DEFINICAO_avg_top.md`. A definição *reforçou* a dívida:
      `avg_top` mistura score com `empty_rate`, e `ranking_score` tem três
      escalas — o `0.010` da tela é RRF (normal, teto 0,016) e seria quase
      ortogonal se fosse cosseno. Faltam os 4 pré-requisitos do §5, e três
      deles tocam o dashboard congelado.
- [~] **#56** — decisão preparada em `edp_v5/docs/DECISAO_probe_por_turno.md`,
      com bloco de assinatura. Achado novo: os **seis** chamadores de
      `is_connected()` usam o valor como guarda, não como relatório de saúde,
      e `health.py:25` já documenta ter recusado o probe pelo mesmo motivo.
      Não implementado: caminho quente do kernel em repositório público.

### 7.4 Outras frentes paradas

- [ ] `PILOTO_ZERO` — 8 documentos pré-registrados, **0 resultados**
- [ ] `exp017` — instrumento (`log-only`) emitindo em produção; assinatura de
      promoção do tratamento continua pendente

---

## 8. Ordem proposta

1. **`TaskService` com persistência** — destrava 7 itens (§1, §2, parte de §3
   e §4). É o que muda mais coisa por linha escrita.
2. Os três endpoints em cima dele: `get_task`, `get_result`, `cancel_task`.
3. Os 7 testes que passam a ser possíveis, mais desconexão e transporte
   indisponível.
4. `correlation_id` e identidade de cliente (§3, os dois parciais).
5. Smoke test do brief de verdade: Router fake no lugar do `PropositorEco`,
   `ProvedorHAR` no lugar do `ProvedorVazio`, consulta do resultado pelo
   mesmo canal.
6. Só então o critério de conclusão — que exige o painel como cliente, e
   portanto uma decisão nova sobre tocar no Exportador.

---

## 9. O que esta rodada fechou, e com que evidência

**Brief: 38 de 39.** Aberto só o §6, que não é meu para fechar.

### O que mudou de arquitetura

`POST /v1/tarefas` deixou de executar dentro da requisição. Agora devolve
**202 + `task_id`**, e `agent_runtime/servico.py` persiste antes de executar,
executa num pool fora da requisição, e responde perguntas depois. Foi essa
única mudança que destravou os sete itens que a §0 apontava.

### Decisões que ficaram no código, não só aqui

- **409, não 200 vazio**, para resultado de tarefa que ainda roda. "Ainda não
  há resultado" é fato diferente de "o resultado é vazio".
- **404, não 403**, para tarefa de outro cliente. 403 confirmaria que aquele
  `task_id` existe, e `task_id` não é segredo — é devolvido a quem submeteu.
- **Cancelamento por exceção** (`Cancelada`), levantada pelo propositor
  embrulhado. O `Executor` embrulha exceção do *provedor*, não do propositor
  (`executor.py:117`), então cancelar por aí não exige que ele aprenda o que é
  cancelamento. A alternativa — devolver `Intencao(concluir=True)` — marcaria
  `CONCLUIDA` uma tarefa que o operador mandou parar.
- **Cancelamento observado entre iterações**, nunca no meio de um provedor:
  matar execução pela metade deixaria observação parcial no registro, que é o
  que `Observacao` frozen existe para impedir.
- **`X-Request-Id` e `X-Correlation-Id` em header.** `TarefaRequest v1` recusa
  campo desconhecido de propósito; pô-los no corpo obrigaria a mudar o
  contrato lógico, que o brief manda manter.
- **`_id_seguro` duplicado** em vez de importado do `auditor` — ver §2.
- **`TETO_SEGUNDOS` mudou de natureza**, de 30 s para 300 s: era o limite do
  que cabia numa requisição síncrona; agora protege o pool, não a conexão.

### Medido, não deduzido

```
suite do lab ............ 517 passed  (490 antes; +23 transporte, +4 smoke)
tests/test_transporte.py . 50 passed
tests/test_smoke_transporte.py .. 4 passed

navegador real, fluxo assincrono completo:
  POST -> 202, task_id T-b768b968
  pagina consulta sozinha -> CONCLUIDA, 1 iteracao, 0 negadas
  2 observacoes com fonte=sessao.har        (HAR real, nao fake em memoria)
  "SEGREDO-DO-HAR" no DOM: False            (redacao antes do cliente)
  "REDIGIDO" presente: True
  GET resultado -> 200
  POST cancelar em tarefa terminal -> 200   (nao e erro)
  outra origem (8011 -> 8010) -> GET e POST BLOQUEADOS pelo navegador

disco:
  /tmp/transp/tarefas/T-b768b968/tarefa.json
  status=CONCLUIDA client_id=default correlation_id=pagina-1788469223657
  started_at e finished_at gravados, observacoes=2
```

### O que continua não feito, e por quê

- **§6, critério de conclusão** — exige o painel do Copiloto como cliente. A
  assinatura de 03/09 escolheu "página separada primeiro" e não autoriza
  tocar no Exportador. Fechar isto é uma **decisão nova**, não uma tarefa
  pendente.
- **Segundo smoke com modelo real** — o brief o marca como opcional e
  posterior. Exige chave de provider.
- **§7 inteiro** — assinaturas, push de commits, execução do piloto e as três
  dívidas. Nenhum é meu para fechar sozinho.
