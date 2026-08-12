# Pré-registro — Fase 2 da calibração de tokens

## A razão real chars→token do corpus do EDP difere do `4.0` herdado?

> **Régua da Bancada (método):** este documento declara hipótese, condições,
> métricas, dataset e critério de decisão **ANTES de qualquer dado**. A coleta
> não começou — `EDP_TOKEN_TELEMETRY` está default OFF e nenhuma amostra existe
> no momento em que isto é escrito. O harness (`sujeitos/edp/experimentos/`)
> congela ao primeiro disparo real. **Não se descongela para ajustar parâmetro
> depois de ver resultado**; bug que invalide ⇒ Fase 2b nova, não emenda.

**Status: CONGELADO em 2026-08-12**, no commit deste arquivo. Nenhuma amostra
existia quando isto foi escrito — `EDP_TOKEN_TELEMETRY` seguia default OFF.

**Quem decidiu o quê**, para que a autoria de cada corte fique auditável:

| decisão | valor | decidido por |
|---|---|---|
| volume e prazo da coleta | `N=300`, `30 dias`, `n_min=30` | **Daniel** — é o tempo e o custo dele em chamada real |
| predição pré-dado | só a do arquiteto (§4) | **Daniel** — optou por não predizer |
| estratificação primária | só por `classe` | arquiteto, §5 |
| critério | equivalência por IC bootstrap, faixa `[3.6, 4.4]` | arquiteto, §4/§6 |
| nível do IC | 90% nominal (`0.85–0.88` sob os dois geradores testados) | arquiteto, §4 — medido em simulação, não suposto |
| faixas de tamanho | `0–1k / 1k–4k / 4k+`, descritivas | arquiteto, §6 |
| numerador primário | `text_chars` | arquiteto, §9 |

Os cinco últimos passaram por duas rodadas de auditoria externa antes do
congelamento. **A partir daqui nada se descongela**: bug que invalide ⇒ Fase
2b nova, com dado novo, não emenda sobre dado visto.

---

## 3. Motivação / contexto provado

`edp/runtime/context_window_manager.py:12-13` divide todo orçamento de janela
por `4 chars ≈ 1 token`, com margem auto-declarada de ~10% e **nenhuma citação
de onde veio**. O corpus real do EDP é PT-BR + código — o pior caso para uma
razão universal, porque o vídeo de tokenização e o `TokenExploiter` do
GLOSSOPETRAE mostram que BPE é dependente de idioma e de raridade de termo.

O token real já chega em toda resposta da Anthropic (`usage.input_tokens`) e
era descartado. A Fase 1 (`edp_v5` `6131e12`) passou a gravá-lo junto do
tamanho em chars, do regime de formato e da classe de conteúdo.

**Contexto que NÃO é motivação:** nenhuma medição de razão foi feita. O smoke
da Fase 1 usou `input_tokens` placeholder (`text_chars // 4`) — não é dado.

## 4. Hipóteses e predições

Formuladas como **equivalência**, não como comparação pontual. A pergunta não
é "a razão medida caiu dentro de 10%" — é "há evidência de que a razão *real*
está dentro de 10%", e as duas são afirmações diferentes: a primeira ignora a
incerteza da estimativa.

**Faixa de equivalência: `[3.6, 4.4]`** (`4.0` ± 10%).

- **H0** — a razão real é compatível com `4.0`: IC 90% inteiramente **dentro**
  da faixa, em todos os estratos com `n ≥ n_min`.
- **H1** — a razão real difere: IC 90% inteiramente **fora** da faixa, em ao
  menos um estrato com `n ≥ n_min`.
- **INDETERMINADO** — IC cruza qualquer fronteira da faixa.

**O "90%" é rótulo, não garantia — medido antes de congelar.** Bootstrap
percentil sobre estimador de razão Σ/Σ **subcobre** em n pequeno. Medido com
`bancada.cobertura`, em três rodadas independentes (duas implementações, duas
sementes, dois modelos de ruído), n=30, nominal 90%:

| modelo de ruído | rodada | cobertura | reps | déficit |
|---|---|---|---|---|
| homocedástico | scipy, semente 7 | 0.878 | 2000 | 3.01 SE |
| homocedástico | scipy, semente 20260812 | 0.879 | 800 | **1.82 SE** |
| homocedástico | stdlib, semente 20260812 | 0.856 | 500 | 2.80 SE |
| homocedástico | **pool inverso-variância** | **0.8753** | 3300 | **4.30 SE** |
| overhead fixo | scipy, semente 7 | 0.877 | 2000 | 3.13 SE |
| overhead fixo | scipy, semente 20260812 | 0.858 | 800 | 3.40 SE |
| overhead fixo | stdlib, semente 20260812 | 0.846 | 500 | 3.35 SE |
| overhead fixo | **pool inverso-variância** | **0.8686** | 3300 | **5.35 SE** |

Déficit por rodada, e não um intervalo único: as rodadas têm precisões
diferentes (reps 500 a 2000) e misturá-las num "de X a Y" esconde isso. **Uma
célula fica em 1.82 SE**, abaixo da convenção de 2 — sozinha ela não sustentaria
"sistemático". O pool das três, que é o que sustenta, dá 4.30 e 5.35 SE.

> **ERRATA (12/08/2026).** A versão anterior desta seção dizia "déficit de 2.8
> a 3.3 erros-padrão" citando as três rodadas. Aqueles dois números eram os
> SE-múltiplos **de uma só rodada** (stdlib), copiados do output e apresentados
> como faixa das três. O intervalo inventado excluía a própria medição mais
> fraca (1.82 SE). Erro de quem escreveu, não de quem revisou — e num documento
> cujo ponto é não escrever número sem conferir. Texto anterior preservado aqui
> em vez de apagado, conforme regra 3 do projeto.

O
IC sai mais estreito que a incerteza real, e o erro é na direção de **aceitar
H0 falsamente**, que é justamente a direção conveniente. Por isso o critério
diz `IC 90% nominal (cobertura real medida ≈ 0.85–0.88)` e não `IC 90%`.

**Subir `n_min` não é a saída óbvia:** a mesma medição não mostra convergência
clara nem em n=200 (0.885), e 3 classes × 100 = 300 = exatamente o N alvo, sem
folga para as amostras excluídas e suspeitas que a cascata do §10 garante que
vão existir. E calibrar o nível nominal para compensar herdaria a suposição de
ruído sintético que a própria medição mostrou variar ~3pp entre sementes.

Instrumento e limite: `bancada/cobertura.py`. A direção do viés é conhecida da
literatura e não depende do gerador; **o número exato depende** — reporte a
ordem de grandeza, não o terceiro dígito.

**Declarado agora, para não parecer desenho falhado depois:** com `n_min = 30` e
**nenhuma estimativa prévia da variância** da razão — que é justamente o que
esta fase existe para medir, logo não há prior — é plausível que o IC saia mais
largo que a própria faixa `[3.6, 4.4]` na maioria dos estratos.
**INDETERMINADO é resultado esperado, não caso de borda.** Se acontecer, não é
falha: é a medição de variância que permite dimensionar o `n_min` de uma Fase
2b. Registrar isso antes é o que impede tratar um resultado previsto como
surpresa.

**Por que 10%:** o consumidor da razão é orçamento de janela. Com
erro de 10%, um cap de 12000 chars vale 2727 tokens em vez de 3000 — folga que
o sistema absorve. Com 25%, vale 2400: corte silencioso de conteúdo, que é o
defeito que a calibração existe para evitar. 10% é onde a consequência começa a
importar, não um limiar estatístico.

**H0 vencer é resultado publicável.** Se a razão der ≈4.0, o número herdado
estava certo e a Fase 3 não acontece — isso encerra a frente com economia, não
com fracasso. Declarado antes de propósito, para não virar "não achamos o
efeito que queríamos" depois.

**Predição pré-dado (arquiteto, antes de qualquer amostra):** H1 no estrato
`acentuado`, com razão **abaixo** de 4.0 (PT-BR acentuado gasta mais token por
char que o inglês em que o `4.0` foi calibrado). H0 no estrato `ascii`.
Indeterminado em `codigo`. Registro para poder ser refutada — o histórico
desta frente é de predições majoritariamente erradas e honestamente relatadas.

## 5. Condições / desenho

Observacional, não intervencional: nenhuma condição é manipulada. O que
estratifica é o que o uso real produzir.

| eixo | níveis | papel |
|---|---|---|
| **classe de conteúdo** | `acentuado`, `codigo`, `ascii` | **PRIMÁRIO** — decide H0/H1 |
| regime de formato (`format_hash`) | 2 por processo (ver abaixo) | secundário — descritivo, nunca decide |
| faixa de tamanho | `0–1k`, `1k–4k`, `4k+` chars | secundário — saída de calibração (§6) |

**Por que `classe` é o eixo primário e `format_hash` não:** a pergunta de
pesquisa (§3) é inteiramente sobre conteúdo — PT-BR acentuado vs. código vs.
ASCII. `format_hash` entrou no desenho como **guarda contra confundimento**,
não como pergunta. Promovê-lo a eixo primário responderia algo que ninguém
perguntou, ao custo de multiplicar o N necessário.

**Correção de uma premissa que quase entrou aqui.** A revisão externa supôs que
`3 classes × N format_hash` faria N explodir sem limite. **Verifiquei, e a
cardinalidade é estruturalmente limitada:** as 9 flags de
`FORMAT_STATE_FLAGS` são constantes de módulo avaliadas **no import**
(`config.py:53,65,87,…`) e nenhum ponto de `edp/` as reatribui — grep
confirmado. Dentro de um processo, só `mode` varia, então **o `format_hash`
assume exatamente 2 valores** (verificado: `69d14ba8…` cognitive,
`a5fbbd5f…` sprint). Com 3 classes × 2 regimes × `n_min` 30 = 180, cabe
dentro de N=300.

Ou seja: a decisão de rebaixar `format_hash` a secundário está certa, mas **não
pelo motivo alegado** — não é explosão de N, é escopo de pergunta. Reinícios do
processo com env diferente adicionam hashes, mas cada um é ato deliberado, não
deriva.

## 6. Critério de decisão (PASSA/FALHA)

Por estrato de **classe** com `n ≥ n_min`:

```
razão      = Σ text_chars / Σ usage.input_tokens   (agregada, não média de razões)
IC 90%     = bootstrap não-paramétrico, 10.000 reamostragens, percentil
             reamostra PARES (text_chars, input_tokens) e recalcula Σ/Σ
faixa      = [3.6, 4.4]

PASSA H0        sse  IC inteiramente dentro da faixa
PASSA H1        sse  IC inteiramente fora da faixa
INDETERMINADO   sse  IC cruza a faixa, OU n < n_min
```

Razão **agregada** (soma sobre soma), não média de razões por amostra: média de
razões pondera igualmente um prompt de 200 chars e um de 12000, e o primeiro é
justamente onde o andaime domina.

**Bootstrap e não erro-padrão de média.** A razão é um estimador Σ/Σ, não uma
média simples; aplicar SE de média sobre ela seria usar a fórmula errada. O
bootstrap reamostra no nível da amostra (o par), o que preserva a estrutura do
estimador sem exigir suposição de distribuição — que não temos.

**Guarda de dependência de tamanho — dois instrumentos, papéis distintos.**

O smoke mostrou `payload_bytes` (379) ≈ 2× `text_chars` (194) em prompt curto,
com a divergência encolhendo conforme o prompt cresce.

*(i) Spearman como descritiva, SEM limiar.* Correlação de posto entre
`text_chars` e a razão por amostra, dentro do estrato, **reportada sempre e
decidindo nada**.

Uma versão anterior deste documento tinha `|ρ| > 0.3` como gatilho. O limiar
foi **removido**: era número sem origem — o texto explicava o conceito da
guarda e não por que 0.3 e não 0.25, exatamente o defeito Tier A que
`instrumentos/TIERS_DE_JUSTIFICATIVA.md` cataloga, escrito por quem catalogou.
Como a saída por faixa (ii) passou a ser incondicional, o gatilho ficou
redundante: não havia decisão para ele tomar. **Eliminar o número foi mais
barato que justificá-lo.**

Sobre a objeção de que isso seria circular por ter `text_chars` nos dois lados:
não é. Se `input_tokens = text_chars/4 × (1+δ)` com `δ` independente do
tamanho, a razão colapsa para `4/(1+δ)` — **sem correlação nenhuma com
`text_chars`**, em qualquer N. Spearman só dispara se o desvio realmente escalar
com o tamanho, que é exatamente o efeito de andaime-fixo que se quer capturar.
É teste indireto, e válido.

*(ii) Faixas fixas como saída de calibração.* Spearman diz **se** há dependência
monotônica; não diz **onde** ela deixa de importar — e o que decide `CAP_CHARS`
é justamente onde. Faixas congeladas agora, antes de qualquer dado:

| faixa | `text_chars` | por que este corte |
|---|---|---|
| curto | `0 – 1.000` | onde o andaime JSON é fração relevante do payload |
| médio | `1.000 – 4.000` | ordem do cap turno-1 em `cognitive` (4000) |
| longo | `4.000 +` | ordem do cap turno-1 em `sprint` (12000) |

Os cortes vêm dos caps que o sistema realmente usa (`CAPS_POR_MODO`), não de
quantis do dado — quantil escolhido depois de ver a distribuição é escolher
onde a resposta fica melhor.

**A faixa é DESCRITIVA, não eixo de decisão.** Razão reportada por faixa dentro
de cada classe, sempre e incondicionalmente — é a saída que calibra
`CAP_CHARS`. Mas **PASSA/FALHA continua agregado por classe**, pelo mesmo
motivo que rebaixou o `format_hash` na §5: a pergunta da §3 é sobre conteúdo, e
tamanho de prompt é saída de calibração, não hipótese a testar.

A aritmética confirma: 3 classes × 3 faixas = 9 células × `n_min` 30 = 270 de
300 — a mesma inviabilidade da opção "n_min=100", em escala menor. Promover
faixa a eixo de decisão gastaria 90% do N respondendo o que ninguém perguntou.

**Nada disso se descongela.** Se um defeito invalidar a coleta, abre-se Fase 2b
com dado novo; não se ajusta limiar, faixa nem `n_min` sobre dado visto.

**Não se descongela.** Se um defeito invalidar a coleta, abre-se Fase 2b com
dado novo; não se ajusta limiar sobre dado visto.

## 7. Data de pré-registro

Escrito e congelado em **2026-08-12**, antes de qualquer amostra existir
(`EDP_TOKEN_TELEMETRY` default OFF em todo o intervalo). O commit que
introduz este arquivo é o ato de congelamento e precede o commit de
qualquer resultado — é isso que torna a ordem auditável (`NORTE.md §4.2`).

## 8. Dataset (CONGELADO)

**População:** definida por `edp.runtime.pareto_store.amostra_valida_fase2` —
o harness **importa a função**, não re-implementa o filtro. Contrato completo em
[`sujeito_edp/CONTRATO_FASE1_TOKENS.md`](sujeito_edp/CONTRATO_FASE1_TOKENS.md).

**Janela de coleta:** abre ao ligar `EDP_TOKEN_TELEMETRY=1`; fecha no primeiro
dos dois: **300 amostras válidas** ou **30 dias corridos**.
`n_min` por estrato: **30** — convenção (regra de bolso do TLC),
não medição, e registrada como convenção.

**Regra de parada é fixa, não sequencial.** Não se olha o dado para decidir
quando parar; olhar N acumulado é permitido, olhar a razão não. Parada por
precisão atingida inflaria o resultado.

**Exclusões, todas contadas e reportadas:**

| exclusão | motivo | destino |
|---|---|---|
| `format_state is None` | câmara e `cognitive_decisions` — outra população | contada, fora |
| `provider != "anthropic"` | não instrumentado | contada, fora |
| tokens incompletos | par falso envenenaria a razão | contada, fora |
| turno sobreposto a `mode_switched` | corrida `mode→prompt`, `CONTRATO §8-bis` — regime declarado pode não ser o usado | **contada, fora da análise primária, reportada à parte** |

**Cascata obrigatória no relatório** (`CONTRATO §10`): bruta → provider →
`format_state` → tokens → população → suspeitas → excluídas → analisadas. Toda
redução explicável; `n=300` solto não é resultado.

## 9. Métricas

| métrica | definição |
|---|---|
| razão primária | `Σ text_chars / Σ input_tokens` |
| IC da razão | bootstrap percentil sobre pares (`bancada.cobertura`), nominal 90%, **cobertura real medida ≈ 0.85–0.88** |
| razão secundária | `Σ payload_bytes / Σ input_tokens` — reportada sempre, nunca decide |
| ρ tamanho×razão | Spearman, **descritiva** — reportada, não decide (§6) |
| razão por faixa | por classe × faixa de tamanho, saída (ii) da §6 |
| n por estrato | contagem, por classe e por classe×faixa |

**`text_chars` como primária, escolhido por mecanismo e não por
resultado:** é o texto que a API tokeniza. `payload_bytes` inclui o andaime
JSON, que a API não cobra e cujo tamanho escala com `n_messages`. A escolha é
declarada aqui, antes do dado, precisamente porque as duas estão gravadas e
escolher depois seria escolher a que der o número mais bonito.

## 10. Anti-mock e isolamento

Zero mock: as amostras vêm de uso real contra a API real, geradas pelo Daniel.
Nenhuma é sintetizada. O harness **lê** o JSONL do Pareto e não chama LLM
nenhum — a análise não pode gastar token nem tocar rede.

Fronteira `bancada/` ↔ `sujeitos/`: a estatística genérica sobre JSONL vai em
`bancada/`; o conhecimento do schema `token_usage` vai em `sujeitos/edp/`.
`tests/test_fronteira.py` trava que `bancada/` não importe `edp.*`.

## 11. Constantes congeladas

| constante | valor | origem |
|---|---|---|
| razão herdada sob teste | `4.0` | `context_window_manager.py:12-13` |
| faixa de equivalência | `[3.6, 4.4]` (4.0 ± 10%) |, §4 |
| nível do IC | `90%` nominal / `≈0.85–0.88` real |, medido em `bancada.cobertura` |
| reamostragens bootstrap | `10.000` | convenção |
| estrato primário | `classe` (3 níveis) | §5 |
| `n_min` por estrato | `30` |, convenção (TLC) |
| N alvo | `300` | |
| prazo máximo | `30 dias` | |
| faixas de tamanho | `0–1k / 1k–4k / 4k+` |, cortes de `CAPS_POR_MODO`, descritivas |
| numerador primário | `text_chars` |, §9 |

---

## Congelamento

Este documento passa a ser contrato no commit que o introduz. O harness
(`sujeitos/edp/experimentos/`) ainda não existe e congela ao primeiro disparo
real contra o JSONL coletado.

**A coleta pode começar**: ligar `EDP_TOKEN_TELEMETRY=1` no ambiente onde o EDP
roda contra a API real. Ligar a flag é também a declaração de que o formato de
injeção está congelado — mudança de regime a partir daí é detectável pelo
`format_hash` e vira estrato, não contaminação.

**Enquanto a coleta estiver aberta, não se olha a razão.** Olhar N acumulado é
permitido (é a regra de parada); olhar a razão não, porque parada por resultado
observado invalidaria o critério que este documento acabou de congelar.

Instrumentos: `bancada/cobertura.py` (validação de cobertura de IC),
`edp.runtime.pareto_store.amostra_valida_fase2` (população).
Contrato da amostra: [`sujeito_edp/CONTRATO_FASE1_TOKENS.md`](sujeito_edp/CONTRATO_FASE1_TOKENS.md).

---

## OBJEÇÃO REGISTRADA APÓS O CONGELAMENTO (12/08/2026)

Auditoria externa levantou, depois do commit de congelamento, uma objeção ao
critério. **O critério NÃO muda** — "nada se descongela" vale inclusive contra
objeção procedente. Fica registrada aqui porque quem ler o resultado precisa
saber que ela foi feita, por quem, e por que o critério permaneceu.

**A objeção.** O viés de subcobertura empurra na direção de **aceitar H0
falsamente** — e H0 é o resultado conveniente (encerra a frente com economia,
Fase 3 não acontece). A resposta dada foi trocar o rótulo do IC em vez de
compensar o viés. A compensação padrão — subir o nível nominal (ex.: pedir IC
94–95% para mirar cobertura real de ~90%) — é barata e independente do BCa que
foi descartado.

**Por que a objeção é forte, e mais do que a rejeição original admitiu.** O
documento rejeitou calibrar o nível nominal (§4) alegando que o fator de
correção herdaria a suposição de ruído sintético, que variou ~3pp entre
sementes. Esse argumento é mais fraco do que pareceu na hora: **errar para mais
é seguro**. Um IC calibrado em excesso fica largo demais, produzindo mais
INDETERMINADO — a direção conservadora. Um IC não calibrado erra exatamente na
direção que importa. Correção grosseira domina correção nenhuma quando o erro
de sobrecorrigir é benigno.

Vale nomear por que o sinal inverte em relação à intuição usual: num teste
comum, IC estreito favorece **rejeitar** H0. Num teste de **equivalência**,
PASSA H0 exige o IC inteiramente **dentro** da faixa — então IC estreito
favorece **aceitar** H0. A subcobertura, aqui, é pró-conveniência.

**Por que o critério permanece assim mesmo.**

1. Alterar limiar depois do congelamento é a coisa exata que este documento
   proíbe. Uma objeção procedente não é exceção; se fosse, "congelado"
   significaria "congelado até alguém argumentar bem".
2. A exposição é limitada pelo que já está declarado no §4: **INDETERMINADO é
   o resultado esperado**. Não se aceita H0 falsamente em estrato que nunca
   chega a H0. O viés só morde em estrato que simultaneamente atinge `n_min`
   **e** cai perto da fronteira `[3.6, 4.4]`.
3. Se morder, o remédio é **Fase 2b com nível nominal calibrado**, sobre dado
   novo — não emenda sobre dado visto.

**Como isto deve ser lido no resultado.** Um veredito PASSA H0 nesta fase
carrega **menos peso probatório** do que "IC 90%" sugere. Quem citar o
resultado cita com esta seção junto.

**Duas partes da mesma objeção que foram verificadas e não procedem** (o
auditor não tinha acesso a este repositório e auditou por consistência do
relato):

- *"Calibrar o nível nominal não aparece cogitado em nenhum lugar do texto"* —
  aparece, §4, linhas 100-101, com a razão da rejeição escrita. A rejeição era
  fraca, como admitido acima; a ausência, não é fato.
- *"N e n_min foram travados antes de a propriedade de cobertura ser
  conhecida"* — a medição precedeu a decisão. A pergunta feita ao Daniel
  trazia a subcobertura no enunciado das opções, e a opção `n_min=50` era
  explicitamente descrita como "ataca a subcobertura medida (0.85–0.88 em
  n=30)". Ele escolheu `n_min=30` **com** o achado à vista, não antes dele.

**Uma terceira parte procede e foi corrigida acima:** a frase "cobertura real
MEDIDA" comunicava mais do que se mediu. O que se mediu é cobertura sob dois
geradores sintéticos; a distribuição real char→token do EDP não existe ainda.
Texto anterior preservado nesta seção, corrigido na tabela do cabeçalho.
