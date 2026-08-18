# Pré-registro — Experimento E10
## Um verificador léxico separa "a afirmação está na memória citada" de "não está"?

**Bancada de Contexto — EDP.** Categoria **VALIDAÇÃO DE INSTRUMENTO**, eixo
**confiabilidade**. O arco E9/E9b/E9c produziu régua para o eixo de **custo**.
Não existe régua equivalente para "a resposta é sustentada pelo que foi
recuperado" — e é essa que trava tudo que for autônomo.

> **Régua da Bancada:** hipóteses, condições, dataset, métricas e critério
> congelados ANTES de qualquer medição. A encarnação (`exp_e10.py`) espelha
> este `.md` e congela ao 1º disparo real. Mudou a régua → é o E10b.

**Data de pré-registro: 2026-08-18**, antes da primeira medição.

---

## §1. Por que este experimento, e por que agora

Num laço autônomo **não há usuário para corrigir**. O único crítico existente
no EDP é a Câmara de Eco, e ela dispara por `AUTO_SINAL_LIMITE_REGEX` —
detecta que o modelo **disse** "não consigo". Consequência já estabelecida: o
operador zera o próprio sinal de treino não emitindo a frase. A recompensa tem
conjunto vazio alcançável em uma jogada.

A alternativa é ancorar em algo que o operador **não consegue emitir**:
a afirmação cita `entry_id`, e o verificador **abre a entrada e confere**.

O E10 pergunta a versão mais barata e mais falsificável disso: **um
verificador puramente léxico dá conta?** Se der, o laço autônomo ganha crítico
sem custo de inferência. Se não der, fica estabelecido o piso que qualquer
crítico terá de superar — e isso vale igualmente.

---

## §2. Contexto provado — Passo 0 de 2026-08-18

Verificado por leitura direta hoje, **não herdado de docstring**. Duas destas
linhas corrigem afirmação minha anterior.

### 2.1 O lineage grava metade do par

`edp/runtime/lineage.py` é escrito no caminho vivo
(`api/routes/websocket.py:1318,1326`). Sobre os 18 registros de
`data/sessions/default_cognitive/lineage.jsonl`:

| | |
|---|---|
| `entry_id` citados que resolvem no episódico | **75/75** ✓ |
| `response_id` que resolvem no episódico | **0/18** ✗ |
| `correlation_id` preenchido | **0/18** ✗ |
| `quality_score` preenchido | 4/18 |

> **ERRATA de afirmação minha.** Eu disse, duas vezes, que *"o substrato
> existe — o lineage já grava `entry_ids · scores · source_type`; falta o
> passo de verificação"*. **O lado citado existe; o lado da afirmação não.**
> O lineage registra *quais memórias informaram uma resposta* e **não permite
> recuperar a resposta**. `response_id` não é o `id` da entrada.

As 18 entradas do episódico **são** respostas (`llm_response` ×16,
`camara_response` ×2), e 18/18 registros de lineage juntam a uma entrada por
**proximidade de timestamp (±5 s)**. Ou seja: o par é recuperável por
heurística temporal, não por chave. Isso é dívida do kernel, registrada aqui
para não sumir — **e não é usada por este experimento** (§4).

### 2.2 O corpus já mediu o que decide a predição

Da telemetria de contradição (13/08): **16 dos 18 textos do store contêm
marcador de negação**. Este número não é decorativo — ele prevê o
comportamento da condição `lexico_negacao` (§7).

### 2.3 As peças reutilizadas existem e são reais

- `edp.runtime.contradiction_flagger.negation_asymmetry(a, b)` — `True` se
  **um** dos textos tem negação e o outro não. Componente de produção,
  usado como é.
- `bancada.scorer.wilson(k, n, z)` — IC de proporção, agnóstico de sujeito,
  já usado pelos exp001/003/004/006/007.

---

## §3. Hipóteses

- **H1 — separação básica.** O verificador `lexico` separa `suportada` de
  `trocada` **sem limiar**: o menor escore entre as suportadas é maior que o
  maior escore entre as trocadas.
- **H2 — colapso na contradição.** A mesma separação **NÃO** vale entre
  `suportada` e `negada`. Afirmação negada tem quase o mesmo léxico da
  original.
- **H3 — a negação não resgata.** `lexico_negacao` **também** falha em
  `negada`, porque `negation_asymmetry` exige que **um só** lado tenha
  negação, e 16/18 dos textos já têm (§2.2).

**H0 de cada uma é achado.** Se H2 for refutada — se o léxico separar
contradição — isso é o resultado mais valioso possível aqui, e mudaria o
desenho do crítico do laço autônomo.

---

## §4. Dataset CONGELADO — e por que não vem da produção

**Descartado: pares de produção.** O §2.1 mostra que o par é recuperável por
timestamp. Mas para validar um verificador é preciso **gabarito**, e não se
sabe se uma resposta real era de fato sustentada pelas entradas citadas.
Par sem gabarito não testa verificador nenhum.

**Adotado: gabarito por construção.** A afirmação é o `key_assertion` que o
extrator `cognitive_decisions` produziu **a partir daquela entrada** — outro
componente, não eu. O texto é o `text` da mesma entrada.

Universo: entradas de `default_cognitive` com `key_assertion` não-vazio.
Medido hoje: **16 de 18**. `N_PARES` é o tamanho do universo, não uma escolha.

| estrato | par | gabarito |
|---|---|---|
| `suportada` | `key_assertion(i)` × `text(i)` | **SUSTENTA** |
| `trocada` | `key_assertion(i)` × `text((i+1) mod N)` | não sustenta |
| `negada` | negação de `key_assertion(i)` × `text(i)` | não sustenta |

`trocada` usa `(i+1) mod N` — regra determinística, a mesma do controle
shuffle do exp008.

**Negação mecânica, congelada:** insere `" não "` após o primeiro verbo
reconhecido por lista fixa; se nenhum casar, prefixa `"Não é verdade que "`.
A regra é impressa na prova-no-espelho para revisão humana antes de armar.

---

## §5. Condições (variantes de verificador)

| rótulo | escore | papel |
|---|---|---|
| `cego` | **ignora o texto**; escore = função monotônica só do tamanho da afirmação | **CONTROLE NEGATIVO** |
| `lexico` | `\|tok(afirm) ∩ tok(texto)\| / \|tok(afirm)\|` | tratamento |
| `lexico_negacao` | `lexico`, zerado se `negation_asymmetry(afirm, texto)` | tratamento |

`cego` existe pelo mesmo motivo do `base_B` no E9c: se um verificador real não
superar um que **não lê a entrada**, nada foi aprendido.

> **Emenda E10-1 (pré-dado, 2026-08-18).** A primeira redação dizia "devolve
> escore **constante**". Escore constante torna `min(A) > max(B)` **falso por
> construção** — o controle passaria sempre, sem poder falhar. É o mesmo teatro
> que a regra de sobreposição de IC produzia no E9b, e eu o reintroduzi.
>
> Corrigido: `cego` pontua **só pela afirmação**, ignorando o texto
> (`len(tok(afirm)) / 100`). Agora ele tem dois comportamentos, e ambos
> informam:
> - contra `suportada` × `trocada` — **não pode separar**, porque os dois
>   estratos usam as MESMAS 16 afirmações. Se separar, o vazamento está no
>   encanamento.
> - contra `suportada` × `negada` — **PODE separar**, e se separar revela um
>   confundidor real: a negação mecânica altera o tamanho da afirmação, e um
>   verificador poderia "detectar contradição" só notando que ela ficou maior,
>   sem ler o texto.
>
> O segundo caso é o que a versão constante não conseguia nem enxergar.

`tok(s)`: minúsculas, corte em não-alfanumérico, descarta com menos de
`MIN_TOKEN_LEN` caracteres, remove `STOPWORDS` (§11).

---

## §6. Critério — livre de limiar, e por quê

Com 16 pares por estrato, escolher um limiar de corte é convite a
sobreajuste — e seria a **quarta constante Tier A** deste arco depois de
`LOAD_DURATION_MAX_FRAC` e dos dois `DELTA_EQUIV`. Não repito.

A hipótese é de **separação completa**, no molde do
`preregistro_gate_especificidade.md`:

```
SEPARA(A, B)  ⟺  min{ escore(x) : x ∈ A }  >  max{ escore(y) : y ∈ B }
```

Cascata, **para no primeiro que falhar**:

1. **VALIDADE-a.** `cego` **não** pode separar `suportada` de `trocada`
   (mesmas afirmações nos dois). Se separar → **INSTRUMENTO INVÁLIDO**,
   vazamento no encanamento, nada é afirmado.
2. **VALIDADE-b.** `cego` **não** pode separar `suportada` de `negada`. Se
   separar → **ESTRATO `negada` CONFUNDIDO**: a negação mecânica é detectável
   pelo tamanho da afirmação, sem ler o texto, e H2/H3 deixam de ser sobre
   contradição. Nada é afirmado sobre `negada`.
3. **SANIDADE.** Os três estratos têm `N_PARES` pares cada, e nenhuma
   afirmação vazia ou texto vazio.
4. **H1.** `SEPARA(suportada, trocada)` para `lexico`.
5. **H2.** `SEPARA(suportada, negada)` para `lexico` é **FALSO**.
6. **H3.** `SEPARA(suportada, negada)` para `lexico_negacao` é **FALSO**.

Reportado junto, **descritivo e NÃO critério**: acurácia por estrato com IC de
Wilson 95% ao melhor limiar observado, e a margem de separação
`min(A) − max(B)`. Servem para dimensionar o E10b; não decidem nada aqui.

---

## §7. Predição pré-dado do arquiteto

Registradas antes de qualquer medição, para poderem ser refutadas.

- **H1 confirmada** — confiança alta. `key_assertion` é derivado do texto;
  o overlap deve ser alto contra o próprio e baixo contra o vizinho.
- **H2 confirmada** (o léxico falha em contradição) — **confiança alta**.
  Inserir `"não"` muda ~1 token de dezenas.
- **H3 confirmada** (a negação não resgata) — **confiança média-alta**, e é a
  predição que vale mais, porque é a única derivada de medição anterior:
  16/18 textos já contêm negação, então `negation_asymmetry` devolve `False`
  na maioria dos pares `negada` e o veto não dispara.

**Se H3 for refutada**, minha leitura de que `negation_asymmetry` é inútil
como veto neste corpus está errada, e o crítico léxico volta à mesa.

---

## §8–§10. Métricas, anti-mock, isolamento

**Métrica primária:** separação completa (§6), binária por par de estratos.
**Secundárias:** Wilson 95% da acurácia por estrato; margem de separação.

**Anti-mock:** `negation_asymmetry` é a função **de produção**, importada de
`edp.runtime.contradiction_flagger` — não reimplementada. Exige
`PYTHONPATH` apontando para o `edp_v5`, como `monitora_coleta.py` já faz.

**Isolamento:** leitura pura de `episodic.json`. **Não** chama `retrieve()`
(que muta `acessos`/`ultimo_acesso` e persiste), **não** escreve em
`data/sessions/`, **não** chama modelo nenhum — o E10 não faz inferência.

**Registro bruto:** todo par com afirmação, id da entrada, escore por
variante e gabarito vai para JSONL. O agregado não é o achado.

---

## §11. Constantes congeladas (espelhadas em `exp_e10.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"E10"` |
| `N_PARES` | `16` |
| `MIN_TOKEN_LEN` | `3` |
| `STOPWORDS` | `frozenset({'para', 'com', 'que', 'uma', 'dos', 'das', 'nao', 'por', 'como', 'mas', 'seu', 'sua', 'aos', 'nas', 'nos', 'ele', 'ela', 'isso', 'esta', 'este'})` |
| `TROCA_OFFSET` | `1` |
| `Z_WILSON` | `1.96` |
| `SEED` | `20260818` |
| `DIVISOR_CEGO` | `100.0` *(E10-1)* |
| condições | `cego`, `lexico`, `lexico_negacao` |
| estratos | `suportada`, `trocada`, `negada` |

`N_PARES = 16` é o tamanho do universo medido hoje, não uma escolha de
potência. **Se o extrator rodar mais e o universo crescer, isso é o E10b** —
mudar `N_PARES` depois de ver o resultado seria escolher a régua com o dado na
mão.

**CONGELADO ao primeiro disparo real. Mudou a régua → é o E10b.**

---

## §12. Honestidade de escopo

- **n = 16 por estrato é grosseiro.** Sustenta um sim/não sobre separação
  completa; **não** sustenta calibração de limiar nem comparação fina entre
  variantes. O IC de Wilson em 16 pares tem amplitude ~±0,20.
- **`key_assertion` como afirmação é um caso favorável.** Foi derivado
  daquele texto por um extrator. Uma afirmação composta por um operador
  navegando várias memórias é **mais difícil**, e o E10 não a testa. Um H1
  aqui é piso, não teto.
- **Nada sobre verdade.** O E10 mede se a afirmação está **sustentada pela
  entrada citada** — que é `OBSERVAÇÃO`, não `VERDADE`. A distinção é a mesma
  que o próprio projeto usa, e ela é o ponto: um verificador de proveniência
  não decide se algo é verdade, decide se foi inventado.
- **Nada sobre a Câmara de Eco.** O E10 não a modifica nem a avalia; propõe
  uma âncora alternativa e mede se ela se sustenta sozinha.

---

## §13. Resultado — 2026-08-18

48 pares (16 por estrato), corpus real `default_cognitive`, kernel resolvido em
`/media/sf_edp_v5_main/edp`. Leitura pura, zero inferência, execução em segundos.

### Separações `min(A) > max(B)`

| verificador | `suportada` > `trocada` | `suportada` > `negada` |
|---|---|---|
| `cego` | não (margem −0,080) | não (margem −0,080) |
| `lexico` | **não** (margem −0,333) | não (margem −1,000) |
| `lexico_negacao` | não (margem −0,222) | não (margem −1,000) |

| # | cheque | |
|---|---|---|
| 1 | VALIDADE-a — `cego` não separa `trocada` | **ok** |
| 2 | VALIDADE-b — `cego` não separa `negada` | **ok** |
| 3 | SANIDADE — 16/16/16 | **ok** |
| 4 | **H1** — `lexico` separa `trocada` | **FALHA** |
| 5 | **H2** — `lexico` falha em `negada` | **ok** |
| 6 | **H3** — `lexico_negacao` também falha | **ok** |

> **VEREDITO: PARCIAL — H2 e H3 confirmadas, H1 REFUTADA.**

### H1 refutada — e era a predição de confiança mais alta

O §7 declarou *"H1 confirmada — confiança alta"*. Errado.

Descritivo da distribuição de `escore_lexico`:

```
suportada   min=0,000  p25=0,667  mediana=0,764  max=1,000   zeros 1/16
trocada     min=0,000  p25=0,000  mediana=0,050  max=0,333   zeros 8/16
negada      min=0,000  p25=0,667  mediana=0,725  max=1,000   zeros 1/16
```

A separação falhou por **um único par**: a afirmação *"Oferta de assistência
técnica genérica"* não compartilha **nenhum** token de conteúdo com o próprio
texto de origem.

**Por que eu errei:** supus que `key_assertion` fosse **extrativo** — derivado
do texto, logo lexicalmente ancorado nele. Ele é parcialmente **abstrativo**:
na maioria dos casos compartilha vocabulário (mediana 0,764), mas às vezes
produz um rótulo puro, sem token em comum. Isso é atualização sobre o **EDP**,
não só sobre o experimento.

**O que NÃO faço com isso.** O critério era `min > max`, escolhido de propósito
por ser livre de limiar e implacável. Ele falhou. Observar que "excluindo aquele
par a separação existiria" seria escolher a régua depois de ver o dado — a
mesma tentação do E9, recusada pelo mesmo motivo. **H1 está refutada como
especificada.** A observação sobre o outlier é insumo para o E10b, não resgate
do E10.

### H2 e H3 — o achado que sustenta a conclusão

```
suportada  mediana 0,764
negada     mediana 0,725
```

**Inserir uma negação praticamente não move o escore.** Muda ~1 token entre
dezenas. Um verificador léxico não distingue `X` de `X não`.

E `lexico_negacao` não resgata, exatamente como o §7 previu a partir de
medição anterior deste repo (16/18 textos já contêm marcador de negação, logo
`negation_asymmetry` não dispara). Foi a única predição derivada de medição, e
foi a que se sustentou.

### A conclusão operacional

Acurácia ao melhor limiar observado (**descritivo, não critério**):

| verificador | acurácia | IC 95% |
|---|---|---|
| `cego` (não lê a memória) | 0,646 | [0,504 · 0,766] |
| `lexico` | 0,708 | [0,568 · 0,818] |
| `lexico_negacao` | 0,688 | [0,547 · 0,800] |

> **O verificador léxico não é estatisticamente distinguível de um que nunca
> lê a memória.** ICs largamente sobrepostos, e o veto de negação **piora**.

**Verificação de proveniência por meio léxico não serve como crítico de laço
autônomo.** Isso era o que o §1 se propôs a estabelecer, e está estabelecido —
como piso experimental, não como opinião.

### Predições pontuadas

| | previsto | resultado |
|---|---|---|
| H1 | confirmada, **confiança alta** | **REFUTADA** |
| H2 | confirmada, confiança alta | confirmada |
| H3 | confirmada, confiança média-alta, **derivada de medição** | confirmada |

Duas de três. A que falhou foi a de maior confiança e a única baseada em
suposição minha sobre o comportamento de um componente; a que mais se sustentou
foi a única ancorada num número já medido. O padrão é o mesmo do arco E9.

### Uma fraqueza de desenho, registrada

**Para o E10, prova-no-espelho e disparo real são a mesma computação.** O E10 é
determinístico — sem amostragem, sem tempo, sem aleatoriedade. As duas execuções
diferem apenas em imprimir o dataset e gravar o JSONL. Diferente do E9, onde o
dry-run exercitava o encanamento sem gastar a coleta, aqui **não há nada para
revisar "antes"**: ver a saída do dry-run já é ver o resultado.

Não invalida nada — o critério estava congelado e commitado (`970bcdc`) antes de
qualquer execução, o que é o que importa. Mas a prova-no-espelho não cumpre no
E10 a função que cumpre no E9, e chamá-la assim seria imprecisão.

---

## §11-bis. Emendas

### E10-2 — o harness verifica de ONDE o `edp` foi importado · 2026-08-18

**Achado ao escrever o harness, antes da primeira medição.** Sem `PYTHONPATH`,
`import edp` resolve para `~/.local/lib/python3.11/site-packages/edp/` — cópia
**instalada** de 492 linhas, anterior à telemetria de contradição de 13/08,
contra **527** do kernel vivo.

O E10 importaria `negation_asymmetry` de **outra build**, e nada avisaria. O
§10 exige a função *de produção*; uma cópia instalada não é produção — é um
retrato dela, de data desconhecida.

Congelado: `kernel_resolvido()` **recusa** execução se o `edp` vier de
`site-packages`/`dist-packages`, respeita `EDP_KERNEL` quando definida, e o
caminho resolvido vai para a saída. Um experimento sobre proveniência
registrando a própria proveniência.


---

## §14. ERRATA — o E10 rodou contra o store errado · 2026-08-18

**O §4 e o §11 afirmam que `N_PARES = 16` é "o tamanho do universo medido
hoje, não uma escolha". A afirmação é falsa.**

Os 16 vieram de `<repo>/data`, um store **lateral** de 18 entradas que o EDP
criou entre 12 e 13/08 porque `EDP_BASE_DIR` tem três defaults distintos no
código (`config.py:9`, `pareto_store.py:223`, `lineage.py:315`) e ficou
indefinida. Li `data/` porque havia arquivos ali e **nunca verifiquei que era
produção**.

Medido em 18/08, depois de fundir os dois stores:

| | E10 (13/08) | store real |
|---|---|---|
| entradas episódicas | 18 | **155+** |
| universo com `key_assertion` | 16 | **93** |

### O que isso faz com o resultado do §13

**Não sei, e é essa a resposta honesta.**

O que o §13 afirma — `H1 REFUTADA`, `H2` e `H3` confirmadas — vale para 16
pares de um store lateral. Não vale para o corpus do EDP, e não posso inferir
a direção:

- **H1** falhou por **um único par** de escore zero. Com 93 pares há mais
  chances de outliers como aquele, mas também um `trocada` mais diverso, que
  poderia separar melhor. Os dois efeitos empurram em sentidos opostos.
- **H2/H3** (negação quase não move o escore léxico) são **estruturais** —
  inserir uma palavra entre dezenas muda pouco, e `negation_asymmetry` exige
  exatamente um lado com negação. Sobrevivem *provavelmente*.

**"Provavelmente" não é resultado.** Foi exatamente essa palavra que custou o
defeito da telemetria de ranking no mesmo dia
(`ACHADO_TELEMETRIA_NO_CAMINHO_MORTO.md`).

### O que NÃO faço

Não repontuo o E10 com `N_PARES = 93`. O critério estava congelado e o
experimento rodou como especificado; trocar a constante agora seria mudar a
régua depois do resultado. **O §11 fica em 16** — é o que foi congelado e o
que rodou, e o gate de espelhamento continua exigindo isso.

Refazer contra o corpus certo é o **E10b**, com pré-registro próprio. E ele
herda três coisas desta errata:

1. `N_PARES` volta a ser o tamanho do universo — agora **medido no store
   verificado**, com o caminho impresso na saída, como o `kernel_resolvido()`
   já faz para a proveniência do `edp`.
2. A condição **semântica** (cosseno de embeddings) que ficou de fora por
   economia — com 93 pares e execução em segundos, o custo continua
   desprezível e a informação por experimento dobra.
3. A métrica secundária com cobertura verificada que o §12 pediu, para um
   ponto solitário não determinar o veredito quando o efeito de fundo é
   grande.

### O que sobrevive intacto

A emenda **E10-2** (o harness recusa `edp` vindo de `site-packages`) não
depende de corpus e continua valendo — e é, ironicamente, uma guarda de
proveniência escrita no mesmo dia em que eu falhei em verificar a proveniência
do **dado**. Guardei de onde vinha o código e não de onde vinha o corpus.
