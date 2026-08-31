# MVP-1 — produto técnico operacional

**31/08/2026.** O MVP-0 provou que o auditor sabe dizer *"não vou medir isto"*.
O MVP-1 transforma isso em serviço utilizável por terceiros — **sem fingir que
o REL-001 está validado**.

`REL-001` continua **BLOQUEADO**. `Recall@K` comercial continua **não
autorizado**. Reddit continua **fora**.

## A decisão de produto que destravou o resto

O portão do MVP-0 ("nada sob `BLOCKED`") mataria a oferta, porque a auditoria
real do EDP termina em `BLOCKED`. A saída não foi afrouxar o portão — foi
separar duas classes de número:

| | `resultado` | `medicoes` |
|---|---|---|
| o que é | métrica **de protocolo** | fato observável sobre o material recuperado |
| exige | **todas** as pré-condições | apenas ranking com procedência provada |
| existe sob `BLOCKED`? | **não** | **sim** |
| autoriza afirmar qualidade? | no escopo do protocolo | **não** |

Confundir nas duas direções seria erro: vender medição como qualidade não se
segue; publicar κ sob pré-condição quebrada é o que a rodada anterior quase fez.

## As cinco medições — a oferta atual, sem Recall@K

Cada uma carrega o referente: o que mede, N, k, snapshot, fonte, e IC 95% por
bootstrap **sobre a query**, não sobre o item.

| medição | EDP (N=50) |
|---|---|
| `cardinalidade_do_ranking` | 37 documentos distintos por query (slots = 50) |
| `duplicacao_intra_query_por_id` | 0,26 dos slots |
| `duplicacao_por_texto` | mediana 0 — **5 queries afetadas, máx 0,37** |
| `sobreposicao_cross_query` | Jaccard 0,283 (N = 1.225 pares) |
| `razao_score_topo_cauda` | 1,81 |

**Sobre a terceira linha.** A mediana é 0 e o achado é real: o efeito é
concentrado em 10% das queries. A mediana é exatamente a grandeza que esse
defeito não move (`NORTE §4.15`), então a medição passou a carregar
`queries_afetadas` e `max` obrigatoriamente. Um relatório que mostrasse só a
mediana esconderia o achado inteiro.

## Comandos

```bash
python -m auditor check --input <snapshot> --protocol REL-001 --queries <q.json>
python -m auditor run   --input <snapshot> --protocol REL-001 --queries <q.json> \
                        --output <dir>
```

`check` é o dry-run: responde `READY` ou `BLOCKED` **sem executar julgador e sem
calcular métrica de protocolo**. É o comando que teria barrado o REL-001 antes
das 492 chamadas de API.

Exit codes: `0` COMPLETE/READY · `2` BLOCKED · `3` INVALID · `4` erro operacional.

## Critério de aceitação (item 16) — conferido

| | |
|---|---|
| enviar snapshot → executar | ✅ |
| receber READY ou BLOCKED | ✅ |
| obter manifesto e relatório | ✅ `manifesto.json`, `relatorio.md`, `relatorio_tecnico.md`, `artefatos/` |
| reproduzir hashes | ✅ `sha256` do manifesto, estável entre chamadas |
| ver quais checks passaram | ✅ `artefatos/checks.json` |

**Os oito erros que não podem passar em silêncio** — um teste nomeado para cada:
ranking fabricado · id duplicado · controle contaminado · snapshot sem hash ·
artefato inválido · score inválido · procedência ausente · métrica sob `BLOCKED`.

213 testes passando.

## Dois defeitos achados no próprio MVP-1

**`procedencia_ok` aprovava lista vazia.** `_fecha()` roda após cada etapa, e
`all()` sobre lista vazia é `True` — a medição saía calculada antes de o check
de procedência ter rodado, sobre ranking fabricado. Era precisamente o que a
propriedade existia para impedir. Agora os checks exigidos precisam estar
**presentes e PASS**.

**A procedência não era registrada quando outro check falhava.** Com a
cardinalidade barrando, a prova de que o ranking é real nunca entrava no
manifesto, e as medições desapareciam — a auditoria perdia a entrega comercial
justamente no caso em que ela mais importa. Agora é registrada sempre.

## Privacidade (item 10)

Query e documento **nunca** entram em artefato em claro por caminho automático —
o que entra é hash. Texto em claro exige `--exemplos-em-claro`. **Segredo é
removido nos dois modos**: chave de API, token, JWT, chave privada, e-mail, CPF.
O operador pode autorizar mostrar texto do cliente; não pode autorizar vazar
credencial. Há teste garantindo que o manifesto de uma auditoria real não
carrega texto de query nem de documento.

## Custo (item 12)

Tempo por etapa, chamadas ao modelo, tokens. A auditoria real do EDP levou
**55,8 s**. O custo em dólar sai de tabela **explícita**; sem preço registrado o
campo é `null` com o motivo — zero seria mentira.

## Não construído, de propósito

API HTTP (item 13 — só depois do CLI estável) · dashboard (item 14) ·
Question Mining/Reddit (item 18) · execução de juiz no pipeline ·
isolamento entre clientes e retenção · correção do `_hybrid_index`.

## Pendente, e não é do agente

`docs/auditor/DECISAO_RANKING.md` — as três opções (A produção como está,
B deduplicado explícito, C corrigir o índice) com impacto em protocolo,
comparabilidade histórica e leitura comercial. **Enquanto o registro de decisão
estiver em branco, o REL-001 permanece bloqueado.**


---

# MVP-1 — segunda etapa (31/08, tarde)

## A correção que mudou o significado do output

`min_distintos = 50` é uma escolha do **REL-001**, não uma propriedade de RAGs.
O serviço detecta que um sistema não a satisfaz e devolve `BLOCKED` — mas a
única afirmação autorizada é:

> não pode ser auditado **sob o protocolo REL-001 v1**

nunca *"este RAG é impossível de auditar"*. Agora isso é propriedade do código:
o motivo de cada bloqueio nomeia a régua, o relatório diz *"outra régua pode se
aplicar a ele"*, e há teste que reprova o relatório se ele afirmar demais.

## Protocolo tem identidade e tipo

```
REL-001 v1   experimental    o experimento está BLOQUEADO; nada seu foi validado
BASICO  v1   demonstrativo   não sustenta afirmação científica, não certifica
```

Duas versões **nunca** são a mesma régua — `identidade` é `nome vN`, e o
relatório carrega `protocolo_identidade` e `versao_servico`.

## Dois defeitos reais achados nesta etapa

**O IC não era do estimador reportado.** Todas as medições reportam a
**mediana**, e o bootstrap reamostrava a **média**. Apareceu na cara:
`jaccard_cross_query` valia 0 com IC [0,029; 0,042] — um intervalo que não
contém o próprio ponto. Corrigido: o bootstrap reamostra a mediana, e há teste
verificando que o ponto cai dentro do intervalo em toda medição.

**O teste de caminho pessoal violava o `§4.15`.** Ele reprovava
`procedencia.py` porque a **docstring** menciona `edp_data_todo/` ao explicar
por que procedência importa. Menção em prosa não é dependência — a grandeza
certa é o literal que o programa executa. Agora usa AST e ignora docstrings.

## Metadados viraram requisito, não convenção

`Medicao` **falha na construção** sem `N` válido, sem `o_que_mede`, sem
`unidade`, sem `fonte`. Com IC, exige método e seed. **Sem IC, exige dizer por
quê** — ausência de intervalo se declara, não se omite.

E `sobreposicao_cross_query` virou **`jaccard_cross_query`**, com "Jaccard
mediano entre PARES" na descrição. Este projeto já carregou 15,4%, 15,7%, 24,8%
e 25,5% de "duplicação" que pareciam contraditórios e mediam coisas diferentes;
o nome passa a carregar a definição.

## Procedência de entrada é registrada na abertura

O `dataset` (hash das queries, origem) era calculado na etapa `amostragem` — e
sumia quando o pipeline bloqueava antes. O manifesto de uma auditoria bloqueada
não dizia **sobre quais queries** o bloqueio aconteteu. Fato de entrada não
depende de o pipeline chegar lá.

Esse campo é também o **ponto de extensão do item 18**: quando existir gerador
de perguntas, ele entra como fonte com procedência própria — trocar a fonte
muda `sha256_queries` e fica visível no manifesto.

## O caso real do EDP

```
protocolo   REL-001 v1 (experimental) · serviço 0.2.0 · adaptador edp-1
dataset     50 queries, sha 180586f4cf9c
status      BLOCKED          resultado    None
```

| medição | valor | IC 95% | N |
|---|---|---|---|
| `cardinalidade_do_ranking` | 37 | [37; 38] | 50 |
| `duplicacao_intra_query_por_id` | 0,26 | [0,24; 0,26] | 50 |
| `duplicacao_por_texto` | 0 — **5 queries afetadas, máx 0,37** | [0; 0] | 50 |
| `jaccard_cross_query` | 0,283 | [0,276; 0,290] | 1.225 |
| `razao_score_topo_cauda` | 1,81 | [1,75; 1,86] | 50 |

**Store imutável** — `sha256` do `episodic.json` idêntico antes e depois, com
teste de regressão de duas execuções.

## Demonstrações públicas (item 16)

`python -m auditor.demo demos` — corpus sintético, nenhum dado de cliente:

```
demos/A_completa    COMPLETE    resultado presente
demos/B_bloqueada   BLOCKED     resultado None, 5 medições entregues
```

A B é a comercialmente importante: mostra que o serviço não inventa resultado.

## O "Done" do item 19

| | |
|---|---|
| instalar | ✅ núcleo importa sem `edp`; teste em subprocesso |
| fornecer snapshot e queries | ✅ `--input`, `--queries` |
| executar `check` → READY/BLOCKED | ✅ dry-run, sem julgador |
| executar `run` → manifesto e relatórios | ✅ + `artefatos/checks.json` |
| reproduzir hashes | ✅ estável entre execuções |
| entender PASS/FAIL/BLOCKED | ✅ cada check declara o que detecta |
| nenhum defeito do REL-001 passa em silêncio | ✅ oito testes nomeados |

Não há caminho pessoal em literal executável — verificado por AST em todo
`auditor/`. **250 testes.**

## Reprodutibilidade — declarada, não fingida

Mesma entrada produz as mesmas medições, os mesmos checks e o mesmo conjunto de
rankings. **O que muda entre execuções**: `audit_id`, `criado_em`, `custos`
(tempo) e o `sha256_manifesto` que os cobre. Há teste que **falha** se algo
além disso variar — fingir determinismo perfeito seria pior que declarar.

## Continua fora

API HTTP · dashboard · Reddit/Question Mining · juiz no pipeline · isolamento
entre clientes · correção do `_hybrid_index`.

**E continua valendo:** a existência do MVP-1 **não** é argumento de que
Recall@K está validado. O registro em `DECISAO_RANKING.md` segue em branco.
