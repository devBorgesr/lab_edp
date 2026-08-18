# Pré-registro — Experimento E9b
## A diferença de custo entre cargas conhecidas é causada pela carga, e não por confundidor correlacionado a ela?

**Bancada de Contexto — EDP.** Categoria **VALIDAÇÃO DE INSTRUMENTO**, segunda
tentativa. O E9 reprovou no próprio cheque de sanidade e **não avaliou** a
questão confirmatória. O E9b não reinterpreta o E9: coleta novo.

> **Régua da Bancada:** hipótese, condições, métricas, dataset e **regras
> estatísticas** congelados ANTES de qualquer coleta nova. A encarnação
> (`exp_e9b.py`) espelha este `.md` e congela ao 1º disparo real. Mudou a
> régua → é o E9c.

**Data de pré-registro: 2026-08-14**, antes da primeira amostra do E9b.

---

## §1. A pergunta

Duas perguntas, e a segunda é a que o E9 nem chegou a fazer:

1. O instrumento **resolve** uma diferença de carga conhecida?
2. A diferença medida é **causada pela carga**, e não por algo que apenas
   acompanha a carga?

---

## §2. Régua e congelamento

Congela ao primeiro disparo real. As amostras do E9 são **piloto**: servem
para dimensionar e corrigir este desenho, **nunca como evidência do E9b**.

Piloto informa **projeto**; dado confirmatório determina **critério**. A
primeira operação é legítima e auditável; a segunda ao contrário é escolher a
régua com o resultado na mão, e está proibida no §13 do E9.

---

## §3. Contexto provado — as três conclusões, separadas

Separadas de propósito, porque misturá-las é como um resultado nulo vira
alegação positiva.

### 3.1 O que o E9 DEMONSTROU

**O instrumento original não passou no próprio teste de sanidade.** Veredito
`SANIDADE FALHOU (recarga de modelo)`, §6.3. A cascata parou antes do passo
confirmatório. Nada foi afirmado sobre H1.

Passaram, e valem: **controle negativo OK** (`base_A` IC[53,418·56,957] e
`base_B` IC[53,844·57,632], byte-idênticas, sobrepostas) e **carga em 1,99×**.

### 3.2 O que o piloto SUGERE (não demonstra)

`load_duration` parece ter componente **aproximadamente uniforme por
requisição**, e não distribuição compatível com poucas recargas ocasionais:

```
min=2,73%   p50=5,94%   p90=6,56%   p99=7,29%   max=19,69%
acima do teto de 1,0%:  1080/1080  (100,0%)
```

O mínimo já é 2,7× o teto. Recarga real produziria maioria perto de zero com
cauda alta; a banda observada é estreita e alta.

**Consequência para o desenho, e é mais grave que o limiar errado:**
`load_duration` **não entra no estimador** `prompt_eval_duration /
prompt_eval_count`. O §6.3 do E9 guardou uma grandeza que está fora da conta.
Corrigir a magnitude do teto não teria consertado nada.

### 3.3 O que NÃO foi demonstrado

**Que a diferença de ~27,7 ms/token entre `base_A` e `dobro` é causada
exclusivamente pela carga de prompt.** Dois pontos não distinguem "custo
cresce com o comprimento" de "algo muda de regime entre 1× e 2×" — cache de
prefixo, caminho de alocação de KV, escalonamento de threads.

Este é o trabalho do E9b, e é a razão da condição nova do §5.

---

## §4. Hipóteses

- **H1 — resolve.** O IC 95% de `R_efeito` exclui 1,0 e fica acima de 1,0.
- **H2 — dose-resposta.** O custo unitário cresce **monotonicamente** com a
  carga: `R(meio) < R(dobro)`, com ICs que não se cruzam na ordem inversa.
- **H0 — não resolve, ou não é a carga.** Qualquer uma falha.

**H0 vencer é achado.** Se H1 passa e H2 falha, o instrumento separa mas a
causa não é o comprimento — e isso é mais informativo que um H1 sozinho,
porque desqualifica o uso da régua para comparar cargas intermediárias, que é
exatamente o caso do E10/E12.

---

## §5. Condições

| rótulo | carga alvo | papel |
|---|---|---|
| `base_A` | 1,0× | referência |
| `base_B` | 1,0×, **byte-idêntica a `base_A`** | **controle negativo** |
| `meio`   | ~1,5× | **dose-resposta** (novo no E9b) |
| `dobro`  | ~2,0× | efeito |

`meio` existe por causa do §3.3. Com três pontos de carga, "custo cresce com o
comprimento" prevê monotonicidade suave; "algo muda de regime" prevê salto.
Dois pontos não separam as duas histórias; três separam.

---

## §6. Critério — regras estatísticas congeladas

### 6.0 Estimador (§9) e por que não é "os ICs se sobrepõem"

Comparar dois ICs marginais é regra fraca e, para o controle negativo, é
**invertida**: ali quero provar *igualdade*, e IC largo sobrepõe trivialmente.
Um controle que passa por falta de resolução é teatro.

Por isso o E9b estima a **razão entre condições, diretamente**, com IC próprio:

```
R(X) = custo_unitario(X) / custo_unitario(base_A)
custo_unitario(X) = Σ prompt_eval_duration(X) / Σ prompt_eval_count(X)
```

### 6.1 VALIDADE — equivalência do controle negativo

`base_A` e `base_B` são byte-idênticas. Passa **sse**:

```
IC95( R(base_B) )  ⊂  [1 − DELTA_EQUIV , 1 + DELTA_EQUIV]
```

Teste de **equivalência**, não de diferença — o CI inteiro tem de caber na
margem. IC largo agora **reprova**, que é o comportamento correto.

Falhou → **INSTRUMENTO INVÁLIDO**, nada é afirmado sobre `meio` ou `dobro`.

### 6.2 SANIDADE — `load_duration` é comum às condições

Sobre `load_duration` **ABSOLUTO**, não sobre a fração. A fração cai
mecanicamente em `dobro` porque `total_duration` cresce; medi-la mediria o
denominador. Este é o erro do §6.3 do E9, corrigido.

```
IC95( mediana load_duration(dobro) / mediana load_duration(base_A) )
       ⊂ [1 − DELTA_EQUIV , 1 + DELTA_EQUIV]
```

Overhead comum não pode explicar diferença entre condições, e não entra no
estimador. Se diferir, entra — e aí é confundidor de verdade.

### 6.3 SANIDADE — recarga real, por FORMA e sem limiar novo

Recarga é `load_duration > FATOR_OUTLIER × mediana(load_duration)` — reusa a
constante já congelada em `FATOR_OUTLIER = 5.0`, medida contra a **própria
distribuição de `load_duration`**, não contra `total_duration`.

Reprova se a fração de recargas exceder `MAX_DESCARTE_FRAC`.

### 6.4 SANIDADE — as cargas atingiram os alvos

`meio` ∈ `TOLERANCIA_MEIO`, `dobro` ∈ `TOLERANCIA_CARGA`, medidos em
`prompt_eval_count` mediano contra `base_A`.

### 6.5 CONFIRMATÓRIO — H1

Com 6.1–6.4 passando: `IC95( R(dobro) )` exclui 1,0 **e** o limite inferior
> 1,0.

### 6.6 CONFIRMATÓRIO — H2 (dose-resposta)

`IC95( R(meio) )` exclui 1,0, limite inferior > 1,0, **e** o limite superior
de `R(meio)` < limite inferior de `R(dobro)`.

### 6.7 Ordem

6.1 → **6.3** → **6.2** → 6.4 → 6.5 → 6.6. **Para no primeiro que falhar.** A inversão de 6.2/6.3 é a emenda E9b-5.

### 6.8 Descritivo, explicitamente NÃO critério

A magnitude de `R(dobro)`. O piloto deu 1,50×; o §7 registra predição. Não
decide nada.

---

## §7. De onde vem `DELTA_EQUIV`, e a honestidade sobre isso

> **SUPERADO PELA EMENDA E9b-1 (§11-bis).** O valor congelado é `0.07`, não
> `0.02`. O texto abaixo fica preservado porque é instrutivo: mostra um
> raciocínio que se declarava cuidadoso, listava a tentação e a recusava — e
> ainda assim produziu um critério **matematicamente inatingível**, porque
> nenhuma das duas opções que eu considerei checou se o IC caberia na margem.
> Apagá-lo esconderia justamente a lição.

`DELTA_EQUIV = 0.02`. Duas margens seriam possíveis e a diferença importa:

- **Escolha de projeto (esta):** o instrumento precisa resolver, no E10/E12,
  efeitos de memória que serão **muito menores** que 2×. Um piso de artefato
  de 2% significa capacidade de resolver efeitos a partir de ~4%. É requisito
  de engenharia declarado antes da coleta.
- **Ajuste ao observado (recusada):** o piloto mostrou o controle em 1,0%
  (55,749/55,197 = 1,010). Escolher a margem *para caber* nisso seria
  garantir aprovação.

**Declaro o incômodo em vez de escondê-lo:** eu vi o 1,0% do piloto antes de
escrever `0.02`. Não há como desver. O que torna isto defensável e não
circular é que 2% deixa **espaço real para reprovar** — uma degradação de 2×
em relação ao piloto derruba o controle — e que a margem está amarrada a um
requisito do experimento seguinte, não ao número observado. Piloto informando
projeto é padrão; piloto determinando critério confirmatório não é.

### Predição pré-dado do arquiteto

Registradas antes de qualquer amostra do E9b, para poderem ser refutadas:

- **6.1 passa** — confiança alta.
- **6.2 passa** — confiança média. É o cheque novo e nunca foi medido.
- **H1 confirmada** — confiança alta.
- **H2 confirmada** — confiança **média-baixa**. Custo unitário mistura termo
  linear (FFN) e quadrático (atenção); monotonicidade é esperada, mas os ICs
  de `meio` e `dobro` podem não separar com esta margem.
- `R(dobro)` entre **1,45× e 1,60×**. O piloto deu 1,50×.

---

## §8. Dataset CONGELADO

Os mesmos 12 prompts do E9 §8, mesma `SEED`, mesma regra de preenchimento
calibrada pelo motor (E-3/E-4). **Amostras novas** — nenhuma reaproveitada.

Ordem intercalada e embaralhada. Descarte de aquecimento antes de qualquer
estatística. `temperature=0`, `num_predict` fixo, `seed` fixa.

---

## §9. Métricas, e a cobertura do IC verificada ANTES de armar

O estimador `R(X)` é **razão de razões** e o lab **não** tem cobertura medida
para ele. `bancada.cobertura.ic_bootstrap_percentil` cobre `Σa/Σb`, não o
quociente de dois.

**Trava, e ela é bloqueante:** antes de armar, roda-se
`bancada.cobertura.cobertura_simulada` sobre o bootstrap conjunto de `R`, no
`n` deste desenho. Cobertura medida `< COBERTURA_MINIMA` ⇒ **não arma** — sobe
o `n` ou troca o estimador.

Isto não é zelo: o §3.4 do E9 exige IC com cobertura verificada, e o mesmo
bootstrap percentil já foi medido sub-cobrindo em n pequeno neste lab
(0,846–0,879 contra 0,90 nominal, `df5e055`). Estrear estimador novo sem medir
repetiria, na estatística, o erro que o `LOAD_DURATION_MAX_FRAC` cometeu na
sanidade.

### Cobertura MEDIDA antes de armar — a trava foi executada

`bancada.cobertura_de_estimador` sobre `ic_bootstrap_razao_de_razoes`,
n=360 por condição, 95% nominal, semente `20260814`:

| cenário | cobertura | déficit | veredito |
|---|---|---|---|
| `R` verdadeiro = 1,50 (efeito) | **0,9467** | +0,26 SE | passa |
| `R` verdadeiro = 1,00 (controle) | **0,9650** | −1,15 SE | passa |

**O estimador novo não sub-cobre em n=360** — diferente do bootstrap de razão
simples, que sub-cobria em n pequeno. Piso `COBERTURA_MINIMA = 0.90`
satisfeito nos dois cenários.

A mesma execução mediu a **largura** do IC, e foi ela que reprovou o
`DELTA_EQUIV` original — ver emenda E9b-1.

---

## §10. Anti-mock e isolamento

Idênticos ao E9 §10: motor real, produção do EDP intocada, harness ocioso
durante a inferência, registro bruto dos seis campos por requisição.

---

## §11. Constantes congeladas (espelhadas em `exp_e9b.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"E9b"` |
| `K_PROMPTS` | `12` |
| `N_REPETICOES` | `30` |
| `N_AQUECIMENTO` | `5` |
| `TOLERANCIA_CARGA` | `(1.8, 2.2)` |
| `TOLERANCIA_MEIO` | `(1.35, 1.65)` |
| `DELTA_EQUIV` | `0.10` *(E9b-6)* |
| `TEMPERATURA` | `0` |
| `NUM_PREDICT` | `64` |
| `SEED` | `20260814` |
| `N_BOOTSTRAP` | `10000` |
| `NIVEL_IC` | `0.95` |
| `COBERTURA_MINIMA` | `0.90` |
| `FATOR_OUTLIER` | `5.0` |
| `MAX_DESCARTE_FRAC` | `0.05` |
| condições | `base_A`, `base_B`, `meio`, `dobro` |
| `MODELO` | `"llama3.2:1b"` |
| `TOPOLOGIA` | `"windows_local"` |

`N_REPETICOES` **permanece em 30**, e a razão é contra-intuitiva: o `n` aqui é
dimensionado pelo **controle negativo**, não pelo efeito. Pelo piloto,
`n ≈ 6` por condição já separaria `dobro` de `base_A`. Mas o controle exige
**equivalência dentro de 2%**, e IC largo reprova. Cortar o `n` para economizar
tempo tornaria o controle impossível de passar — ou, com a regra antiga de
sobreposição, fácil demais. Em ambos os casos, teatro.

**CONGELADO ao primeiro disparo real. Mudou a régua → é o E9c.**

---

## §11-bis. Emendas PRÉ-DADO do E9b

Nenhuma amostra do E9b existe. Verificável por `git log`.

### E9b-1 — `DELTA_EQUIV` era inatingível · 2026-08-14

**A trava do §9 reprovou o critério antes de armar.** Ao medir a cobertura do
estimador novo, mediu-se também a **largura** do IC de `R`, e ela decide se o
teste de equivalência é sequer possível.

Simulação calibrada contra o piloto — `ruido_rel = 0.28` reproduz a
meia-largura relativa observada no E9 (3,29% simulado contra 3,206% medido):

| | |
|---|---|
| largura média do IC de `R` em n=360 | **0,0937** |
| margem de `DELTA_EQUIV = 0.02` | 0,040 |
| folga | **0,43× — NÃO CABE** |
| mínimo matemático | `DELTA_EQUIV > 0,0469` |

**O critério original era inatingível.** O IC é 2,3× mais largo que a margem;
o controle negativo reprovaria **sempre**, por falta de resolução e não por
artefato. É o mesmo tipo de defeito que o projeto já documentou no honeypot
("≥5 de 14" excedia o teto do pool, declarado antes de rodar) e o §4.3 do
NORTE manda declarar, não esconder.

**Novo valor: `DELTA_EQUIV = 0.07`**, derivado de duas fronteiras e não de
gosto:

- **Piso (viabilidade):** `> 0,0469`, senão o teste não pode passar.
- **Teto (utilidade):** a margem tem de ser pequena o bastante para que um
  controle aprovado **descarte artefatos capazes de explicar o efeito**. Com
  efeito de ~50% (piloto), exigir `δ ≤ 1/5` do efeito dá `δ ≤ 0,10`.
- Escolhido `0,07`: dentro da janela `[0,047 · 0,10]`, com folga de
  viabilidade de 1,5×.

**O que isso custa, declarado:** o piso de artefato do instrumento passa a ser
7%, ou seja, ele resolve efeitos a partir de ~14%. Se o efeito de memória no
E10/E12 for menor que isso, **este instrumento não o mede** — e essa é uma
limitação do E9b, não do E10.

**Por que isto não é escolher a régua com o dado na mão.** A distinção é
inteira e vale escrevê-la:

| | |
|---|---|
| **proibido** | mudar o limiar depois de ver o resultado confirmatório, fazendo o veredito virar |
| **isto** | provar, **antes de qualquer amostra confirmatória existir**, que o critério é matematicamente impossível, e substituí-lo pelo mais apertado que é viável — declarando a resolução perdida |

O primeiro salva a hipótese; o segundo salva o experimento de não medir nada.

### E9b-3 — `load_duration` agregado por MÉDIA, não mediana · 2026-08-14

O §6.2 pedia razão de **medianas**. A encarnação usa **média**, via pares
`(load_duration, 1.0)` no mesmo `ic_bootstrap_razao_de_razoes`.

Motivo: o §3.4 exige IC com cobertura **verificada**, e a cobertura medida
(§9) é a do estimador `Σa/Σb`. Um IC de razão de medianas teria cobertura
desconhecida — o mesmo defeito que este pré-registro acabou de corrigir na
margem de equivalência. Trocar rigor de cobertura por robustez a outlier seria
piorar o que se está consertando.

A cauda é tratada onde tem instrumento próprio: o §6.3 detecta recarga real
por forma, contra a distribuição do próprio `load_duration`.

### E9b-4 — preenchimento ANINHADO entre os degraus · 2026-08-14

O §5 não dizia se o texto de `dobro` estenderia o de `meio` ou seria
independente. Congelado: **estende**. `calibrar_escada()` faz um crescimento
só e captura em dois pontos.

Aninhar remove o conteúdo do preenchimento como variável entre os degraus — o
que muda de `meio` para `dobro` passa a ser **só comprimento**, que é
exatamente a variável da dose-resposta do §6.6. Com preenchimentos
independentes, um salto entre degraus poderia vir do texto e não do tamanho.

### E9b-5 — a ordem 6.2/6.3 estava invertida · 2026-08-14

**Achado por teste sintético, antes da coleta.** O §6.2 compara **médias** de
`load_duration` entre condições. Recarga é exatamente o que desestabiliza
média: a distribuição vira bimodal e o IC da razão explode.

Consequência: com recargas presentes, o 6.2 reprovava **antes** do 6.3, com
mensagem enganosa — "`load_duration` difere entre condições" quando o que
havia era recarga em todas elas.

Não se pergunta "o overhead é comum?" com a distribuição de overhead
contaminada. **Nova ordem: 6.1 → 6.3 → 6.2 → 6.4 → 6.5 → 6.6.**

### E9b-6 — `DELTA_EQUIV` de novo, e o erro foi de raciocínio · 2026-08-14

A emenda E9b-1 corrigiu `0.02 → 0.07` mostrando que o IC (largura 0,0937) não
cabia na margem (0,040). **Mas "cabe" não é "passa".**

O IC precisa caber **e estar centrado**, e o centro é aleatório. A potência do
teste de equivalência, medida:

| `DELTA_EQUIV` | potência do controle (analítica) | empírica |
|---|---|---|
| 0,05 | 10,5% | — |
| **0,07** | **66,7%** | **60,7%** |
| 0,09 | 92,9% | — |
| **0,10** | **97,4%** | **95,3%** |

Com `0.07`, **um terço das rodadas limpas declararia `INSTRUMENTO INVÁLIDO`** —
reprovação por sorte, não por artefato. O controle negativo perderia o
sentido: falharia tanto quando há problema quanto quando não há.

**Novo valor: `DELTA_EQUIV = 0.10`.** É o único que satisfaz as duas
fronteiras ao mesmo tempo — potência ≥ 95% **e** dentro do teto de utilidade
(`≤ 1/5` do efeito de ~50%). Ele fica **exatamente na borda**, e isso é o
achado: em n=360 este instrumento mal sustenta um teste de equivalência que
seja válido e potente ao mesmo tempo.

**Alternativa declarada, não escolhida:** `n=720` por condição daria potência
de ~97% com `DELTA_EQUIV = 0.07` — piso de artefato 7% em vez de 10%. Custa
2880 requisições (~6h em vez de ~3h). Fica registrada porque **se o efeito de
memória no E10/E12 vier abaixo de ~20%, é para lá que se vai** — não para
afrouxar a margem.

**Custo desta escolha, dito alto:** piso de artefato 10%; o instrumento
resolve efeitos a partir de ~20%.


### E9b-7 — o modelo é Q8_0, não Q4 · 2026-08-18

**Errata factual.** A emenda E-1 do E9 descreve `llama3.2:1b` como
*"quantização padrão do Ollama, Q4"*. O log do motor mostra outra coisa:

```
print_info: file type = Q8_0
print_info: file size = 1.22 GiB (8.50 BPW)
```

São **8,5 bits por peso**, não 4. O erro é meu, e vem de eu ter oferecido
"1B em 4-bit" como opção sem verificar o que `ollama pull llama3.2:1b`
entrega de fato.

**O critério não muda** — `MODELO_DIGEST` pina os pesos reais
(`baf6a787fdffd633`), e o experimento sempre rodou contra eles. O que estava
errado era a descrição, não o objeto. Fica corrigido aqui em vez de editado
no lugar.

**Importa para interpretação:** Q8_0 tem largura de banda de memória e custo
por token diferentes de Q4. Nenhum número deste experimento transfere para uma
rodada em Q4 sem nova medição.

### E9b-8 — ambiente de execução, registrado antes da coleta · 2026-08-18

Do log do motor, para o resultado não ser lido como mais geral do que é:

| | |
|---|---|
| backend | `ggml-cpu-sandybridge.dll` |
| ISA | SSE3, SSSE3, AVX — **sem AVX2, sem FMA** |
| CPU | 4 núcleos físicos, 8 lógicos, `NumThreads:4` |
| memória livre no início | 2,2 GiB de 7,9 GiB (swap livre 2,5 GiB) |
| contexto | `n_ctx = 4096`, KV cache 128 MiB, buffer de compute 258,5 MiB |
| `OLLAMA_NUM_PARALLEL` | 1 — sem concorrência interna, um confundidor a menos |
| `OLLAMA_KEEP_ALIVE` | 5m — rodada contínua não descarrega o modelo |

Ausência de AVX2/FMA é característica dominante: a inferência roda num caminho
de código bem mais lento que o de máquina moderna. Isso **não afeta a validade
interna** (todas as condições rodam no mesmo hardware, e o controle negativo
mede exatamente isso), mas fecha qualquer leitura de que os ms/token medidos
representem um custo típico.

**O aviso `failed to disable thread power throttling (87)` persiste** e não é
corrigível — a chamada não é suportada nesta versão do Windows. O SO pode
variar a frequência das threads durante a rodada. Não há mitigação; há
detecção: é precisamente o tipo de deriva que o §6.1 existe para pegar, e se
ele reprovar, esta é a primeira suspeita.

### E9b-2 — terceira constante Tier A minha a falhar, e isso é o padrão

`LOAD_DURATION_MAX_FRAC = 0.01` (E9), `DELTA_EQUIV = 0.02` e depois
`DELTA_EQUIV = 0.07` (E9b) foram todas escolhidas sem medir a consequência, e
todas estavam erradas — por ~6×, por ~2,3×, e por potência (67% onde precisava
de 95%).

A terceira é a mais instrutiva porque **eu já estava corrigindo a segunda**:
computei a largura do IC, comparei com a margem, declarei viável. O que faltou
não foi medir — foi perceber que **caber não é passar**, porque o centro do IC
é aleatório. Erro de raciocínio dentro de um passo de rigor.

Fica registrado como achado sobre o **método**, não sobre o Ollama: num
experimento cuja razão de existir é parar de usar constante não-calibrada, eu
introduzi duas. A diferença é que agora existe maquinaria que as pega antes do
dado — a cascata de sanidade pegou a primeira, a trava de cobertura pegou a
segunda.

**Regra que passa a valer para os próximos pré-registros:** toda constante que
entra num **critério de decisão** precisa de uma das duas coisas antes de
congelar — medição, ou demonstração de viabilidade. Plausibilidade não basta,
e este experimento é a evidência.

---

## §12. Honestidade de escopo

Além de tudo o que o §12 do E9 já proíbe (joule, arquitetura de memória, outro
hardware, qualidade de resposta), o E9b acrescenta:

- **Um H2 confirmado não prova que a carga é a única causa** — prova que a
  resposta é monotônica em três pontos, o que é compatível com causa de carga
  e incompatível com uma troca de regime brusca. Não fecha todos os
  confundidores possíveis; fecha a classe que produz descontinuidade.
- **A margem de 2% é escolha declarada**, não descoberta. Outro pesquisador
  com outro requisito escolheria outra, e o resultado do controle mudaria
  junto.
