# `AuditInput v1`

```json
{
  "schema":     "AuditInput v1",
  "snapshot":   "/caminho/do/corpus",
  "queries":    "/caminho/perguntas.json",
  "protocol":   "DIAGNOSTICO",
  "adapter":    "sintetico",
  "options":    { "mode": "AUDIT" },
  "request_id": "opcional-para-idempotencia"
}
```

| campo | obrigatório | nota |
|---|---|---|
| `schema` | não | default `AuditInput v1`; outra versão é recusada |
| `snapshot` | **sim** | diretório do corpus; é hasheado e vira identidade |
| `queries` | **sim** | lista de perguntas, ou `{"queries": [...]}` |
| `protocol` | **sim** | `DIAGNOSTICO` ou `BASICO` |
| `adapter` | **sim** | o tradutor do seu sistema |
| `options` | não | objeto livre |
| `request_id` | não | mesma id não cria duas auditorias |

**Campo desconhecido é recusado**, não ignorado. Um `protocolo` escrito no lugar
de `protocol` rodaria com a régua errada em silêncio, e você só descobriria
lendo o manifesto.

## Perguntas

```json
{"queries": [
  {"id": "q001", "query": "como configurar o índice?", "dominio": "infra"},
  "ou apenas a string da pergunta"
]}
```

Use perguntas **reais** do seu domínio. Perguntas inventadas medem o retriever
contra um uso que ninguém faz.

## `AuditResult v1`

17 campos obrigatórios, entre eles: `status`, `protocolo_identidade`,
`snapshot` (com sha256), `dataset` (com sha256), `checks`, `medicoes`,
`resultado`, `custos`, `privacidade`, `sha256_manifesto`.

`resultado` é `null` sob `BLOCKED` — e o manifesto traz `NAO_HA_RESULTADO`
dizendo por quê.
