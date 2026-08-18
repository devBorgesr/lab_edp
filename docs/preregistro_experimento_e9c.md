# Pré-registro — Experimento E9c
## A diferença de custo entre cargas conhecidas é causada pela carga? (terceira tentativa, rodada enxuta)

**Bancada de Contexto — EDP.** Categoria **VALIDAÇÃO DE INSTRUMENTO**.

O E9c **herda integralmente** o desenho do E9b — hipóteses, condições,
estimador, cascata de critério, dataset, margens. Este documento registra
apenas **o que muda e por quê**. Para tudo o mais, a autoridade é
`preregistro_experimento_e9b.md`, incluindo suas emendas E9b-1 a E9b-8.

**Data de pré-registro: 2026-08-18**, antes da primeira amostra do E9c.

---

## §1. O que muda, e só isso

| constante | E9b | E9c |
|---|---|---|
| `EXPERIMENTO` | `"E9b"` | `"E9c"` |
| `NUM_PREDICT` | `64` | `1` |

**Nenhuma outra.** `tests/test_exp_e9c.py` compara o conjunto de constantes
dos dois módulos e exige que a diferença seja exatamente este par — e compara
a fonte da cascata de pontuação para provar que a cópia não derivou.

---

## §2. Por que

O E9b foi armado em 18/08 com `NUM_PREDICT = 64`. A primeira linha de
progresso mediu **16,9 s/req → 6,6 h**. Decompondo com os números do E9:

```
prompt_eval   ~1,9 s    ← a métrica primária é ISTO
eval         ~15,0 s    ← 88% do tempo, e não entra em critério nenhum
```

O §8 do E9b exige que a geração seja **constante** entre condições, para
`eval_duration` não variar por motivo que não é o testado. Constante pode ser
**1**. Gerar 64 tokens que nenhum critério lê custa 88% da rodada.

**Piso de hardware, medido:** DDR3-1333 em dois canais dá ~15 GB/s efetivos, e
gerar um token exige ler 1,22 GiB de pesos — **~81 ms/token só de banda**.
Observado ~235 ms/token (i7-2670QM Sandy Bridge, sem AVX2/FMA). Nesta máquina
`NUM_PREDICT=1` não é otimização; é o único desenho viável.

---

## §3. Por que isto não é escolher a régua com o dado na mão

`NUM_PREDICT` **não aparece em nenhuma regra de decisão do §6 do E9b**. Não
entra no estimador `Σ prompt_eval_duration / Σ prompt_eval_count`, nem em
6.1, 6.2, 6.3, 6.4, 6.5 ou 6.6. Não pode virar veredito.

Mas é constante da tabela congelada, e o disparo do E9b **já havia começado**.
Por isso isto é E9c, não "E9b corrigido". A regra do §2 do E9b é literal:
*mudou a régua → é o E9c*. Renomear é barato; abrir exceção não é.

**As amostras parciais do E9b são descartadas.** Nenhum número delas é lido,
nem como piloto. O `--score` já recusa arquivo incompleto por padrão.

---

## §4. O viés desta mudança, declarado antes da coleta

Rodada de ~45 min em vez de 6,6 h significa **menos exposição a deriva
térmica e a throttling**. Deriva é a ameaça principal ao controle negativo.

> **Portanto a mudança torna o §6.1 MAIS FÁCIL de passar.** Ela me favorece.

Some-se a isso duas alterações de ambiente feitas na mesma decisão (§5), ambas
na mesma direção. Não há como neutralizar isso; há como declarar e estreitar a
conclusão — ver §12.

---

## §5. Ambiente do E9c, fixado antes da coleta

Diferenças declaradas em relação ao ambiente registrado na emenda E9b-8:

| item | E9b | E9c |
|---|---|---|
| VM VirtualBox (4 GB, 6 vCPU) | **ligada** durante E9/E9b | **desligada** |
| plano de energia | Equilibrado | Alto desempenho, estado máx. do processador 100% |
| `xmrig-6.25.0` | presente no disco, estado não verificado | **verificado parado** pelo pesquisador |

Permanecem inalterados e continuam declarados: i7-2670QM, 4 núcleos / 8
threads, 8 GB DDR3-1333, backend `ggml-cpu-sandybridge`, **sem AVX2, sem
FMA**, `llama3.2:1b` **Q8_0** (1,22 GiB, 8,50 BPW), `n_ctx=4096`,
`OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=5m`.

**A GPU não participa e não pode participar:** GeForce GT 525M é Fermi
(compute capability 2.1), o ramo de driver 391 é o último a suportá-la, e os
backends CUDA modernos exigem `sm_52`+. Além disso são 1024 MB de VRAM contra
um modelo de 1,22 GiB. Dois bloqueios independentes, registrados para ninguém
reabrir a pergunta.

O aviso `failed to disable thread power throttling (87)` **persiste e não é
corrigível** (API não suportada nesta versão do Windows). Sem mitigação, com
detecção: é o que o §6.1 existe para pegar.

---

## §6–§11. Herdados do E9b, sem alteração

Critério (cascata `6.1 → 6.3 → 6.2 → 6.4 → 6.5 → 6.6`), estimador de razão com
IC bootstrap conjunto, condições, dataset, prompts, `SEED`, margens e
tolerâncias: **idênticos**. Ver `preregistro_experimento_e9b.md`.

### §11. Constantes congeladas (espelhadas em `exp_e9c.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"E9c"` |
| `K_PROMPTS` | `12` |
| `N_REPETICOES` | `30` |
| `N_AQUECIMENTO` | `5` |
| `TOLERANCIA_CARGA` | `(1.8, 2.2)` |
| `TOLERANCIA_MEIO` | `(1.35, 1.65)` |
| `DELTA_EQUIV` | `0.10` |
| `TEMPERATURA` | `0` |
| `NUM_PREDICT` | `1` |
| `SEED` | `20260814` |
| `N_BOOTSTRAP` | `10000` |
| `NIVEL_IC` | `0.95` |
| `COBERTURA_MINIMA` | `0.90` |
| `FATOR_OUTLIER` | `5.0` |
| `MAX_DESCARTE_FRAC` | `0.05` |
| `MODELO` | `"llama3.2:1b"` |
| `TOPOLOGIA` | `"windows_local"` |

**CONGELADO ao primeiro disparo real. Mudou a régua → é o E9d.**

---

## §7. Predição pré-dado do arquiteto

Registradas antes de qualquer amostra do E9c, para poderem ser refutadas.

- **6.1 passa** — confiança alta, e agora **mais alta que no E9b**, pelo §4.
  Se falhar mesmo com máquina aquietada e rodada curta, o problema não é
  deriva ambiental e a suspeita muda de lugar.
- **6.3 passa** (zero recargas) — `KEEP_ALIVE=5m` e rodada contínua.
- **6.2 passa** — confiança média. Cheque novo, nunca medido.
- **H1 confirmada** — confiança alta.
- **H2 confirmada** — confiança média-baixa, igual ao E9b.

**A predição que vale mais, porque testa o próprio raciocínio desta emenda:**

> O **absoluto** deve cair em relação ao E9 (55,2 ms/token), porque a máquina
> está aquietada e sem 15 s de carga sustentada por requisição aquecendo o
> CPU. Mas a **razão `R(dobro)` deve se preservar em ~1,45–1,60×**, porque a
> mudança é multiplicativa e comum às condições.
>
> Se o absoluto cair **e** a razão se mover muito, minha premissa de que
> `NUM_PREDICT` é neutro para a métrica está errada — e aí o E9c refuta a
> própria justificativa que o criou.

---

## §12. Honestidade de escopo — o que o E9c NÃO autoriza

Além de tudo que os §12 do E9 e do E9b já proíbem (joule, arquitetura de
memória, outro hardware, qualidade de resposta, transferência para Q4):

- **A alegação é mais estreita que a do E9b.** Um `H1 CONFIRMADA` aqui
  significa *"o instrumento resolve 2× numa rodada de ~45 min, em máquina
  aquietada, com plano de energia em desempenho máximo"*. **Não** significa
  que resolve sob rodada longa ou máquina em uso — condições que o E9b teria
  testado e que esta versão evita de propósito (§4).
- **Nada sobre `eval` (geração).** Com `NUM_PREDICT=1` a métrica secundária
  `custo_saida` passa a ser medida sobre um único token e **não deve ser
  reportada** como característica de geração.

---

## §13. Resultado do disparo real — 2026-08-18

`EDP_LAB_ARMED=1`, 1440 amostras, 360 por condição, 4,5 s/req (~1,8 h).
`llama3.2:1b` Q8_0, digest `baf6a787fdffd633`, régua secundária `psutil` ativa.

| condição | n | custo unitário | `R` = custo / custo(`base_A`) |
|---|---|---|---|
| `base_A` | 360 | 49,146 ms/token | referência |
| `base_B` | 360 | 49,213 ms/token | [0,9608 · 1,0450] |
| `meio`   | 360 | 63,703 ms/token | [1,2455 · 1,3487] |
| `dobro`  | 360 | 72,497 ms/token | [1,4226 · 1,5321] |

### A cascata inteira, na ordem congelada

| # | cheque | medido |
|---|---|---|
| 6.1 | controle negativo (equivalência) | IC [0,9608 · 1,0450] ⊂ [0,90 · 1,10] **ok** |
| 6.3 | recarga por forma | **0/1440** acima de 5,0× a mediana **ok** |
| 6.2 | `load_duration` comum | IC [0,9999 · **1,0037**] **ok** |
| 6.4 | carga `meio` / `dobro` | 1,51× / 1,99× **ok** |
| 6.4b | descarte de outlier | 0,0% nas quatro **ok** |
| 6.5 | **H1** | IC(R dobro) exclui 1,0 **CONFIRMADA** |
| 6.6 | **H2** dose-resposta | 1,3487 < 1,4226 **CONFIRMADA** |

> **VEREDITO: `H1 E H2 CONFIRMADAS`.**

### O que passou merece leitura separada

**O controle negativo passou com resolução, não por largura.** IC de amplitude
0,084 contra margem de 0,20 — sobra de 2,4×. Duas condições byte-idênticas
medindo a 0,14% uma da outra. Era a peça que a emenda E9b-6 quase tornou
impossível, e é a que sustenta tudo o mais.

**O `load_duration` é comum a 0,4%.** IC [0,9999 · 1,0037] é praticamente a
identidade. Confirma, com o cheque certo, o que o E9 diagnosticou com o cheque
errado: overhead fixo por requisição, idêntico entre condições, fora do
estimador. O §6.3 do E9 media a grandeza errada.

**A dose-resposta é suave, não um salto.** Cargas 1,00 → 1,51 → 1,99 dão
custos 1,000 → ~1,29 → 1,475, com ICs disjuntos e monotônicos. Era exatamente
a pergunta do §3.3 do E9b, que o E9 não podia responder com dois pontos.

### Predições do §7 — pontuadas

Todas as sete se sustentaram, incluindo o par que existia para refutar a
justificativa do E9c: **o absoluto caiu** (55,197 → 49,146 ms/token, −11%, com
a máquina aquietada) **e a razão se preservou** (1,502 → 1,475, deslocamento de
1,8%, muito dentro da amplitude do IC). `NUM_PREDICT` é neutro para a métrica,
como o §3 afirmou antes de medir.

Duas notas contra mim:

- **Confiança calibrada errado em H2.** Declarei "média-baixa" e ela separou
  com folga de 0,074. Subestimei.
- **Estimativa de tempo errada de novo.** Previ ~45 min; foram ~1,8 h. Calculei
  o `prompt_eval` só da `base` em vez da média entre condições, onde `dobro`
  custa 3× a base. Erro na direção inofensiva, mas é o terceiro palpite de
  tempo meu que não bate.

### Interpretação mecanística — pós-dado, explicitamente NÃO critério

Custo **por token** subindo com o comprimento é a assinatura do termo
quadrático da atenção. Se o custo fosse linear em tokens (dominado por FFN), o
custo unitário seria constante e `R` daria 1,0. Um modelo `T(N) = αN + βN²`
com `βN_base ≈ 0,9α` prevê `R(meio) ≈ 1,24` e `R(dobro) ≈ 1,47` — próximo do
observado (1,29 e 1,475).

Isto é coerência, não evidência: o desenho não foi feito para estimar α e β, e
nenhum critério depende deste ajuste.

### O que este resultado NÃO autoriza

Vale o §12 inteiro, sem atenuação. Em especial:

- **A alegação é a estreita.** *"O instrumento resolve 2× numa rodada de ~1,8 h
  em máquina aquietada, com VM desligada e plano de energia em desempenho
  máximo."* Não sob rodada longa nem máquina em uso — condições que o E9b teria
  testado e que esta versão evitou de propósito (§4).
- **Piso de artefato 10%.** Com `DELTA_EQUIV = 0.10`, o instrumento sustenta
  efeitos a partir de ~20%. Se o efeito de memória do E10/E12 vier abaixo
  disso, o caminho é `n = 720` (potência 97,2% com margem 0,07, medido na
  emenda E9b-6) — **não** afrouxar a margem.
- **Nada sobre geração.** Com `NUM_PREDICT = 1`, `custo_saida` é medido sobre
  um único token e não deve ser reportado.
- **Nada sobre memória.** Não existe condição com memória, de propósito.
