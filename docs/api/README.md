# Diagnóstico de Retrieval — API

Serviço HTTP para medir o que o seu sistema de retrieval está recuperando.

**Não é auditoria de qualidade.** Ver [O que não fazemos](../auditor/produto/O_QUE_NAO_FAZEMOS.md).

## Subir

```bash
pip install -e ".[http]"
python -m auditor.api --base ./dados_servico --port 8080
```

Criar um cliente e obter a chave (aparece **uma vez**):

```python
from pathlib import Path
from auditor.tenancy import Clientes
print(Clientes(Path("dados_servico/clientes.json")).cria("acme"))
```

## Ciclo completo

```bash
KEY=ak_...

# 1. criar — assíncrono, responde 202
curl -s -XPOST localhost:8080/v1/audits -H "X-API-Key: $KEY" \
  -H 'Content-Type: application/json' -d '{
    "schema": "AuditInput v1",
    "snapshot": "/dados/meu_corpus",
    "queries": "/dados/perguntas.json",
    "protocol": "DIAGNOSTICO",
    "adapter": "cliente",
    "request_id": "meu-id-unico"
  }'
# {"audit_id":"a1b2c3d4e5f6","status":"QUEUED"}

# 2. acompanhar
curl -s localhost:8080/v1/audits/a1b2c3d4e5f6/status -H "X-API-Key: $KEY"

# 3. relatório e manifesto
curl -s localhost:8080/v1/audits/a1b2c3d4e5f6/report -H "X-API-Key: $KEY"
curl -s localhost:8080/v1/audits/a1b2c3d4e5f6/manifest -H "X-API-Key: $KEY"
```

## Garantias

**Nenhum `GET` executa auditoria.** Todos leem artefato já produzido — um `GET`
que recalculasse devolveria, para a mesma URL, um número diferente do que você
recebeu, e o `sha256` do manifesto deixaria de significar alguma coisa.

**Isolamento por caminho.** O `client_id` autenticado entra na raiz dos dados,
então um `audit_id` de outro cliente não existe onde o serviço procura. Não
depende de o código lembrar de comparar.

**Idempotência.** O mesmo `request_id` do mesmo cliente devolve a mesma
auditoria, inclusive depois de reiniciar o serviço.

**A API não muda a régua.** Nenhum parâmetro de requisição altera `top_k`,
protocolo ou ressalva.
