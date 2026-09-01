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


---

# MVP-1B — productização

**31/08/2026.** O núcleo validado foi preservado; nenhum experimento científico
novo foi aberto. `REL-001` segue bloqueado, Recall@K segue fora da oferta.

## A mudança imediata: identidade completa na abertura

A regra que valia só para o `sha256_queries` virou geral. Antes da primeira
etapa, o manifesto já carrega:

```
snapshot (hash) · dataset (hash, origem) · protocolo + versão
adaptador + versão · configuração · política de privacidade
```

Há verificação que **levanta** se algum faltar. Qualquer `BLOCKED` nasce
contestável: o cliente sabe sobre qual corpus, quais queries e qual régua.

## Uma implementação, duas portas

```
AuditInput v1 → valida → workspace isolado → engine → redação
              → manifesto + relatórios → AuditResult v1
```

CLI e HTTP entram por `servico.executa`. Há teste que **falha** se `api.py`
mencionar qualquer regra de auditoria — duas implementações da mesma regra
divergem, e a divergência apareceria quando o cliente comparasse o CLI com a API.

## Formatos versionados

`AuditInput v1` recusa **antes** de qualquer trabalho: campo faltando, campo
desconhecido, schema de outra versão, protocolo ou adaptador inexistente. Um
`protocolo` escrito no lugar de `protocol` rodaria com a régua errada em
silêncio.

`AuditResult v1` tem 17 campos obrigatórios, verificados por teste.

## Isolamento por auditoria

```
<raiz>/<audit_id>/
    input/  artifacts/  reports/  manifest.json
```

Reaproveitar diretório é recusado. Escrever fora da raiz é recusado. A fronteira
é a **raiz da auditoria**, não o subdiretório — `reports/../input/x` continua
dentro do mesmo cliente e é legítimo.

## Retenção por classe

```
input 7d · artifacts 30d · reports 90d · manifest 365d
```

O material bruto do cliente é o mais sensível e expira primeiro. A expiração
**lista por padrão e só apaga quando mandado** — apagar dado de cliente é
irreversível.

## Redação como última barreira

A sanitização roda dentro de `Manifesto.salva`, o único ponto por onde o
manifesto vira arquivo. Se um segredo sobreviver, a gravação **falha** em vez
de escrever: vazamento é irreversível, e não gravar é melhor que corrigir
depois. O hash cobre o que foi realmente gravado.

## API HTTP

```
POST /v1/audits            202, assíncrona
GET  /v1/audits/{id}       AuditResult v1
GET  /v1/audits/{id}/status
GET  /v1/audits/{id}/report?tipo=executive|technical
GET  /v1/audits/{id}/manifest
```

Job não depende da conexão ficar aberta. `request_id` garante idempotência —
um retry de rede não vira duas auditorias cobradas. O estado do job **deriva**
do estado da auditoria: um job não pode dizer `COMPLETE` sobre auditoria
`BLOCKED`.

`fastapi` é importado só em `api.py`; o núcleo roda sem ele, verificado em
subprocesso.

## Pacote

`pyproject.toml` com **`dependencies = []`** — engine, checks, medições e CLI
rodam com a biblioteca padrão. HTTP é extra opcional. Entry point `auditor`.

## Observabilidade separada do resultado

`observabilidade` carrega tempo de serviço e por etapa, com nota explícita de
que **não é resultado da auditoria** e não deve ser lido como medição do
sistema do cliente.

## Critério de saída (item 20) — conferido

Um terceiro instala, fornece inputs, roda `check` (que **não grava relatório**),
recebe `BLOCKED`, roda `run`, obtém manifesto e os dois relatórios, verifica o
`sha256`, e roda de novo **sem alterar o snapshot** — tudo com teste nomeado.

Impedidos automaticamente: ranking fabricado · snapshot trocado · artefato
inválido · dado vazando · métrica sob `BLOCKED` · contaminação entre clientes.

**276 testes.**

## Dois defeitos meus, achados pelos próprios testes

**O teste de fronteira do workspace assertava demais**: reprovava
`reports/../input/x`, que fica dentro do mesmo cliente. A fronteira é a raiz,
não o subdiretório.

**`configuracao` duplicava o `audit_id`**, que já é campo de topo. O teste de
reprodutibilidade pegou como fonte de variação não declarada. Removi a
duplicata — identificador em dois lugares convida a divergir.

## Pendente, e não é do agente

`DECISAO_RANKING.md` em branco · piloto externo (`PILOTO_EXTERNO.md` tem o
protocolo pronto, **não executado**) · preço (`UNIDADE_ECONOMICA.md`:
`PRECO_POR_MTOK` vazio de propósito).

**Continua fora:** dashboard, Reddit, juiz no pipeline, correção do
`_hybrid_index`. E o MVP-1B **não** é argumento de que Recall@K está validado.

---

# DIAGNOSTICO v1 — a régua com escopo comercial

**31/08/2026.** O entregável comercial estava chegando rotulado como fracasso.

O cliente que quer saber quanto da janela de contexto o retriever desperdiça
não precisa de estrato, de cauda 20–50 nem de controle negativo — isso é
aparato do REL-001. Mas o pipeline rodava essas verificações, bloqueava nelas, e
entregava as cinco medições **debaixo de um `BLOCKED`**. Foi o que aconteceu com
os três adaptadores do piloto.

## O que mudou

`Protocolo` ganhou `escopo`:

```
protocolo     mede métrica de protocolo (Recall@K, κ) — precisa do aparato
diagnostico   mede o MATERIAL RECUPERADO — não usa estrato nem controle
```

**Não é afrouxamento.** É uma régua diferente, com escopo declarado. A etapa de
estratos fica `PENDING` com motivo — **nunca `PASS`**: dizer que passou uma
verificação que não rodou seria a mentira que o serviço existe para evitar.

E o que ela exige continua de pé: **ranking com procedência provada**. Um
adaptador que devolve ordem de arquivo bloqueia igual, e entrega zero medições.

## Resultado no EDP real

```
DIAGNOSTICO v1 · 50 queries · COMPLETE
```

| medição | valor | IC 95% |
|---|---|---|
| cardinalidade | 37 documentos por query | [37; 38] |
| duplicação por id | 0,26 dos slots | [0,24; 0,26] |
| duplicação por texto | 0 (5 queries afetadas, máx 0,37) | [0; 0] |
| jaccard cross-query | 0,283 | [0,276; 0,290] |
| razão topo/cauda | 1,81 | [1,75; 1,86] |

Lido em português: **de 50 slots recuperados, chegam 37 documentos distintos;
26% dos slots foram ocupados por um id que já havia aparecido na mesma query.**

> **Errata 01/09.** A primeira versão desta linha dizia *"um quarto da janela
> **vai em** documento repetido"*. Isso afirma consequência — que a repetição
> **consome** a janela útil — e consequência não foi medida. O
> `NUMEROS_DE_DUPLICACAO.md` já registrava a regra quando escrevi a frase:
> *"nenhum é 'X% do contexto do RAG é inútil'; todos medem repetição de slot"*.
> Saber a regra não impediu de violá-la, e é por isso que ela virou teste.

## Um defeito corrigido no relatório

Sob `COMPLETE`, a seção *"O que NÃO foi medido"* imprimia **"(nada — a auditoria
completou)"**. Para um diagnóstico isso é **falso** e perigoso: convida a ler
escopo estreito como auditoria plena.

Agora essa seção é obrigatória e explícita — não foi medida qualidade de
resposta, nem Recall@K, nem relevância (nenhum julgamento foi feito), nem
conformidade. Com a frase que separa as duas coisas:

> Os números descrevem **o que foi recuperado**, não **se o que foi recuperado
> era o certo**.

Há teste que reprova o relatório se qualquer uma dessas ressalvas sumir.

**283 testes.** `REL-001` segue bloqueado; `DECISAO_RANKING.md` segue em branco.

---

# MVP-1D — integração e primeiro fluxo de cliente

**01/09/2026.** Escopo científico do `DIAGNOSTICO v1` intacto. `REL-001`
bloqueado. Nenhum dashboard, nenhum Question Mining.

## O job passou a existir de verdade

Antes, o job vivia num dicionário em memória dentro do `api.py`. Duas
consequências: o CLI não conseguia responder `status` nem `report` — o processo
já tinha morrido — e o HTTP perdia tudo ao reiniciar. **Um serviço que esquece o
que executou não é auditável.**

Agora o registro fica em `<raiz>/<audit_id>/job.json`, e CLI e HTTP leem o
mesmo. A idempotência por `request_id` passou a sobreviver a reinício: em
memória, um retry depois de restart criaria uma segunda auditoria, e o cliente
pagaria duas vezes por dois manifestos do mesmo sistema.

`auditor status` e `auditor report` existem, e `report` **não recalcula nada** —
lê o que foi gerado.

## Clientes externos simulados, como dados

`fixtures/customer_{a,b,c}/` são `corpus.json`, `queries.json` e `config.json`
em disco — não classes do próprio pacote. Uma fixture que é código interno
testa o serviço contra si mesmo.

**O EDP não foi usado**: ele é o nosso sistema, e usá-lo como cliente externo
seria medir a integração contra a única integração que já existia.

## O instrumento recupera o defeito injetado

| | `customer_a` | `customer_b` | injetado em B |
|---|---|---|---|
| documentos distintos por query | 50 | **22** | — |
| duplicação intra-query por id | 0,00 | **0,56** | **0,55** |

O gerador do `customer_b` não conhece o código de medição, e a medição devolveu
0,56 para 0,55 injetado. **O instrumento detecta o defeito que afirma
detectar** — o mais perto de validação que dá para chegar sem dado externo.

Não substitui dado externo: escrevi o gerador e o medidor, e é exatamente esse
viés que um piloto real elimina.

## A incompatibilidade C1, ponta a ponta

| `customer_c` | `check` | `run` | status | medições |
|---|---|---|---|---|
| distância crua | 0,17 s | 0,19 s | **`BLOCKED`** | **0** |
| com conversão declarada | 1,74 s | 1,80 s | `COMPLETE` | 5 |

O caso bloqueado é **10× mais rápido** — a propriedade funcionando: ele para na
primeira etapa, antes de qualquer trabalho.

O serviço **nunca** aplica a conversão sozinho. Fazer isso seria adivinhar a
semântica do score do cliente.

## Terceiro falso positivo da trava de claims, e a regra que faltava

A trava reprovou a página `O_QUE_NAO_FAZEMOS.md` — na frase que existe **para
proibir** a frase: *"dizemos … e nunca "26% do seu contexto é desperdiçado""*.
O guard de negação olha 40 caracteres atrás; o `nunca` estava a 50, do outro
lado da citação. (E a citação ainda atravessava quebra de linha.)

Alargar a janela seria remendo. A regra que cobre os três casos é mais simples:
**o documento afirma com as próprias palavras e cita com aspas.**

Limite aceito conscientemente: isso abre um falso negativo — um claim entre
aspas passa. É aceitável porque os relatórios são gerados por código e nunca
põem afirmação entre aspas, e porque o erro oposto já se mostrou pior: um
linter que reprova a ressalva força a apagá-la.

## Produto: *diagnóstico*, não *auditoria*

`docs/auditor/produto/` traz **Como funciona**, **O que você recebe** e **O que
não fazemos** — a última coerente com `CLAIMS.md`, com teste que roda a trava
sobre as três páginas.

O título é **Diagnóstico de Retrieval**, e há teste que reprova se virar
"auditoria": a palavra promete qualidade, conformidade e certificação, e tem
que caber no que a medição sustenta.

## O que continua `NAO_MEDIDO`

```
satisfação · utilidade percebida · disposição de pagar
intenção de renovação · tempo humano de integração · dificuldade percebida
```

Todos exigem usuário real. **318 testes.**
