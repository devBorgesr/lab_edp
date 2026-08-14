# Pré-registro — Experimento E9
## O instrumento consegue resolver uma diferença conhecida de carga computacional nesta topologia?

**Bancada de Contexto — EDP.** Categoria **VALIDAÇÃO DE INSTRUMENTO**. O E9
**não testa a arquitetura de memória**. Ele responde se existe régua capaz de
dizer "sim" ou "não" sobre custo de inferência neste hardware — antes de
alguém gastar meses construindo a arquitetura que a régua deveria avaliar.

> **Régua da Bancada (método):** este documento declara hipótese, condições,
> métricas, dataset e critério de decisão **ANTES de qualquer dado**. A
> encarnação (`exp_e9.py`) espelha este `.md` e é **CONGELADA após o 1º
> disparo real**. Anti-mock: motor de inferência REAL, não simulado.
> Produção do EDP intocada — o E9 não chama `retrieve()` nem escreve em
> `data/sessions/`.

**Data de pré-registro: 2026-08-14**, antes de qualquer amostra existir.
Terceiro pré-registro nativo do `lab_edp`, depois do E7 e da Fase 2 de tokens.

---

## §1. A pergunta, em uma linha

Uma diferença de carga que eu **sei** ser de ~2× aparece separada nos números
que o motor reporta, nesta topologia (VM ↔ host), com repetições suficientes
para os intervalos de confiança não se tocarem?

Se não aparecer, nenhuma diferença mais sutil vai aparecer — e o programa
energético inteiro está morto neste hardware, o que é achado publicável e
custa uma tarde em vez de meses.

---

## §2. Régua e gatilho de congelamento

Congela no primeiro disparo real (`EDP_LAB_ARMED=1` sem `--dry-run`).
Mudou a régua → é o E10, não o E9. Duas exceções declaradas **agora**, não
depois: modelo e topologia (§7-bis), que só podem ser fixados após a decisão
de infraestrutura do pesquisador, e que entram por **emenda E-1 pré-dado**.

---

## §3. Contexto provado (Passo 0 — verificado em 2026-08-14, não herdado)

### 3.1 Energia em joule NÃO é medível nesta máquina

```
$ systemd-detect-virt      → oracle          (VirtualBox guest)
$ nproc / free -g          → 6 vCPU / 4 GB   (host: 8 GB, CPU-only)
$ ls /sys/class/powercap/intel-rapl*  → ausente
```

O contador RAPL não é exposto ao guest. E no host Windows não há leitura de
joule **por processo** disponível sem driver dedicado. Portanto:

> **DECLARADO ANTES DO DADO (NORTE §4.3):** este experimento **não mede
> energia**. Mede **tempo de computação e contagem de tokens reportados pelo
> próprio motor**. Nenhum resultado do E9 autoriza conclusão em joule ou watt.

Tempo de computação é *proxy* de energia sob frequência e utilização
aproximadamente constantes. É proxy declarado, não medida — e o §12 registra
o que isso proíbe concluir.

### 3.2 O motor está fora do alcance da VM hoje

```
curl http://127.0.0.1:11434/api/tags    → sem resposta
curl http://10.0.2.2:11434/api/tags     → sem resposta
curl http://192.168.56.1:11434/api/tags → sem resposta
```

Ollama roda no host Windows e liga em `127.0.0.1` por padrão. Resolver isso é
pré-condição de armar, e a escolha entre as duas topologias do §7-bis muda o
que é confundidor.

### 3.3 O que o motor entrega, e por que é bom instrumento

A API do Ollama devolve por requisição, em nanossegundos e contagens:

| campo | o que é |
|---|---|
| `prompt_eval_count` | tokens de ENTRADA processados |
| `prompt_eval_duration` | tempo para processar a entrada |
| `eval_count` | tokens GERADOS |
| `eval_duration` | tempo para gerar |
| `load_duration` | tempo de carga do modelo |
| `total_duration` | total |

Isso é medido **dentro do processo que faz o trabalho**. É melhor que
cronômetro de parede vindo da VM: a latência de rede e o escalonamento do
guest entram no relógio de parede e **não** entram nesses campos.

`prompt_eval_duration` é a métrica primária porque é exatamente onde memória
injetada custa — mais contexto no prompt é mais trabalho de entrada.

### 3.4 O IC de bootstrap sub-cobre em n pequeno — já medido neste lab

`bancada/cobertura.py` (`df5e055`) mediu a cobertura real do bootstrap
percentil sobre estimador de razão: **0,846–0,879 contra 0,90 nominal**,
déficits agrupados de 4,30 SE (homocedástico) e 5,35 SE (overhead fixo).

Consequência para o E9, decidida antes do dado: o `n` não é escolhido por
conveniência. Roda-se `bancada/cobertura.py` no `n` proposto **antes de
armar**, e se a cobertura medida ficar abaixo de `COBERTURA_MINIMA` (§11), o
`n` sobe até passar. IC cuja cobertura não foi verificada não é usado como
critério.

---

## §4. Hipóteses (declaradas antes do dado)

- **H1 — o instrumento resolve.** Com o controle negativo válido (§6.1), o IC
  95% de `prompt_eval_duration / prompt_eval_count` da condição `dobro` fica
  **inteiramente acima** do IC da condição `base_A`.

- **H0 — o instrumento não resolve.** Os ICs de `dobro` e `base_A` se tocam.
  O ruído desta topologia engole uma diferença de carga de 2×.

  **H0 vencer é achado válido e encerra o programa energético neste
  hardware** — não adia. Diferença arquitetural real (memória vs. sem
  memória) será menor que 2×; se 2× não separa, nada separa. Publicar isso
  economiza a construção inteira.

---

## §5. Condições (rótulos únicos, mesmo motor, mesma sessão de medição)

| rótulo | o que é | papel |
|---|---|---|
| `base_A` | prompt canônico do dataset §8, sem preenchimento | referência |
| `base_B` | **byte-idêntico a `base_A`**, rótulo diferente | **CONTROLE NEGATIVO** |
| `dobro` | mesmo prompt + preenchimento neutro até `prompt_eval_count` ≈ 2× | diferença conhecida |

### Por que `base_B` é o controle certo

Duas condições **idênticas** têm de medir igual. Se `base_A` e `base_B`
separarem, a separação veio de deriva térmica, contenção de CPU entre VM e
host, recarga de modelo ou ordem de execução — e **não** de carga. Nesse caso
qualquer separação em `dobro` é indistinguível de artefato, e nada é
afirmado. É a mesma estrutura do `tratamento_control_shuffle` do exp008:
validade antes de efeito.

### Por que NÃO existe condição `memoria` aqui

Tentador e errado. O E9 mede a régua; incluir a condição de tratamento
convida a ler o resultado dela como achado sobre a arquitetura, que é
exatamente o que o §4.12 do NORTE proíbe. A condição com memória real é o
**E10**, e só existe se o E9 passar.

### Preenchimento neutro — congelado

Texto em português, sem acentuação incomum, sem código, sem repetição de
n-grama que possa acionar cache de prefixo do motor. Gerado por regra
determinística a partir da `SEED` (§11) e **impresso na prova-no-espelho**
para revisão humana antes de armar.

---

## §6. Critério de decisão (travado, sem reabertura pós-dado)

Avaliado nesta ordem. Parar no primeiro que falhar.

1. **VALIDADE — controle negativo.** `base_A` vs `base_B`: os ICs 95% da
   métrica primária **têm de se sobrepor**. Se separarem → **INSTRUMENTO
   INVÁLIDO**, nenhum achado é afirmado sobre `dobro`, e o relatório reporta
   a magnitude do artefato.

2. **SANIDADE — carga de fato dobrou.** `prompt_eval_count` mediano de
   `dobro` ∈ `[1,8×, 2,2×]` o de `base_A`. Fora disso, o preenchimento não
   fez o que devia e o teste não é sobre o que se pensa.

3. **SANIDADE — modelo não recarregou.** `load_duration` mediano < 1% do
   `total_duration` em todas as condições, após o descarte de aquecimento
   (§8). Se falhar, as medições estão contaminadas por carga de disco.

4. **CONFIRMATÓRIO — H1** sse 1, 2 e 3 passam **e** o IC 95% de `dobro` fica
   inteiramente acima do de `base_A`.

5. Caso contrário → **H0 não rejeitada**: a régua não resolve 2× nesta
   topologia. Dado válido, instrumento insuficiente.

**Descritivo, explicitamente NÃO critério:** a razão medida
`dobro / base_A`. Espera-se ~2, mas o teste é de *separação*, não de
magnitude — e usar a magnitude como critério depois de ver o número seria
escolher a régua com o dado na mão.

---

## §7. Predição pré-dado do arquiteto (registrada para poder ser refutada)

Escrevo antes de qualquer medição, ciente de que fica no git:

- **Controle negativo passa** (ICs sobrepostos) — confiança moderada. O risco
  real é contenção VM↔host, e é por isso que a topologia B do §7-bis é a
  recomendada.
- **H1 confirmada** — confiança alta. 2× de trabalho de prompt é uma
  diferença grosseira e `prompt_eval_duration` é reportado pelo motor, não
  pelo relógio da VM.
- **A razão medida virá ABAIXO de 2** (algo entre 1,5× e 1,9×), por custo
  fixo por requisição que não escala com o prompt. Se vier ≥ 2,0 minha
  predição está errada e isso fica registrado.

---

## §7-bis. Topologia — congela por emenda E-1, antes do 1º disparo

| | **A — harness na VM** | **B — harness no Windows** |
|---|---|---|
| exige | `OLLAMA_HOST=0.0.0.0` no Windows + regra de firewall | Python no Windows |
| confundidor | **contenção de CPU**: VM e Ollama disputam o mesmo silício | nenhum atravessa fronteira |
| instrumento extra | — | `psutil` lê o tempo de CPU do processo `ollama` — **segunda régua independente** |
| repositório | nativo | mesma pasta compartilhada, visível do Windows |

**Recomendo B.** Não por conveniência: por ela dar uma segunda medida
independente da primeira. Se o tempo de CPU do processo e o
`prompt_eval_duration` do motor discordarem, isso é sinal de artefato que a
topologia A não consegue nem enxergar.

Escolhida a topologia, ela entra aqui como emenda E-1 datada, antes do
primeiro disparo. Se for A, o §11 ganha a linha `CONTENCAO_DECLARADA=True` e
o relatório é obrigado a citá-la como limite.

---

## §8. Dataset CONGELADO

- **`K_PROMPTS = 12`** perguntas fixas, escritas neste documento no momento da
  emenda E-1, em português, sem código — o corpus real do EDP é PT-BR com
  acentuação e é isso que se quer exercitar.
- Cada prompt roda **`N_REPETICOES`** vezes por condição.
- **Ordem de execução intercalada e embaralhada** com `SEED` congelada, de
  modo que deriva térmica e escalonamento **não** se alinhem com condição.
  Rodar todas as `base_A`, depois todas as `dobro`, confunde tempo com
  aquecimento — e é o erro que o controle negativo pegaria tarde demais.
- **Descarte de aquecimento:** as primeiras `N_AQUECIMENTO` requisições da
  sessão inteira são jogadas fora antes de qualquer estatística, para o
  `load_duration` do primeiro carregamento não entrar.
- `temperature = 0`, `seed` fixa, `num_predict` fixo — a geração precisa ser
  do mesmo tamanho em todas as condições, senão `eval_duration` varia por
  motivo que não é o testado.

---

## §9. Métricas (fórmula + agregação)

**Primária:**
```
custo_entrada = prompt_eval_duration / prompt_eval_count     [ns por token de entrada]
```
Normalizada por token de propósito: compara custo *unitário*, não custo total,
que trivialmente dobra quando o prompt dobra.

**Secundárias (reportadas, não critério):**
```
custo_saida  = eval_duration / eval_count
total_duration, load_duration
```

**Agregação:** mediana por condição, com **IC bootstrap percentil 95%**,
`B = N_BOOTSTRAP` reamostragens, `SEED` congelada. Mediana e não média porque
tempo de execução tem cauda direita pesada (uma preempção do SO cria outlier
que a média absorve e a mediana ignora).

**Verificação de cobertura antes de confiar no IC:** ver §3.4. Roda-se
`bancada/cobertura.py` no `n` proposto; cobertura medida `< COBERTURA_MINIMA`
⇒ sobe o `n` e repete, **antes** de armar.

---

## §10. Anti-mock e isolamento

- **Motor REAL.** Ollama de verdade, modelo de verdade. Nada simulado, nenhum
  tempo sintetizado.
- **Produção do EDP intocada.** O E9 não importa `edp.memory`, não chama
  `retrieve()` (que muta `acessos`/`ultimo_acesso` e persiste), não lê nem
  escreve `data/sessions/`. Os prompts são do §8, não do store.
- **Harness ocioso durante a inferência.** Nenhum trabalho concorrente entre
  enviar a requisição e receber a resposta — o próprio medidor não pode ser
  fonte de contenção.
- **Registro bruto.** Toda resposta do motor é gravada com os seis campos
  crus, não só o agregado. O número não é o achado; o achado é reproduzível a
  partir do bruto.

---

## §11. Constantes congeladas (espelhadas em `exp_e9.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"E9"` |
| `K_PROMPTS` | `12` |
| `N_REPETICOES` | `30` |
| `N_AQUECIMENTO` | `5` |
| `FATOR_CARGA` | `2` |
| `TOLERANCIA_CARGA` | `[1.8, 2.2]` |
| `TEMPERATURA` | `0` |
| `NUM_PREDICT` | `64` |
| `SEED` | `20260814` |
| `N_BOOTSTRAP` | `10000` |
| `NIVEL_IC` | `0.95` |
| `COBERTURA_MINIMA` | `0.90` |
| `LOAD_DURATION_MAX_FRAC` | `0.01` |
| condições | `base_A`, `base_B`, `dobro` |
| `MODELO` | **emenda E-1** |
| `TOPOLOGIA` | **emenda E-1** |

**CONGELADO ao primeiro disparo real. Mudou a régua → é o E10, não o E9.**

O gate `tests/test_preregistro_espelha_encarnacao.py` do `edp_v5` compara
tabela ↔ módulo e quebra o build se divergirem sem desvio declarado em
`§N-bis`. Este experimento nasce sob esse gate — o desvio silencioso de
`POOL_SIZE` no exp008 (50 congelado, 100 rodando, dois meses sem nota) é o
precedente que ele existe para não repetir.

---

## §12. Honestidade de escopo — o que o E9 NÃO autoriza concluir

- **Nada sobre joule ou watt.** Ver §3.1. Tempo de computação é proxy
  declarado. Um resultado positivo aqui significa "a régua resolve 2× de
  trabalho", não "medimos energia".
- **Nada sobre a arquitetura de memória.** Não existe condição com memória
  (§5). Passar no E9 habilita o E10; não diz nada sobre ele.
- **Nada sobre outro hardware.** O resultado vale para esta máquina, esta
  topologia, este modelo. Um H0 aqui não diz que a tese energética é falsa —
  diz que **este** instrumento não a avalia.
- **Nada sobre a qualidade da resposta.** O E9 não lê o que o modelo escreveu.
  `temperature=0` e `num_predict` fixo existem para tirar a geração da
  equação, não para avaliá-la.
