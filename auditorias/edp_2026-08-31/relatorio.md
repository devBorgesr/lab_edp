# Auditoria `b3f44a68ce79` — REL-001

**Status: BLOCKED**

## Resumo executivo

Esta auditoria **não produziu métricas**. Uma ou mais pré-condições de validade não foram satisfeitas, e o pipeline foi interrompido antes de qualquer cálculo.

Isto não é uma falha do serviço: é o resultado que o serviço deve entregar quando o sistema auditado não sustenta o protocolo pedido.

## Motivo

**`ranking.cardinalidade` — BLOCKED**

50 de 50 queries nao alcancam 50 documentos distintos (min=30, mediana=37.0, max=41). Os slots estao cheios; os documentos, nao.

```
slots = 50
ids_distintos = 30
exigido = 50
ids_repetidos = 20
queries = 50
distintos_min = 30
distintos_mediana = 37
distintos_max = 41
queries_reprovadas = 50
```

*Este check detecta:* duplicacao no indice consumindo a janela top-k: slots cheios, documentos distintos insuficientes

## O que NÃO foi concluído

Nenhuma métrica foi calculada. Especificamente:

- etapa `estratos` — não executada
- etapa `amostragem` — não executada
- etapa `julgadores` — não executada
- etapa `estatistica` — não executada

Qualquer número que apareça em outro lugar sobre este sistema **não veio desta auditoria**.

## Próximo passo

Decisão do responsável, entre alterar o objeto auditado e alterar o protocolo. As duas mudam o que está sendo medido e nenhuma pode ser adotada em silêncio.

## Verificações

| check | estado | barra? | detecta |
|---|---|---|---|
| `procedencia.snapshot_tem_hash` | PASS | não | corpus trocado sob o mesmo caminho entre a auditoria e a contestacao |
| `ranking.cardinalidade` | BLOCKED | **sim** | duplicacao no indice consumindo a janela top-k: slots cheios, documentos distintos insuficientes |

## Etapas

| etapa | estado |
|---|---|
| `snapshot` | PASS |
| `entrada` | PASS |
| `retriever` | PASS |
| `ranking` | BLOCKED |
| `estratos` | PENDING |
| `amostragem` | PENDING |
| `julgadores` | PENDING |
| `estatistica` | PENDING |

## Procedência

```
dir = /tmp/auditoria_wj5kgj5u/sessions/default_cognitive
store = /tmp/auditoria_wj5kgj5u/sessions/default_cognitive
sha256_episodic = d64fcc74a0c7e9b08eb3972129a7f5689b008912c3e32abce9e386477d1703be
sha256_semantic = 632a7f228045f89cc92bf98695a4f664e181e214a93236035f0af1a635eab27d
retriever.top_k = 50
retriever.origem = EDPAuditavel
manifesto.sha256 = 9366c32d058d752451d5a2c4544cedc959568b795df9f483413331cd06e1e2f6
```

---

Manifesto completo em `manifesto.json`. Modo: `AUDIT`. O sha256 acima cobre o manifesto inteiro e permite contestar cada número deste relatório.