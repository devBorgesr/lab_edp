# Pré-registro — Experimento 019
## As instruções compensatórias do system prompt previnem o que declaram prevenir?

**Congelado em 18/08/2026, ANTES de qualquer dado.**

---

## §1. Motivação (medida, não suposta)

O `SYSTEM_TEMPLATE` (`edp/llm_adapter.py`) tem **3.095 caracteres em 60 linhas**.
O slot `{context}` — onde as memórias recuperadas entram — está no caractere
**124**. Depois dele vêm **2.962 caracteres de instrução**, contra 1.000–3.000
caracteres de memória de fato recuperada (5 itens × 200–600 chars).

O modelo recebe o conteúdo e, em seguida, um manual do mesmo tamanho ou maior
sobre como lê-lo.

Doze das 60 linhas são proibições explícitas. Três dos quatro blocos não
instruem comportamento — **compensam falhas do sistema de memória**:

| linhas | chars | o que manda | defeito que tapa |
|---|---|---|---|
| 16–24 | ~560 | "NUNCA traga memórias antigas" | ranking traz memória antiga em vez do turno anterior |
| 26–34 | ~640 | "NÃO diga 'não tenho memória entre sessões'" | recuperação entrega nada relevante |
| 36–48 | ~830 | "é um SNIPPET, não o texto completo" | truncamento em 200–600 chars |
| 50–60 | ~450 | anti-verbosidade | instrução de comportamento (não compensa memória) |

**Este é o maior artefato não testado do caminho quente.** Ranking, dedup,
contradição, tokens e reflexão todos passaram por pré-registro. O system prompt
entra em **todo turno**, pesa mais que a memória recuperada, e nunca teve
hipótese, limiar, variante congelada ou medição. Cresceu por remendo: cada
regra é a cicatriz de uma falha, e nenhuma foi removida quando a falha foi
consertada.

## §2. Hipótese (declarada antes do dado)

- **H1:** Remover os blocos compensatórios (16–48) **aumenta** a frequência dos
  comportamentos que eles proíbem, nas queries que eles endereçam. As regras
  são portantes.
- **H0:** A frequência **não aumenta**. As regras são peso morto — cicatrizes de
  falhas já consertadas, ocupando 2.962 chars em todo turno sem efeito.

**H0 vencer é publicável** (NORTE §4.2) e é o resultado mais acionável dos dois:
autoriza encolher o prompt com medição, em vez de por gosto.

## §3. Condições (2 prompts × 2 estratos)

| condição | template |
|---|---|
| `completo` | `SYSTEM_TEMPLATE` verbatim, como em produção |
| `ablado` | idem, **sem** as linhas 16–48 (blocos compensatórios) |

O bloco 50–60 (anti-verbosidade) **permanece nas duas** — ele não compensa
memória, e removê-lo junto misturaria dois tratamentos.

**Modelo:** condição congelada, **registrada no ato do disparo** numa tabela
`§8-bis`. O resultado vale para o modelo registrado e para nenhum outro
(NORTE §4.12). Não se declara transferência entre modelos sem medir.

**Estado do índice:** o disparo roda com a configuração de produção do dia,
incluindo `EDP_SUMMARY_DEDUP=0` e `EDP_RETRIEVE_DEDUP=0`. Isto é **declarado, não
ideal**: em 18/08 mediu-se que 2 dos 5 itens entregues são frequentemente
duplicata. O resultado é condicional a esse estado, e uma réplica com dedup
ligado é **outro experimento**, não uma correção deste.

## §4. Estratos de query (o controle negativo é um estrato, não um terceiro prompt)

| estrato | n | o que contém | previsão ANTES do dado |
|---|---|---|---|
| `alvo` | 40 | pronome/follow-up, temporal/continuidade, citação de memória — o que os blocos 16–48 endereçam | efeito, se H1 |
| `controle` | 40 | lookup factual puro, sem pronome, sem referência temporal, sem citação | **sem efeito, nas duas hipóteses** |

Se o `controle` mover junto com o `alvo`, há confundidor e o resultado **não é
interpretável** — não é ajustado depois, é declarado inválido.

Dataset construído e **congelado antes do primeiro disparo**, num arquivo
versionado, com as queries escritas à mão. Não é gerado por LLM: query gerada
por modelo carrega o viés do modelo que a gerou.

## §5. Métricas (extrativas por decisão, não por conveniência)

**Nenhuma métrica usa julgamento de modelo.** O E10 mediu exatamente essa classe
— verificador como crítico autônomo — e a H1 foi **refutada**, porque a tarefa
que eu supus extrativa era parcialmente abstrativa. Aqui só entra o que é
contável por regra fixa.

1. **`nega_memoria`** (primária, binária): a resposta casa a lista congelada de
   frases de negação — `"não tenho memória"`, `"não tenho acesso a"`, `"não
   consigo lembrar"`, `"não tenho como saber"`, `"sou um modelo"`, cada uma como
   regex insensível a acento e caixa. A lista congela no §8 e não cresce depois
   do dado.
2. **`usa_turno_anterior`** (secundária, binária): a resposta contém ≥ 20 chars
   contíguos verbatim do item marcado `[turno anterior]` no contexto entregue.
   Extrativo: é comparação de substring, não juízo de relevância.
3. **`n_chars_resposta`** (descritiva): tamanho. Não entra em critério de
   decisão — está aqui porque o bloco 50–60 fica constante e um desvio grande
   sinalizaria confundidor.

## §6. Critério de decisão (travado, com poder MEDIDO)

**H1 confirmada** se, no estrato `alvo`, a diferença `ablado − completo` em
`nega_memoria` tiver IC 95% (Wilson, duas proporções) **excluindo zero** na
direção positiva, **E** o estrato `controle` **não** excluir zero.

Poder simulado antes do dado (20.000 réplicas, α=0.05, `N=40` por célula):

| efeito | poder em N=40 |
|---|---|
| 0.05 → 0.35 | **0.95** |
| 0.10 → 0.40 | **0.90** |
| 0.20 → 0.60 | **0.97** |
| 0.05 → 0.25 | **0.76** |
| 0.10 → 0.50 | 0.99 |

**Declarado, não escondido (NORTE §4.3):** com `N=40` este desenho **não** tem
poder para um efeito de 20 pontos a partir de base baixa (0.05→0.25 fica em
0.76). Se o efeito real for desse tamanho, um H0 aqui significa *"não detectado
com este poder"*, **não** *"não existe"*. A conclusão vai escrita assim.

`N=40` foi escolhido pelo poder acima, não por conveniência. Custo: 2 × 2 × 40 =
**160 chamadas**. Na régua do E9c (~17,5 s/req nesta máquina) ≈ **47 minutos**.

## §7. Anti-mock e isolamento

- O prompt `completo` é lido do `SYSTEM_TEMPLATE` real, não transcrito — cópia
  manual diverge silenciosamente do que produção usa.
- O `ablado` é derivado por remoção programática das linhas 16–48 do mesmo
  literal, e o harness **falha** se o corte não bater o número de chars
  esperado (guarda contra o template mudar sem o experimento notar).
- Store clonado, nunca o de produção. Nenhuma escrita volta.
- Ordem das queries embaralhada com seed congelado; as duas condições veem a
  mesma ordem.

## §8. Constantes congeladas (espelhadas em `exp019.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"019"` |
| `N_POR_CELULA` | `40` |
| `ALPHA` | `0.05` |
| `MIN_CHARS_VERBATIM` | `20` |
| `LINHAS_ABLADAS` | `(16, 48)` |
| `SEED` | `20260818` |
| `TOP_K` / `MIN_SCORE` | `5` / `0.0` |
| `CHARS_TEMPLATE` | `3095` |
| `CHARS_BLOCO_ABLADO` | `1877` |
| frases de negação | `não tenho memória`, `não tenho acesso a`, `não consigo lembrar`, `não tenho como saber`, `sou um modelo` |

As duas últimas foram **medidas** contra o template real em 18/08 (não
escolhidas) e acrescentadas ANTES do primeiro disparo — o congelamento vale
a partir dele, e o §7 já exigia a guarda sem nomear o número.

**CONGELADO ao primeiro disparo real. Mudou a régua → é o Experimento 020.**

## §9. O que este experimento NÃO responde

- **Não** mede qualidade de resposta. Mede a frequência de comportamentos
  específicos que regras específicas proíbem. Uma resposta pode piorar sem
  disparar nenhuma das métricas.
- **Não** testa reordenar o prompt (instruções antes das memórias em vez de
  depois). É uma manipulação diferente e merece número próprio.
- **Não** testa a hipótese de que **instrução negativa torna saliente o
  comportamento proibido**. Isso é folclore até alguém medir, e medir exige
  contrastar `NÃO diga X` contra uma formulação positiva do mesmo requisito —
  outro desenho.
- **Não** transfere entre modelos. Ver §3.

---

## §4-bis. Errata — o dataset passa a ser amostrado do log real

**18/08/2026, antes de qualquer dado.** O §4 exigia queries **escritas à mão**.
A regra fica registrada e o método muda, por dois motivos que a invalidam.

**1. Circularidade.** Quem escreveria as queries leu as 60 linhas do
`SYSTEM_TEMPLATE` primeiro. Qualquer pergunta escrita depois disso é calibrada —
mesmo sem intenção — para casar com o que as regras proíbem. Seria construir a
prova a partir do gabarito, e o experimento mediria se as regras bloqueiam
perguntas desenhadas para acioná-las. Isso confirma H1 por construção. Log real
não sabe que as regras existem.

**2. Taxa de base.** As regras nasceram de falhas reais, mas ninguém mediu com
que frequência essas falhas aparecem. Um bloco pode funcionar perfeitamente e
ainda assim custar 640 chars em **todo** turno para atender 1% do tráfego.
Query inventada **assume** a frequência; amostra real a **mede**. Sem log real
descobre-se se a regra funciona; com log real descobre-se se ela **vale a pena**
— que é a pergunta original.

### Fonte e critério (congelados aqui, antes de olhar o corpus)

- **Fonte:** entries do store vivo com `source_type == "user_input"`. Exclui
  `session_summary`, `llm_response` e `meta_conversation`.
- **Deduplicação:** por texto normalizado (`strip + casefold + colapso de
  whitespace`). Medido em 18/08: há 14 cópias extras no store, e amostrar sem
  deduplicar daria peso extra a quem está repetido.
- **Estratificação MECÂNICA**, por marcador, não por julgamento:

| estrato | regra de inclusão (congelada) |
|---|---|
| `alvo` | contém pronome/referência (`isso`, `sua resposta`, `o que você disse`, `qual a base`, `tirou`, `falou`) **OU** marcador temporal (`ontem`, `agora`, `antes`, `última vez`, `lembra`) **OU** citação de memória (`aquela`, `você falou de`) |
| `controle` | **nenhum** dos marcadores acima |

- **Amostragem:** aleatória sem reposição dentro de cada estrato,
  `SEED = 20260818`.
- As listas de marcadores **congelam aqui** e não crescem depois de ver o
  corpus.

### Se um estrato não encher, isso é RESULTADO — não é problema de dataset

Se o log real não fornecer 40 queries do estrato `alvo`, **não** se afrouxa o
marcador, **não** se escreve query à mão para completar, e **não** se reduz o N
em silêncio.

O N alcançado vai reportado, com o poder recalculado para ele. E a escassez
entra como achado primário: *os blocos 16–48 endereçam um caso que aparece em
X% do tráfego real* — que responde a pergunta de custo-benefício direto, sem
precisar do experimento principal.

Esta é a única forma de a impossibilidade de rodar virar informação em vez de
frustração (NORTE §4.3).

---

## §4-ter. Resultado da checagem de viabilidade — o estrato `alvo` não enche, e isso responde a pergunta

**18/08/2026, antes do disparo.** O §4-bis previa este caso e mandou tratá-lo
como achado. Ele ocorreu.

### O número

Corpus: `edp_data/sessions/default_cognitive/episodic.json`, snapshot de 18/08
12:14, **137 entradas → 75 perguntas únicas** após extração e dedup.

| estrato | n | fração |
|---|---|---|
| `alvo` | **3** | **4,0%** |
| `controle` | 72 | 96,0% |

IC 95% de Wilson sobre a fração `alvo`: **[1,4% ; 11,1%]**.

`N_POR_CELULA = 40` exige **37 queries a mais** no `alvo`. O desenho é inviável
neste corpus por um fator de ~13.

### O que isso já responde, sem rodar o experimento

> Os blocos 16–48 custam **1.877 chars em 100% dos turnos** e endereçam um caso
> que aparece em **4% do tráfego real** — no limite superior do IC, **1 turno em
> 9**.

Esta é a pergunta de custo-benefício que originou o exp019, e ela ficou
respondida pela construção do dataset. O experimento principal — *as regras
funcionam?* — segue aberto e agora é secundário: mesmo que funcionem
perfeitamente, funcionam para uma minoria pequena do tráfego.

### DUAS correções de instrumento achadas aqui (as duas antes de qualquer dado)

**1. `source_type == "user_input"` não existe neste store.** A regra de fonte do
§4-bis devolvia **zero**. As 137 entradas são `llm_response` (77),
`session_summary` (32), `meta_conversation` (18) e `camara_response` (10). A
pergunta do usuário vive **dentro** do texto do turno, na linha `Q:`. Eu supus a
estrutura do corpus sem conferir — o mesmo erro das três constantes Tier A do
arco E9.

**2. Casamento por substring, terceira vez no mesmo dia.** O marcador `antes`
casou dentro de **`importantes`**, promovendo uma query ao `alvo` indevidamente.
Corrigido para fronteira de palavra (`\b`), o que derrubou 4 → 3.

Nota sobre por que esta correção é legítima e não raciocínio motivado: ela torna
o critério **mais estrito** e o estrato **menor**. Uma correção que só pode
piorar a própria viabilidade não pode ter sido escolhida para salvar o
resultado. (As outras duas do dia: `prompt_eval_count` contendo `eval_count`, e
o catálogo de código morto.)

### CONFUNDIDOR que este número não resolve — e que pode invertê-lo

A baixa frequência pode ser **consequência** da falha, não evidência de que ela
não importa. Se perguntas de continuação falham, o usuário aprende a não
fazê-las. O relato que originou toda esta linha foi *"o contexto não está
lembrando da última conversa"* — exatamente o sintoma que faria alguém parar de
usar pronome e passar a repetir o assunto por extenso.

Isso é **seleção pelo desfecho**, e o corpus não consegue distingui-la de baixa
demanda genuína. Um corpus de usuário novo, ou traffic anterior à falha,
separaria as duas. Nenhum dos dois existe aqui.

**Portanto: o 4% mede a frequência OBSERVADA, não a demanda latente.** Qualquer
decisão de cortar os blocos com base só neste número herda esse confundidor, e a
decisão precisa dizer isso em voz alta.

### O que NÃO foi feito (§4-bis)

- **Não** se afrouxou nenhum marcador — a lista congelada segue intacta.
- **Não** se escreveu query à mão para completar o estrato.
- **Não** se reduziu `N_POR_CELULA` em silêncio.

O `N` alcançado fica reportado como está. O disparo do experimento principal
depende de corpus maior; até lá, o achado de frequência **vale sozinho** e é de
Tier D (medido), com o confundidor acima declarado.

---

## §4-quater. Exploratório (Tier C) — o confundidor NÃO foi resolvido

**18/08/2026.** Análise **exploratória**, não pré-registrada. Serve para dizer o
que o corpus **não** consegue decidir, e é rotulada Tier C por isso.

### Tentativa: a frequência de 4% caiu ao longo do tempo?

Se a baixa frequência fosse aprendizado (o usuário parou de usar pronome porque
não funcionava), esperaríamos queda temporal **e** perguntas ficando mais longas
e autocontidas. Duas previsões, feitas antes de olhar.

| terço | n | `alvo` | % | mediana chars | período |
|---|---|---|---|---|---|
| início | 25 | 2 | 8,0% | 35 | 31/05–04/06 |
| meio | 25 | 1 | 4,0% | 40 | 04/06–13/06 |
| fim | 25 | 0 | 0,0% | 39 | 13/06–09/08 |

**Resultado: inconclusivo, e uma das duas previsões falhou.**

- A direção da queda é consistente com aprendizado, mas **Fisher exato
  início vs fim: p = 0,49**. Com 3 eventos no total não havia como dar outra
  coisa. Isto **não é evidência**.
- A mediana de caracteres ficou **plana** (35 / 40 / 39). A previsão de
  autocontenção crescente **não se confirmou** — e era a metade que
  fortaleceria a hipótese.

**O confundidor segue aberto.** O corpus não distingue aprendizado de demanda
genuinamente baixa, e esta análise não mudou isso.

### Observação sobre a composição do estrato — com alerta sobre mim mesmo

Inspecionando as 3 queries do `alvo`, uma delas é:

> *"...hardware especializador para **isso**?"*

O marcador `isso` casou corretamente na fronteira de palavra, mas aponta para
**dentro da própria frase** — dêixis intra-sentencial, não referência ao turno
anterior, que é o que os blocos 16–24 endereçam. Pela **intenção** do estrato,
não deveria contar.

Se não contasse, a taxa cairia de 4,0% para **2,7%** (2/75).

**A lista de marcadores está congelada e NÃO foi alterada.** Fica registrada
como over-inclusiva, e o 4,0% do §4-ter permanece como o número oficial.

**Alerta explícito:** esta observação **fortalece** a conclusão que o §4-ter já
defende — os blocos servem pouco tráfego. Diferente da correção
`antes`/`importantes` (que piorava a viabilidade e por isso era imune a
raciocínio motivado), esta corre a favor de quem a fez. Por isso ela entra como
nota, não como número revisado, e a decisão de usar 4,0% ou 2,7% fica para quem
auditar — com a assimetria à vista.

---

## §1-bis. Errata — descrevi a ordem do prompt a partir do caminho MORTO

**19/08/2026, observando o prompt real em produção.** O §1 afirma:

> *"O slot `{context}` está no caractere 124. Depois dele vêm 2.962 caracteres
> de instrução... O modelo recebe o conteúdo e, em seguida, um manual do mesmo
> tamanho ou maior sobre como lê-lo."*

**Está errado.** O log de produção mostra o slot **vazio**:

```
Contexto da memoria (use SOMENTE se relevante para a pergunta atual):
                                    ← nada aqui
VOCE TEM ACESSO A INFORMACAO TEMPORAL — IMPORTANTE:
```

As memórias entram muito depois, num bloco próprio `=== MEMÓRIAS RELEVANTES ===`.

**Causa, verificada na fonte.** Há dois caminhos de montagem em `llm_adapter.py`:

| linha | código | quando roda |
|---|---|---|
| `:2661` | `system_prompt.format(context=ctx_str)` | **só se `ContextWindowManager` falhar ao importar** |
| `:2838` | `mgr.build(system_prompt=system_prompt.replace("{context}", "").strip(), ...)` | **produção** |

O caminho vivo **esvazia** o slot e passa as memórias separadas ao manager. Li o
template, vi o `{context}` na linha 4, e assumi que ele era preenchido — sem
conferir qual dos dois caminhos executa. É a terceira vez em dois dias que
"qual caminho realmente roda" me pega (as outras: telemetria de ranking
instalada no cosseno, e o laço `access_boost` descrito como vivo).

### A correção torna a motivação MAIS forte, não menos

Ordem real: **~3.081 chars de instrução, integralmente ANTES de qualquer
memória.** O modelo lê o manual inteiro — incluindo as 12 proibições e os três
blocos compensatórios — antes de ver uma única memória recuperada.

O argumento de **custo** do §1 não muda (1.877 chars em todo turno). O de
**posição** muda de "manual depois do conteúdo" para "manual antes do
conteúdo", que é uma situação diferente e não foi medida por ninguém.

### Efeito sobre o experimento

- **§2 (hipótese), §5 (métricas), §6 (critério): intactos.** Nada ali dependia
  da posição.
- **§7 (anti-mock): intacto.** A ablação corta linhas do literal, e o literal é
  o mesmo nos dois caminhos.
- **§9 ganha um item:** o exp019 **não** testa a ordem instrução-antes-de-memória
  contra memória-antes-de-instrução. Essa manipulação agora tem base concreta
  para existir como experimento próprio, e não existia quando o §9 foi escrito.
