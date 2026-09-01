# Referência

Autenticação: cabeçalho `X-API-Key`. A chave nunca vai em URL nem em log.

## `POST /v1/audits` → `202`

```json
{
  "schema": "AuditInput v1",
  "snapshot": "/caminho/do/corpus",
  "queries": "/caminho/perguntas.json",
  "protocol": "DIAGNOSTICO",
  "adapter": "cliente",
  "options": {},
  "request_id": "opcional"
}
```

Resposta: `{"audit_id": "...", "status": "QUEUED"}`, ou
`{"audit_id": "...", "status": "...", "idempotente": true}`.

Campo desconhecido é **recusado**, não ignorado — um `protocolo` no lugar de
`protocol` rodaria com a régua errada em silêncio.

## `GET /v1/audits`

As auditorias **do cliente autenticado**.

## `GET /v1/audits/{id}/status`

```json
{"audit_id": "...", "status": "COMPLETE",
 "protocol": "DIAGNOSTICO v1", "adapter": "cliente",
 "service_version": "0.4.0",
 "created_at": "...", "updated_at": "...", "erro": null}
```

## `GET /v1/audits/{id}` · `GET /v1/audits/{id}/manifest`

O `AuditResult v1` original, como gravado. `409` enquanto `QUEUED`/`RUNNING`.

## `GET /v1/audits/{id}/report?tipo=executive|technical`

Markdown. `404` se aquele relatório não existe — um dry-run não grava relatório.

## `GET /v1/protocols` · `GET /v1/protocols/{nome}`

As réguas, com `escopo`, `tipo` e `versao`. Hoje: `DIAGNOSTICO` (escopo
`diagnostico`) e `BASICO` (demonstrativo).

`REL-001` **não é exposto**: o experimento está bloqueado, e publicar a régua
sugeriria que ela produz resultado.

## `GET /health` · `GET /ready`

`health`: o processo está vivo. `ready`: workspace gravável, registro de
clientes, protocolos e adaptadores disponíveis. Nenhum dos dois executa
auditoria.

## Estados

```
QUEUED → RUNNING → COMPLETE | READY | BLOCKED | INVALID | ERROR
```

Estado terminal não volta. `COMPLETE → RUNNING` é recusado pelo serviço.

| estado | significado |
|---|---|
| `COMPLETE` | a régua executou; há resultado |
| `READY` | pré-condições ok; a régua não tinha métrica configurada |
| `BLOCKED` | **aquela régua** não pôde ser executada sobre **aquele sistema** |
| `INVALID` | a entrada não é auditável |
| `ERROR` | falha do **serviço** — nunca um veredito sobre o seu sistema |

`BLOCKED` não é erro. Você ainda recebe as medições descritivas, desde que o
ranking tenha procedência provada.
