# Plano congelado — Experimento E8
## O retrieval do EDP supera uma baseline externa de compilar-depois-recuperar, e supera o controle burro?

> **Isto NÃO é um pré-registro.** No vocabulário deste laboratório
> (`docs/TEMPLATE_PREREGISTRO.md`), pré-registro significa régua congelada
> com predições falsificáveis e cortes numéricos fixados antes do dado.
> Os cortes de E8 (N por categoria, X e Y do critério de decisão)
> **dependem de medições de uma Fase 0 que não foi feita** — censo do
> corpus, custo por braço, confirmação do caminho de retrieval vivo do
> EDP. Chamar este documento de pré-registro diluiria o termo nos outros
> cinco que o usam de verdade (008, 009, 010, PRE_REGISTRO_EXP017, E7).
> **Rodar E8 exige um pré-registro próprio, escrito depois da Fase 0, com
> os números preenchidos** — este documento não autoriza disparo.

**Status: PLANEJADO — NÃO EXECUTADO.** Bloqueado por `NORTE.md` até
**02/09/2026** (ou antes, se a meta comercial descrita lá for atingida
primeiro). Ver §6.

---

## §1. Motivação (verificada, não assumida)

`docs/ACERVO_EXPERIMENTOS.md` cataloga todo o acervo de experimentos deste
laboratório e do `edp_v5` herdado: 008, 009, 010, 011, 012, 016, 017 e E7
— **todos comparam o EDP contra o próprio EDP** (híbrido vs. cosine puro,
dedup on/off, shuffle como controle, privilégios de nascença on/off,
sequência real vs. embaralhada). Nenhum testa a hipótese de que uma
arquitetura inteiramente diferente — ou nenhuma sofisticação — serve
melhor ao mesmo corpus. Esta é a lacuna que E8 endereça: uma baseline
**externa** ao EDP, não mais uma variação interna dele.

## §2. Baseline externa: padrão LLM Wiki (Karpathy, abril/2026)

Em vez de recuperar de documentos brutos a cada query, um agente constrói
e mantém incrementalmente uma wiki de markdown interligada (páginas de
entidade, de conceito, resumos de fonte, contradições, referências
cruzadas), em três camadas: fontes brutas imutáveis, `wiki/` mantida pelo
LLM, e um arquivo de schema — mais `index.md` (catálogo) e `log.md`
(histórico de operações). A recuperação é feita lendo índice e seguindo
links.

**Registro explícito: o padrão NÃO é "zero embedding".** O setup de
referência (`tobi/qmd`) recomenda uma camada de busca BM25/vetorial sobre
o próprio markdown. A diferença real entre este padrão e o EDP não é a
mecânica de busca — é **quando a síntese acontece**. RAG (e o EDP)
sintetiza a cada query e joga fora; a wiki sintetiza uma vez, no ingest,
num artefato durável. É essa variável temporal que E8 mede, não
"embedding vs. sem embedding".

## §3. Quatro braços (mesmo corpus, mesmos bytes, mesmo modelo gerador)

Se o modelo que gera a resposta final variar entre braços, o experimento
mede modelo, não arquitetura — por isso os quatro usam o mesmo modelo,
só a recuperação difere.

| braço | papel | descrição |
|---|---|---|
| 0 — zero-contexto | controle de validade das perguntas | mesmo modelo, mesma pergunta, nenhuma memória injetada. Se acerta por conhecimento paramétrico, a pergunta não mede memória e sai do conjunto. |
| 1 — contexto longo ingênuo | controle negativo forte | todo o texto do corpus (ou o máximo que couber, regra de corte a definir) despejado no contexto, sem retrieval. O "sistema mais burro possível". |
| 2 — EDP | tratamento A | SHA congelado (a definir — ver achado sobre ausência de instância implantada, `docs/ACHADO_PREMISSAS_RETRIEVAL.md`), config default, nenhuma modificação durante a medição. |
| 3 — wiki Karpathy | tratamento B | wiki construída a partir do mesmo corpus por agente, três camadas + `index.md` + `log.md`, recuperação via índice/links + camada de busca do §2. |

## §4. Três categorias de pergunta, com predição por categoria

| categoria | definição | predição |
|---|---|---|
| A — fato único | resposta vive em exatamente 1 entrada | EDP deve ir bem — é para isso que recuperação por score serve. |
| B — síntese multi-hop | resposta exige ≥3 entradas de sessões diferentes | wiki deve ir bem — é a limitação que o próprio padrão Karpathy nomeia explicitamente (RAG fragmenta, wiki compila). |
| C — contradição/obsolescência | corpus contém fato superado por outro posterior; resposta correta usa o mais recente ou sinaliza a contradição | a classificação epistêmica do EDP deve ir bem — é capacidade que ele tem e que a wiki depende do agente notar na hora, sem garantia estrutural. |

N por categoria: **A DEFINIR — exige Fase 0** (censo do corpus, 0.2;
sugestão do prompt original era A=15, B=15, C=10, mas depende de quantos
tópicos com ≥3 entradas cruzando sessões o corpus real de fato tem).

## §5. Julgamento (método a congelar antes de existir resposta)

- Cego e randomizado: juiz não sabe qual braço produziu qual resposta,
  ordem de apresentação embaralhada por pergunta.
- Rubrica fixa (a escrever no pré-registro real): correto / parcialmente
  correto / incorreto / alucinado, com definição operacional de cada
  nível — alucinação = afirmação específica ausente do corpus.
- Juiz-LLM com a rubrica + conferência humana cega de um subconjunto
  (tamanho a definir), concordância entre os dois medida e reportada — se
  baixa, o resultado do juiz-LLM não vale.
- **Métrica co-primária de recuperação:** recall dos `entry_ids_suporte`
  — separa "recuperou o material certo" de "escreveu uma resposta boa",
  dois modos de falha diferentes. Para o EDP: quais entradas entraram no
  contexto. Para a wiki: quais páginas o agente leu e quais fontes elas
  citam. Para o Braço 1: trivial (tudo).
- Custo e latência por pergunta, por braço, medidos.
- Consistência entre sessões: subconjunto rodado 3× em sessões novas,
  medindo variância da resposta (EDP tem determinismo declarado como
  força; a wiki depende de julgamento do agente — esta métrica mede
  exatamente essa troca).

## §6. Estrutura do critério de decisão — **N, X, Y: A DEFINIR, exige Fase 0**

Números inventados agora viram âncora — por isso os cortes abaixo ficam
como estrutura, não como valor:

| resultado | ação |
|---|---|
| Braço 1 (ingênuo) ≥ Braços 2 e 3 em A, B e C | ambas as arquiteturas são injustificadas neste tamanho de corpus. Parar de investir em retrieval sofisticado; registrar a refutação com esse nome. |
| Braço 3 (wiki) > Braço 2 (EDP) em B por ≥ **Y (a definir)** pp, sem que o EDP ganhe A ou C por ≥ **X (a definir)** pp | a tese compilar-depois-recuperar vence. Parar de endurecer o pipeline de scoring; planejar migração. |
| EDP vence A e C, perde B | híbrido justificado; a peça que falta (camada de síntese durável) fica identificada, não adivinhada. |
| EDP vence tudo | a aposta central validada contra baseline externa pela primeira vez. Registrar; hardening do pipeline deixa de ser fé. |

X, Y e o poder do teste (que diferença mínima o N escolhido consegue
detectar) só podem ser fixados depois do censo do corpus (0.2) e da
estimativa de custo (0.5) — ambos fora de escopo desta rodada.

## §7. Motivo do congelamento — `NORTE.md`, citado literalmente

`NORTE.md` (em `edp_v5`, válido até **02/09/2026**) trava o foco numa
meta única e falsificável: R$3.000/mês recorrentes de um serviço de
auditoria de retrieval, via abordagem direta a PMEs. Trechos citados sem
paráfrase:

> "TESTE DE ESCOPO (para o agente E para nós, antes de todo prompt)
> Pergunta única: 'isto aproxima o primeiro/próximo cliente pagante
> dentro do prazo?' SIM demonstrável → executa. NÃO ou
> 'indiretamente/um dia' → recusar e apontar este arquivo."

> "Fila técnica do EDP: pool_k/return_k, piso semântico, write-dedup,
> eco do summary, reescala RRF, **benchmark**" — listado em **FORA DE
> ESCOPO ATÉ A META**.

> "O EDP provou o método (lab 9/10, 18 refutações). **Provas adicionais
> têm valor marginal ~zero sem leitor.** A única variável em zero é
> comercial."

Um bake-off de 4 braços com pré-registro, juiz cego e N de dezenas de
perguntas é, por forma e por tamanho, exatamente a categoria de "prova
adicional" que `NORTE.md` pede para não fazer agora. O desenho não se
perde — fica congelado aqui, pronto para virar pré-registro real assim
que a meta comercial for atingida ou o prazo vencer e o documento for
reavaliado.

**Data de revisão: 02/09/2026, ou antes se a meta comercial do NORTE.md
for atingida primeiro.**

## §8. O que falta antes de este plano virar pré-registro (checklist da Fase 0 congelada)

```
[ ] 0.1 — confirmar o caminho de retrieval vivo do EDP (função chamada
    por MemoryStore.retrieve(), FAISS/HNSW vs. força-bruta, BM25/RRF
    vivos ou só no código) — instrumentado, não só lido
[ ] 0.2 — censo do corpus real: tamanho, nº de entradas por camada,
    tokens estimados, nº de tópicos com ≥3 entradas cruzando sessões
[ ] 0.5 — viabilidade e custo: camada de busca sobre a wiki, provider/
    modelo disponível, estimativa de tokens/$ para construir a wiki 1x
    e responder 1 pergunta por braço, multiplicado pelo N real
[ ] 0.6 — SHA do EDP a fixar: resolver a divergência entre main, a
    branch de trabalho e o que está de fato implantado (ver achado em
    docs/ACHADO_PREMISSAS_RETRIEVAL.md — nenhuma instância implantada
    foi localizada neste ambiente)
[ ] conjunto de perguntas (perguntas.json) gerado do corpus real,
    validado, congelado por hash — só depois de 0.2
[ ] N, X, Y preenchidos com justificativa e poder do teste declarado
```

Só depois desta lista preenchida um pré-registro de verdade pode ser
escrito e E8 sair de PLANEJADO para ARMADO.
