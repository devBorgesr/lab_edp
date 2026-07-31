# VALIDACAO_FIX_TOXIC_GUARDS.md — exp018 como oráculo externo

Data: 30/07/2026. Sujeito: EDP branch `fix/toxic-guards` (`057f8b8`, a
partir de `788d7f5`). Instrumento: exp018 INALTERADO — mesmo harness,
mesmo dataset, mesmos ids, mesmo critério congelado em `f578b45`.
Resultados: `exp018_pos_fix.json` (o pré-fix segue em
`exp018_resultados.json`, intocado).

## Antes vs depois

| Cond. | Função | flag | ANTES | DEPOIS | Esperado |
|---|---|---|---|---|---|
| C1 | `consolidate()` | 1 | 4/4 | **0/4** | 0 ✓ |
| C2 | `consolidate()` | 0 | 4/4 | **0/4** | 0 ✓ |
| C3 | `promote_only()` | 1 | 0/4 | **0/4** | 0 ✓ |
| C4 | `promote_only()` | 0 | 4/4 | **0/4** | 0 ✓ |
| C5 (+) | ambas | 1 | 2 e 2 | **2 e 2** | não regride ✓ |
| C6 (−) | ambas | 1 | 0 e 0 | **0 e 0** | 0 ✓ |
| C7 | `consolidate()` | 1 | fundiu, promovida, sem carimbo | **fundiu, NÃO promovida** | barrada ✓ |

Veredito do script: **H1 False · H2 False · H3 False · H0 True**.
As três hipóteses do exp018 deixaram de se sustentar — que é exatamente o
que "o furo fechou" significa neste desenho. `leak_ok=True` nas 9 sessões.

## Como cada mudança foi provada

- **T1+T2 (separação de flags):** C4 de 4→0. Com
  `EDP_WRITE_PROVENANCE=0`, a guarda continua ativa porque agora depende de
  `EDP_TOXIC_GUARDS`. É o achado do
  `ACHADO_FLAG_UNICA_TOXICIDADE.md` fechado por medição.
- **T3 (guarda em `consolidate()`):** C1 e C2 de 4→0, nas duas posições de
  flag.
- **T4 (propagação no merge):** C7 `promovida_fundida` de True→False,
  mantendo `fundiu=True, merged_from=2`. **Confirmado por consequência:**
  a guarda de T3 só pode ter barrado a fundida se o carimbo foi propagado —
  sem T4, `merged.get("answer_class")` seria `None` e ela promoveria.
- **Não-regressão:** C5 promovendo 2 em ambas as funções. Sem isso, "tudo
  zero" seria compatível com um fix que simplesmente quebrou a promoção.

## Predição do arquiteto REFUTADA na forma (não no mecanismo)

Previ `answer_class_presente=True` em C7. Veio `None`, porque o harness lê
esse campo da entry fundida **no semântico** — e ela não está lá, tendo
sido barrada. A predição estava mal formulada: o sinal de sucesso do T4 é
`promovida_fundida=False`, não o carimbo visível. Registrado.

Efeito colateral para vereditos futuros: com a guarda ativa,
`answer_class_presente` fica `None` em C7 e não distingue "barrada" de "não
fundiu" — quem faz essa distinção é `fundiu`, lido do episódico. Mais uma
vez a separação fundiu/promovida (refinamento do executor) é o que mantém
a condição legível depois que o comportamento muda.

## Ressalvas herdadas

- Validação **sintética**: prova que o mecanismo não vaza mais, não que não
  vazava em produção (o store não tem carimbo — ver
  `VEREDITO_EXP018.md` §3 item 9).
- Confound da Dívida #49 continua eliminado por desenho (textos do dataset
  evitam as frases-gatilho).
- Pendência do fix: `merge_cluster()` agora grava `answer_class: null` nas
  fundidas limpas (chave antes ausente). Inócuo no comportamento, mas muda
  a forma no disco e afeta contagens de "entries sem carimbo". Decisão do
  pesquisador se vale a linha extra para omitir a chave quando `None`.

## Estado da fila do backfill

Os quatro pré-requisitos do backfill de produção (três do
`VEREDITO_EXP018.md` + a separação de flags) estão **fechados e validados**.
O backfill de produção deixa de ter bloqueio conhecido — o que não o torna
automático: continua sendo decisão do pesquisador, com backup obrigatório,
e o `ESTADO_EXP012.md` já define o protocolo.