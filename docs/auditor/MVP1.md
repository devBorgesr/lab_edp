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
