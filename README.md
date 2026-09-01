# Diagnóstico de Retrieval

Medição técnica reproduzível do que o seu sistema de retrieval está
recuperando — com evidências, hashes e limites explícitos.

**Não é auditoria de qualidade.** Ver [`O que não fazemos`](docs/auditor/produto/O_QUE_NAO_FAZEMOS.md).

## Instalar

```bash
pip install -e .            # engine + CLI, sem dependência externa
pip install -e ".[http]"    # + API HTTP
auditor --version
```

## Usar

```bash
auditor check --input <corpus> --queries <perguntas.json> \
              --protocol DIAGNOSTICO --adaptador cliente
auditor run   ... --output ./auditorias
auditor status --output ./auditorias
auditor report <audit_id> --output ./auditorias
```

`check` é dry-run: responde `READY` ou `BLOCKED` em segundos, sem processar.

## O que você recebe

`manifest.json` (fonte de verdade, com `sha256`), relatório executivo de uma
página, relatório técnico, e o registro de cada verificação com o defeito que
ela detecta.

## Documentação

| | |
|---|---|
| [Como funciona](docs/auditor/produto/COMO_FUNCIONA.md) | o fluxo |
| [O que você recebe](docs/auditor/produto/O_QUE_VOCE_RECEBE.md) | os artefatos |
| [O que não fazemos](docs/auditor/produto/O_QUE_NAO_FAZEMOS.md) | os limites |
| [Quickstart](docs/auditor/onboarding/QUICKSTART.md) | integrar em 5 minutos |
| [Contrato](docs/auditor/SERVICE_CONTRACT.md) | normativo |
| [Claims](docs/auditor/CLAIMS.md) | o que pode ser afirmado |
| [API](docs/api/README.md) | HTTP |

## Estado

`DIAGNOSTICO v1` mede o material recuperado. Não mede qualidade de resposta,
Recall@K nem relevância, e não certifica nada.

`REL-001` — a régua experimental de relevância — está **bloqueada**, e nenhum
resultado seu foi validado.
