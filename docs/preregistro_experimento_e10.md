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
| `cego` | ignora o texto; devolve escore constante | **CONTROLE NEGATIVO** |
| `lexico` | `\|tok(afirm) ∩ tok(texto)\| / \|tok(afirm)\|` | tratamento |
| `lexico_negacao` | `lexico`, zerado se `negation_asymmetry(afirm, texto)` | tratamento |

`cego` existe pelo mesmo motivo do `base_B` no E9c: se um verificador real não
superar um que **não lê a entrada**, nada foi aprendido. Ele não pode separar
estrato nenhum, por construção.

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

1. **VALIDADE.** `cego` **não** pode separar `suportada` de `trocada`. Se
   separar, o escore está lendo algo que não é a entrada → **INSTRUMENTO
   INVÁLIDO**, nada é afirmado.
2. **SANIDADE.** Os três estratos têm `N_PARES` pares cada, e nenhuma
   afirmação vazia ou texto vazio.
3. **H1.** `SEPARA(suportada, trocada)` para `lexico`.
4. **H2.** `SEPARA(suportada, negada)` para `lexico` é **FALSO**.
5. **H3.** `SEPARA(suportada, negada)` para `lexico_negacao` é **FALSO**.

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
| `TROCA_OFFSET` | `1` |
| `Z_WILSON` | `1.96` |
| `SEED` | `20260818` |
| `ESCORE_CEGO` | `0.5` |
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
