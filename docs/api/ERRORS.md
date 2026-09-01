# Erros

| HTTP | quando | o que fazer |
|---|---|---|
| `401` | chave ausente ou inválida | conferir `X-API-Key` |
| `404` | auditoria não encontrada **ou de outro cliente** | conferir o `audit_id` |
| `409` | ainda `QUEUED`/`RUNNING` | esperar e consultar `/status` |
| `422` | entrada inválida ou acima do limite | ler `detail.erro` |
| `503` | `/ready` falhou | serviço não está apto |

## `404` não distingue "não existe" de "não é sua"

Responder "existe, mas é de outro cliente" já entrega a existência do id. As
duas situações devolvem a mesma coisa.

## `422` é `INVALID`, não `ERROR`

Entrada ruim é problema da entrada, não falha do serviço. A resposta traz um
`audit_id` registrado com status `INVALID` e o motivo — a tentativa fica no
registro, auditável.

```json
{"detail": {"audit_id": "...", "status": "INVALID",
            "erro": "campos desconhecidos ['top_k']. Ignorar campo em silencio
                     faria a auditoria rodar com configuracao diferente da pedida."}}
```

## Limites

Excedê-los dá `422` com o número e o limite. A auditoria **não roda truncada**:
medir metade do material daria um número sobre outro sistema.

```
max_queries · max_documentos · max_snapshot_bytes
max_request_bytes · max_segundos
```

Configuráveis por cliente.

## `ERROR` nunca é veredito

`ERROR` significa que o **serviço** falhou. Nenhuma conclusão sobre o sistema
auditado pode ser tirada de uma execução assim.
