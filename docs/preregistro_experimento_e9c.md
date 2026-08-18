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
