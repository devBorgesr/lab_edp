# Checklist — o que falta no transporte, e o que falta em volta

**03/09/2026.** Medido contra o brief da etapa de transporte, item por item,
depois do commit `98269ed`. Não é estimativa: cada linha marcada `[x]` tem
teste ou medição por trás, e cada `[ ]` foi conferida como ausente no código.

**Estado do brief: 19 de 39 feitos, 3 parciais, 17 ausentes.**

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

- [x] `submit_task(request) -> task_id` — `POST /v1/tarefas`.
      **Ressalva:** funde submit + run + result. Devolve `task_id`, mas
      também já devolve o resultado, porque executa dentro da requisição.
- [ ] `get_task(task_id) -> estado`
- [ ] `get_result(task_id) -> resultado`
- [ ] `cancel_task(task_id) -> estado`

## 2. TaskService com resultado persistido — 0 de 1

- [ ] `TarefaRequest → validação → Tarefa → Executor → resultado persistido`.
      Hoje o resultado é devolvido e esquecido; nada toca o disco.
      `auditor/jobs.py` já resolveu este problema neste repositório —
      máquina de estados (`TRANSICOES`) e escrita atômica (`tmp + os.replace`).
      Reaproveitar o padrão, não reinventar.

## 3. Requisitos de segurança — 8 de 12, 2 parciais

- [x] handshake / autenticação local — `Bearer` + `hmac.compare_digest`;
      servidor recusa subir sem `AGENT_RUNTIME_TOKEN`
- [~] **identificação do cliente** — hoje é um token compartilhado único, sem
      identidade por cliente. O brief pede identificar *quem* mandou.
- [x] validação de `TarefaRequest v1` — `requisicao.valida`
- [x] limite de tamanho da mensagem — `TETO_BYTES` = 64 KiB, 413
- [x] timeout — `TETO_SEGUNDOS` = 30, recusado na entrada
- [x] rejeição de schema desconhecido
- [x] rejeição de campos desconhecidos
- [x] rejeição de capacidades acima do teto L0
- [ ] **isolamento entre tarefas** — sem estado persistido não há o que
      isolar, e portanto também não há prova de isolamento
- [~] **correlation / task ID** — `task_id` existe e volta na resposta;
      `correlation_id` do cliente não existe
- [ ] **tratamento de desconexão** — cliente que cai no meio da execução
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
- [~] task_id / correlation_id — `task_id` é asserido no caminho feliz;
      não há `correlation_id` nem teste dele
- [ ] **desconexão**
- [ ] **duas tarefas simultâneas sem mistura de estado**
- [ ] **consulta do estado**
- [ ] **consulta do resultado**
- [ ] **cancelamento**
- [ ] **idempotência / reenvio do mesmo request**
- [ ] **transporte indisponível**
- [x] bridge não exposto além do necessário

## 5. Smoke test real — 2 de 5

- [x] iniciar o Python Runtime — `python3 -m agent_runtime --propositor eco`
- [x] enviar `TarefaRequest v1` pelo transporte real — Firefox headless,
      mesma origem, token certo → 200, `CONCLUIDA`, observação com hash
- [ ] **usar um Router fake primeiro** — nenhum Router foi usado.
      `transporte.py` tem **zero** referências a `Roteador`; `PropositorEco`
      não passa por Router nenhum.
- [ ] **executar tarefa L0 contra HAR** — rodou com `ProvedorVazio`. A flag
      `--har` existe e nunca foi exercitada; nenhum teste usa `ProvedorHAR`
      pelo transporte.
- [ ] **consultar o resultado pelo mesmo canal** — não há canal de consulta

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

### 7.2 Commits não enviados

- [ ] `lab_edp_novo` — **43** commits à frente de `origin/main`
- [ ] `edp_v5` — **9** commits à frente de `origin/feat/telemetria-ranking`

Nunca empurrados sem confirmação explícita. `edp_v5` é repositório **público**.

### 7.3 Dívidas abertas

- [ ] **#54** — render do runtime flow com LLM real. Precondição medida (log
      de produção prova a cadeia de eventos no servidor); falta medir a tela.
- [ ] **#55** — `avg_top` sem definição fechada. Bloqueia o gráfico de
      tendência de retrieval, que já teria dado disponível no payload.
- [ ] **#56** — `is_connected()` faz round-trip de rede no caminho do turno:
      21,782 s medidos, ~44% de um turno de 49,6 s.

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
