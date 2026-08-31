# Contrato do serviço de auditoria

**v1 — 31/08/2026.** O que o serviço aceita, o que devolve, e o que ele se
recusa a fazer. Este documento é normativo: divergência entre ele e o código é
defeito do código.

## INPUT

| campo | obrigatório | descrição |
|---|---|---|
| `snapshot` | sim | diretório do corpus. Hasheado; identifica o objeto auditado |
| `queries` | sim | lista de perguntas reais do domínio do cliente |
| `protocol` | sim | régua congelada (`REL-001`, `BASICO`) |
| `adaptador` | sim | tradutor do sistema do cliente para `SistemaAuditavel` |
| `mode` | não | `AUDIT` (default) ou `DIAGNOSTIC` |

O sistema auditado precisa implementar quatro métodos:

```python
snapshot_dir          # diretório do corpus
consulta(query, k)    # -> [(doc_id, score), ...]  ranking REAL
texto(doc_id)         # -> str
controle_para(query)  # -> [doc_id, ...]  candidatos a controle negativo
```

**`consulta` devolve `(doc_id, score)`, não `doc_id`.** Não é preferência de
formato: o score é a prova de que o ranking saiu de um retriever. Uma lista de
ids nua não prova nada, e foi assim que a rodada anterior deste projeto perdeu
500 pares e 492 rótulos.

## OUTPUT

```
manifesto.json           tudo que permite contestar
relatorio.md             executivo — quatro perguntas
relatorio_tecnico.md     evidência completa
artefatos/checks.json    cada verificação, estado e evidência
```

## ESTADOS

| estado | significado | métrica de resultado? |
|---|---|---|
| `PASS` | executou e passou | sim |
| `FAIL` | executou e o sistema auditado **reprovou** | **sim — é resultado do cliente** |
| `BLOCKED` | não pôde executar; pré-condição quebrada | **não** |
| `INVALID` | a entrada não é auditável | **não** |
| `PENDING` | não executou | **não** |

> **`BLOCKED`, `INVALID` e `PENDING` nunca possuem métrica de resultado.**

Isso é garantido por três travas independentes: o pipeline interrompe;
`publica_resultado()` levanta; `resultado` levanta na leitura.

`FAIL` × `BLOCKED` é a distinção que mais importa. Um serviço que as confunde
entrega um número quando não mediu nada.

## Duas classes de número, e elas não se substituem

| | `resultado` | `medicoes` |
|---|---|---|
| o que é | métrica **de protocolo** (Recall@K, κ) | fato observável sobre o material recuperado |
| exige | **todas** as pré-condições | apenas ranking com procedência provada |
| existe sob `BLOCKED`? | **não** | **sim** |
| autoriza afirmar qualidade de resposta? | sim, no escopo do protocolo | **não** |

Uma auditoria `BLOCKED` ainda entrega medições. É essa a oferta atual do
serviço, e é por isso que ela não depende de Recall@K.

## PRÉ-CONDIÇÕES e CHECKS

Todo check declara **qual defeito seu número moveria** (`NORTE §4.15`) — campo
obrigatório; a construção falha sem ele.

| check | detecta | barra |
|---|---|---|
| `ranking.veio_do_retriever` | ranking fabricado | sim |
| `ranking.cardinalidade` | duplicação consumindo a janela top-k | sim |
| `ranking.duplicacao_medida` | duplicação por id e por texto | não |
| `estratos.sem_sobreposicao` | mesmo documento julgado duas vezes | sim |
| `estratos.controle_fora_do_ranking` | controle negativo contaminado | sim |
| `estratos.tamanhos` | pool incompleto alterando prevalência | sim |
| `procedencia.artefato_e_auditavel` | artefato invalidado reaproveitado | sim |
| `procedencia.snapshot_tem_hash` | corpus trocado sob o mesmo caminho | sim |
| `estatistica.unidades_suficientes` | IC estreito por contar itens como independentes | sim |
| `estatistica.prevalencia_permite_acordo` | acordo produzido pelo desbalanceamento | sim |

## Telemetria de ranking — contrato, não convenção

Registrado por consulta, no manifesto:

```
origem_do_ranking · top_k_solicitado · n_slots_recebidos
n_ids_distintos   · n_textos_distintos · formato_valido
```

O serviço precisa **provar** que não recebeu uma lista arbitrária de ids.

## PROVENIÊNCIA

Todo artefato carrega: caminho do store, `sha256` de cada arquivo do corpus,
origem declarada do ranking, `top_k`, versão do Python e da plataforma, e um
`sha256` do manifesto inteiro.

O hash do manifesto permite ao cliente contestar cada número.

## POLÍTICA DE ERRO — exit codes

```
0  COMPLETE           executou; há resultado
2  BLOCKED            pré-condição quebrada; há diagnóstico
3  INVALID            entrada não auditável
4  erro operacional   falha do próprio serviço
```

`BLOCKED` **não** é erro do serviço, por isso não é `1`. Um erro operacional
(código 4) não é veredito sobre o sistema auditado: nenhuma conclusão pode ser
tirada dessa execução.

## PRIVACIDADE

- query e documento **nunca** entram em artefato em claro por caminho automático;
- o que entra é hash (`<query:b8e56193c10f>`);
- texto em claro exige `--exemplos-em-claro`, decisão explícita do operador;
- **segredo é removido nos dois modos** — chave de API, token, JWT, chave
  privada, e-mail, CPF. O operador pode autorizar mostrar texto do cliente;
  não pode autorizar vazar credencial;
- a varredura roda sobre a estrutura inteira antes de gravar, inclusive em
  campos que ninguém previu.

## Auditar não altera o auditado

O adaptador **copia** o snapshot antes de consultar. No EDP isso é obrigatório:
`retrieve` incrementa `acessos`/`ultimo_acesso` e salva em disco. Há teste
garantindo que o arquivo de origem não muda.

## O que o serviço NÃO afirma

- não afirma qualidade de resposta sem métrica de protocolo validada;
- não afirma Recall@K — **nenhum experimento deste projeto autorizou isso ainda**;
- não certifica, não aprova, não emite selo;
- não corrige o sistema do cliente durante a auditoria.

### Redação comercial admissível

> Auditoria técnica reproduzível para encontrar problemas de retrieval,
> duplicação, ranking e condições que impedem uma avaliação válida.

### Inadmissível hoje

> ~~Auditoria de RAG validada por Recall@K~~
> ~~Certificamos a qualidade do seu retrieval~~

A oferta diz explicitamente quando o sistema é `BLOCKED`, e que `BLOCKED` é
entrega, não falha.
