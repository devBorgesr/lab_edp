# Pré-registro — Experimento 007-lab (E7)
## Quanto do repeat_rate de 80% em uso real é topicalidade legítima, e não patologia de retrieval?

> **Régua da Bancada (método):** este documento declara hipótese, condições,
> métricas, dataset e critério de decisão ANTES de qualquer dado. A
> encarnação (`sujeitos/edp/experimentos/exp_e7.py`) espelha este `.md` e é
> CONGELADA após o 1º disparo real — desvios só por anexo datado, nunca por
> reescrita. Mudou a régua ⇒ é o E7b, experimento novo.

**Data de pré-registro: 2026-07-28** (antes do disparo). Primeiro experimento
NATIVO do `lab_edp` — os demais no acervo foram herdados do `edp_v5`.

---

## §1. Motivação (verificada, não assumida)

Três medições, todas com a MESMA fórmula (`retrieval_monitor.py:113-118`,
overlap ≥ min(2,k) sobre pares consecutivos):

- **~80%** — monitor de produção, persistente desde jun/2026, sobre a
  sequência REAL de turnos (`EXP017_FASE0.md`, item 1 da Motivação).
- **0,0%** — exp017/T5, 14 queries sintéticas em ordem intercalada
  (`EXP017_FASE0.md` §2, linha "intercalada | OFF").
- **15,4%** — exp017/E6, as MESMAS 14 queries em ordem agrupada
  (`EXP017_FASE0.md` §2, linha "agrupada | OFF"), com predição pré-dado
  batendo exata.

Mesma fórmula, mesmo store, mesmo `top_k`. A única variável que difere é a
**sequência**: uso real tem continuidade tópica; as listas sintéticas foram
construídas para variar. A hipótese H2-C foi registrada pré-dado no E6 do
`PRE_REGISTRO_EXP017.md` e ficou sem teste — este experimento a testa.

## §2. Hipóteses (declaradas antes do dado)

**H1 (topicalidade domina):** parte substancial do repeat_rate observado em
uso real é comportamento CORRETO — turnos consecutivos sobre o mesmo assunto
devem recuperar as mesmas memórias. Predição: `gap ≥ 15pp`.

**H0 (patologia):** o sistema devolve os mesmos itens independentemente de
adjacência tópica ("favoritos"). Predição: `gap ≤ 5pp`.

H0 vencer é achado válido, não fracasso: promoveria a repetição cross-turn de
"métrica mal interpretada" para defeito real, e justificaria o trabalho de
write-side dedup e despriorização de dominância que hoje está na fila sem
prioridade.

## §3. Condições (mesmo store, mesmos turnos, só a ORDEM muda)

| rótulo | papel | descrição |
|---|---|---|
| `real` | tratamento | sequência real de turnos, ordem cronológica reconstruída por timestamp |
| `shuffled` | controle negativo | os MESMOS turnos, ordem embaralhada (seed congelada) — destrói adjacência tópica mantendo o conjunto |
| `aleatoria` | referência neutra | expectativa sob permutação, calculada da matriz completa (não é uma rodada; é aritmética sobre `real`) |

O controle negativo é o coração do desenho: se `shuffled` render o mesmo
repeat_rate que `real`, a adjacência tópica não explica nada e H0 vence. Se
`real` for muito maior, a ordem cronológica carrega o sinal e H1 vence.

## §4. Dataset (CONGELADO)

Store: cópia read-only de `C:\edp_data_fase0` (133 episódicas, 51 semânticas,
scope `cognitive`) — NUNCA `C:\edp_data`.

Regra determinística de construção da sequência, congelada aqui:
1. Ler `episodic.json` do scope `cognitive`, ordenar por `timestamp` crescente.
2. EXCLUIR entries cujo texto comece com `[session_summary]` — não são turnos
   de conversa; são artefatos de consolidação escritos fora de banda.
3. EXCLUIR entries sem texto no formato `Q: ... A: ...` (form-check, regex
   `^\s*Q:\s*.+\bA:\s*` com DOTALL) — aplica o princípio "turno se identifica
   por FORMA, nunca por source_type" (`edp_metodologia.md`, seção final).
4. A query de cada turno é o trecho após `Q:` até o primeiro `A:`.
5. Resultado: lista ordenada de queries, salva em `e7_sequencia.jsonl` ANTES
   de qualquer medição, com `sha256` do arquivo registrado no relatório.

Se a lista resultante tiver **n < 20 turnos**, o experimento PARA e reporta
poder insuficiente — não roda com n pequeno para "ver o que dá".

## §5. Métricas (definidas antes)

- **Binário:** `overlap ≥ min(2, k)` entre pares consecutivos — espelha
  `retrieval_monitor.py:113-118`, é a métrica que gerou os 80% históricos.
- **Contínuo:** `|∩| / k`, média sobre pares consecutivos (emenda E2 do
  exp017 — o binário satura com k pequeno).
- **Matriz completa** par-a-par, para calcular a referência neutra.
- **Referência neutra:** pares ordenados que cruzam `min(2,k)` dividido pelo
  total de pares ordenados; e média dos `m[i][j]` fora da diagonal para o
  contínuo (convenção do E6, `EXP017_FASE0.md`).
- **gap := repeat(real) − repeat(shuffled)**, na métrica binária.

Agregação: proporção simples, com intervalo de Wilson 95% quando n ≥ 20
(via `bancada/scorer.py::wilson`).

## §6. Critério de decisão (travado)

| resultado | veredito |
|---|---|
| `gap ≥ 15pp` | **H1 — TOPICALIDADE DOMINA.** Os 80% são majoritariamente comportamento correto. Consequência registrada: "reduzir repeat_rate" deixa de ser objetivo válido, e a série histórica do monitor precisa de reinterpretação, não de otimização. |
| `gap ≤ 5pp` | **H0 — PATOLOGIA.** A repetição independe de adjacência tópica. Consequência: write-side dedup e despriorização de dominância sobem na fila com justificativa medida. |
| `5pp < gap < 15pp` | **MISTO.** Reportar os três brutos, não classificar por eliminação. |

Os cortes de 15pp/5pp são os MESMOS congelados em 19/07 no
`PRE_REGISTRO_EXP017.md` — reusados deliberadamente, não escolhidos agora
para caber no resultado.

Critério de validade do instrumento (independente do veredito): a
referência neutra calculada deve cair ENTRE `shuffled` e `real` se H1 for
verdadeira. Se `shuffled` divergir muito da referência neutra, o shuffle não
está destruindo a adjacência como esperado — achado sobre o instrumento.

## §7. Anti-mock e isolamento

- Mede o retrieve REAL: `MemoryStore.retrieve(query, top_k=5, min_score=0.20)`
  via o adaptador `sujeitos/edp/adaptador.py::SujeitoEDP.consultar` — nenhuma
  reimplementação da lógica de recuperação.
- Sessão isolada `__lab__<uuid>` via `bancada/isolamento.py::experimental_session`,
  purgada ao fim; `verify_no_leak` compara fingerprint da produção antes/depois.
- `restore()` ANTES de cada query (o retrieve muta `acessos`/`ultimo_acesso`),
  padrão herdado de `suite_regressao_fase1.py`.
- A análise consome o export JSONL via `bancada/auditoria.py` — instrumento já
  existente e testado, não código novo de métrica.

## §8. Constantes congeladas (espelhadas em `exp_e7.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"E7"` |
| `TOP_K` | `5` |
| `MIN_SCORE` | `0.20` |
| `SEED_SHUFFLE` | `20260728` |
| `MIN_TURNOS` | `20` |
| `CORTE_H1_PP` | `15.0` |
| `CORTE_H0_PP` | `5.0` |
| `PREFIXO_EXCLUIDO` | `"[session_summary]"` |
| `FORM_CHECK` | `r"^\s*Q:\s*.+\bA:\s*"` (DOTALL) |
| `SCOPE` | `"cognitive"` |

## §9. Limitação declarada pré-dado

A reconstrução por timestamp assume que a ordem de escrita aproxima a ordem
conversacional. Entries escritas fora de banda (consolidação, promoção) podem
violar isso — a exclusão do §4 mitiga os casos conhecidos, não todos. Se o
veredito for MISTO, esta limitação é a primeira suspeita a investigar, não o
fenômeno.

Além disso: a cópia `fase0` é um recorte do store de produção. O veredito vale
para o corpus medido; extrapolação para produção viva é inferência, não
resultado.
