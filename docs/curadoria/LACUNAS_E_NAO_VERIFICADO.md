# Lacunas e `NAO_VERIFICADO`

**01/09/2026, Fase 3.** Os 7 itens da Fase 2 foram todos medidos. Nenhum ficou
`NAO_VERIFICADO` por falta de tentativa — dois (volume de `events.jsonl` e
suíte do exportador) tinham resposta mensurável, e a resposta era "menos do
que parecia"; nenhum se revelou impossível de medir no ambiente disponível.

## Os 7 itens, fechados

### 1.1 Uso de `sha256` no kernel — FECHADO

3 usos reais (não 10 "arquivos" — a contagem original misturava menções à
palavra "snapshot" em scripts de experimento). Nenhum é hash de corpus:
`store.py:1586,1764` é seed de RNG reprodutível; `pareto_store.py:186` é
identidade do regime de formato; `cache.py:46` é chave de cache de embedding.
**A linha "hash do corpus" da matriz de proveniência não tem equivalente no
kernel** — fechado em `MAPA_PROVENIENCIA.md`.

### 1.2 `LineageTracker` ativo? — FECHADO

Sim. `EDP_LINEAGE` default `"true"`, fora da lista de 19 flags de
`config.py` (padrão de leitura diferente — achado de escopo, ver abaixo).
Chamador único por AST: `edp/api/routes/websocket.py:1326`, no caminho real
de resposta, para todo turno com LLM. Vivo em produção. Fechado em
`MAPA_CAPACIDADES.md` e `MAPA_PROVENIENCIA.md`.

### 1.3 Cobertura de `write_provenance.stamp_and_classify` — FECHADO

Denominador enumerado antes de medir: 3 caminhos de escrita
(`WorkingMemory.add`, `EpisodicMemory.add`, `MemoryStore.add`). Numerador: 1
chamador (`websocket.py:1256`). **O próprio kernel já documenta a lacuna** —
comentário no chamador diz que é o único, e que 0 de 10 entradas da câmara de
eco têm carimbo. Cobertura: 1/3, achado pré-existente que a Fase 2 não tinha
citado.

### 1.4 Volume real de `events.jsonl` — FECHADO

O arquivo existe e tem dado real: store vivo do kernel (`edp_data/pareto/`),
**395 eventos**, mais recente em 18/08/2026. Mas a distribuição por tipo é o
achado que importa: **268 `memory_accessed`, 110 `memory_added`, 8
`camara_outcome`, 7 `mode_switched`, 1+1 `task_*` — zero dos 5 tipos atrás de
flag de telemetria** (`ranking_decision`, `reflection`, `contradiction_scan`,
`token_usage`, `summary_write`). O formato está exercitado; os dados de maior
interesse para diagnóstico, não. Rebaixou o candidato de acoplamento nº 2 de
"pronto" para "depende do nº 1 gerar dado primeiro" — ver
`CANDIDATOS_ACOPLAMENTO_MVP.md`.

### 1.5 `observability/{logger,tracing}.py` — FECHADO

Infraestrutura real: logging estruturado com `correlation_id`
(context manager) + tracing leve (`Span`, `register_exporter`). **4
importadores por AST no repo inteiro**, não 2 — inclui `edp/llm_adapter.py`,
módulo vivo. Sem teste próprio. Fechado em `MAPA_CAPACIDADES.md`.

### 1.6 Suíte de testes do `sf_exportador` — FECHADO

**Não existe.** Busca por `package.json`, `jest`/`vitest`/`mocha`,
`__tests__/`, `*.test.js`, `*.spec.js` em todo o repositório: zero
ocorrências. 6.255 linhas de JavaScript sem nenhuma infraestrutura de teste
automatizado. O `SERVIÇO C` (`CANDIDATOS_NOVOS_SERVICOS.md`) tinha essa
lacuna como suposição; agora é medição.

### 1.7 Por que cada flag está desligada — FECHADO, parcialmente

`git log -S` para as 11 flags sem motivo já conhecido (`EDP_WIKI_CONVERSAS`
já tinha motivo registrado — correção de contagem: 11, não 12): **8 sem
qualquer registro de decisão** — só commits de introdução/correção de bug,
nada dizendo "manter OFF porque X". **3 (o trio `exp017`) têm decisão
registrada, mas pendente**: o commit `28e21da` fecha os critérios estatísticos
e diz explicitamente que a promoção a produção é "etapa separada", aguardando
"assinatura" do pesquisador — a mesma pergunta que `docs/auditor/DECISAO_RANKING.md`
já faz do lado do lab. Detalhe completo em `MAPA_FLAGS.md`.

---

## Três defeitos da própria curadoria, corrigidos nesta fase

### 0.1 `Synapse-Forge` "vazio" — era afirmação sem medida

Corrigido: não está vazio, tem `.vscode/extensions.json`, 512 bytes. O comando
original que tocaria esse caminho estourou timeout antes de chegar lá, e a
frase ficou na Fase 1 sem verificação por trás.

### 0.2 "As 12 flags têm teste" — verificado arquivo por arquivo

Confirmado: os 12 arquivos citados existem e citam a flag correspondente. A
frase da Fase 2 estava certa neste nível — mas faltava o nível seguinte (0.3).

### 0.3 `TESTADO` era existência de arquivo, não execução — agora é execução

`pytest tests/ -q` rodado nos dois repositórios: `edp_v5` **448 passed, 1
deselected, 0 failed**; `lab_edp_novo` **408 passed, 0 failed**. Nenhuma das
12 flags cai para `EXISTE`. Todos os `TESTADO` da curadoria agora carregam
essa confirmação.

**Um quarto defeito, achado ao tentar fechar os 7 itens**, maior que os três
originais: a contagem de "módulos de topo sem importador" (6) estava errada.
O número certo, medido com a metodologia do próprio `edp_v5`
(`tests/test_catalogo_de_modulos_mortos.py`, `os.walk` do repositório
inteiro): **2** — `analytics` e `reranker`, os mesmos que o gate do README já
aponta. `api` e `profiles` são subpacotes com importador real, não módulos
mortos; `types` e `failsafe` tinham importador que a varredura original (só
`edp/`+`tests/`) não alcançava. Corrigido em `INVENTARIO_ECOSSISTEMA.md`, com
o texto original preservado como errata.

---

## `ACHADOS_FORA_DE_ESCOPO`

Sem ficha, sem classificação, sem candidatura — só registro de que existem,
para não desaparecer silenciosamente.

**Flags de comportamento fora de `config.py`.** `MAPA_FLAGS.md` cobre só o
padrão `X = os.environ.get("EDP_X", "0") == "1"` centralizado em
`edp/config.py`. Existem pelo menos mais 6 variáveis de ambiente lidas direto
dentro de módulos individuais, fora dessa convenção:

```
EDP_LAB_ARMED                   default "0"     trava de segurança do
                                                laboratório, 6 pontos de
                                                leitura em edp/lab/
EDP_AUTO_CONSOLIDATE            default "true"
EDP_COGNITIVE_DECISIONS_ENABLED default "true"
EDP_HEALTH_INDEX                default "true"
EDP_LINEAGE                     default "true"   (fechado acima, 1.2)
EDP_QUALITY_SCORE               default "true"
```

Não foram investigadas individualmente — abrir ficha para cada uma seria a
mesma expansão de escopo que esta fase existe para fechar, não para repetir.

**Duas populações confundidas em "hash do corpus".** A linha original da
matriz de proveniência tratava "hash do corpus" e "hash de snapshot" como o
mesmo conceito. São perguntas diferentes — a segunda (o kernel hasheia o
snapshot que consulta, por algum outro mecanismo?) segue **não verificada**:
o item 1.1 pedia especificamente sobre `sha256`, e a resposta que saiu
(nenhum dos 3 usos é hash de corpus) não descarta hash por outro algoritmo.

---

## Lacunas de método que continuam, herdadas da Fase 2

**Não medi qualidade de código.** Só existência, importador, execução,
cobertura de chamada e distribuição de dado real. Um módulo "vivo" pode estar
mal escrito; um "sem teste" pode estar correto.

**Não executei os módulos sem teste** para saber se funcionam. "Sem teste" é
ausência de verificação, não presença de defeito.

**Não medi custo de acoplamento.** As classificações "acoplar agora / depois /
precisa de teste" continuam sendo **julgamento a partir de tamanho, cobertura
e risco de alterar a régua** — não medição.

**Não testei nenhum candidato de acoplamento nesta fase.** A autorização desta
fase foi rodar teste *existente*; nenhuma flag foi ligada, nenhum código foi
alterado, nenhum evento novo foi emitido.

**Não abri as 8 flags "sem registro de decisão"** para tentar deduzir a
intenção por leitura de código adicional — a Fase 3 pediu arqueologia de git
especificamente porque leitura de código já tinha sido tentada na Fase 2 e não
achou nada.

---

## O descompasso, recontado com os números certos

| | Fase 2 (errado) | Fase 3 (medido) |
|---|---|---|
| módulos/unidades de topo | 49 | 49 (40 arquivos + 9 subpacotes) |
| sem importador em todo o repo | 6 | **2** (`analytics`, `reranker`) |
| com importador, sem teste | 27 (55%) | **28 (57%)** |
| vivos (importador + teste) | 16 (33%) | **19 (39%)** |
| flags de engenharia testada, desligadas | 12 | 12 (confirmado por execução) |

A correção **piora**, não melhora, a leitura de cobertura de teste — 57% sem
teste, não 55%. E **melhora** a leitura de código morto — 2 módulos mortos,
não 6. Os dois eixos se moveram em direções opostas porque eram dois erros de
método independentes, não um viés sistemático numa direção só.

`~3.000 linhas de Bancada / 2 arquivos de teste` e `metrics.py: 22
importadores / 0 testes` não foram remedidos nesta fase — continuam como a
Fase 2 registrou.

**Ainda nenhuma capacidade do kernel está em `VALIDADA`.** O teto medido
continua `TESTADO` — agora confirmado por execução, o que é uma barra mais
alta que "arquivo existe", mas ainda não é "medida contra critério congelado
antes do dado", que é o que este projeto chama de validado.
