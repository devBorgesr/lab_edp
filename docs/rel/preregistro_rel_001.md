# Pré-registro — REL-001
## O rótulo de relevância é confiável o bastante para sustentar Recall@K?

**Congelado em 30/08/2026, ANTES de qualquer rotulação.**

Origem: proposta externa (EXP-REL-001), reescrita para passar na metodologia do
lab. O que foi mantido, o que foi corrigido e por quê está no `§10` — a versão
original **não** é apagada, é auditada (NORTE §4.4).

---

## §1. Motivação (medida, não suposta)

A Auditoria de Qualidade depende de saber, para cada query, quais documentos são
relevantes. Este projeto já perdeu três vezes tentando produzir rótulo assim:

| tentativa | resultado |
|---|---|
| juiz LLM como crítico autônomo (E10) | **H1 refutada** — a tarefa que supus extrativa era abstrativa |
| lista de padrões (`negacao_textual`, produção) | recall **6/22 = 27%** contra negações reais |
| lista de padrões (`FRASES_NEGACAO`, exp019) | recall **0/22**, escrita dois dias após ler o texto |

O risco não é o rótulo ser difícil. É construir Recall@K sobre um rótulo cuja
concordância nunca foi medida, e vender o resultado como precisão objetiva.

## §2. Hipótese (declarada antes do dado)

- **H1:** rotulação binária de relevância, aplicada independentemente por humano
  e por juiz LLM sob o mesmo rubric, concorda o bastante para servir de
  **triagem** de ground truth.
- **H0:** não concorda o bastante. Recall@K construído sobre esse rótulo herda o
  ruído dele.

**H0 vencer é o resultado mais valioso comercialmente:** impede vender Recall@K
como medição confiável antes de o instrumento ter passado. Perder o produto é
caro; vender precisão que não existe é pior.

## §3. Desenho — a estratificação que corrige a prevalência

### §3.1 O problema que a versão original não viu

Cohen's κ colapsa com prevalência assimétrica. **Medido por simulação, antes de
qualquer dado:**

| prevalência de relevantes | acordo bruto necessário para κ = 0,80 |
|---|---|
| 0,05 | **98,9%** |
| 0,10 | **97,9%** |
| 0,15 | **97,1%** |
| 0,50 | **94,8%** |

Candidatos de retrieval em k=10 têm tipicamente 10–20% de relevantes. Nessa
faixa, **dois anotadores que concordam em 93% produzem κ = 0,59** — que a
proposta original classifica como REPROVADO.

O gate rejeitaria um instrumento que acerta 93% das vezes, por um motivo que
**não é do instrumento**. É a mesma falha do `DELTA_EQUIV = 0.02` do E9b:
critério que parece rigoroso e é inalcançável por construção.

### §3.2 A correção, que resolve dois problemas de uma vez

O pool de candidatos de cada query é **estratificado por desenho**:

| estrato | n por query | origem | previsão ANTES do dado |
|---|---|---|---|
| `topo` | 5 | top-5 do retriever | prevalência alta; onde a discordância mora |
| `cauda` | 3 | posições 20–50 do mesmo retriever | prevalência baixa |
| `controle` | 2 | documento aleatório de **outro domínio** | **irrelevante nos dois julgadores, ~100% de acordo** |

O estrato `controle` é o **controle negativo** (NORTE §4.5) que a proposta
original não tinha. A previsão está escrita acima, antes do dado: se os dois
julgadores discordarem sobre documento de outro domínio, o rubric ou a unidade
de julgamento estão quebrados, e **o resto da medição não vale** — declarado
inválido, não ajustado.

E a mistura leva a prevalência para perto de 0,5, onde κ é interpretável.

## §4. Rubric congelado

Pergunta única ao julgador:

> **"Este documento é materialmente útil para responder ESTA query?"**

```
1 = RELEVANTE      contribui materialmente; contém informação necessária
                   ou evidência diretamente utilizável
0 = NÃO_RELEVANTE  pode ser do mesmo assunto, usar palavras parecidas ou ser
                   topicalmente próximo, e ainda assim não contribuir
```

**Similaridade temática não é relevância.** Documento sobre exatamente o mesmo
assunto pode receber `0`.

Proibido: "parcialmente", "talvez", escala contínua, ver o ranking original, ver
a decisão do outro julgador. Documento sem informação suficiente para decidir
recebe `0`.

## §5. Métricas

**Primária:** Cohen's κ entre humano e juiz LLM.

**IC por bootstrap de QUERY, não de par.** Dez pares compartilham a mesma query
e não são independentes; tratá-los como 500 observações independentes estreita o
intervalo indevidamente. Mesmo motivo pelo qual a medição de duplicação de 19/08
usou bootstrap por turno.

**Secundárias, reportadas sempre:** acordo bruto, matriz de confusão,
**prevalência alcançada** (se divergir de ~0,5, o κ precisa ser lido com ela
declarada), Gwet's AC1 como checagem de robustez à prevalência, discordância por
estrato.

## §6. Critério (poder MEDIDO antes da coleta)

Simulação com prevalência balanceada e bootstrap de query:

| desenho | acordo real | κ | IC 95% | decide? |
|---|---|---|---|---|
| 50q × 10d = **500 pares** | 95% | 0,85 | [0,80 ; 0,90] | sim |
| 50q × 10d = 500 pares | 93% | 0,68 | [0,61 ; 0,75] | sim |
| 50q × 10d = 500 pares | 90% | 0,61 | [0,54 ; 0,68] | sim |
| 30q × 10d = 300 pares | 95% | 0,85 | [0,77 ; 0,91] | **não** |

**`N_QUERIES = 50`, `N_DOCS = 10`.** Escolhido pelo poder acima: 300 pares não
separam 0,80 do resto.

### Veredito — sobre o INTERVALO, não sobre o ponto

| resultado | conclusão permitida |
|---|---|
| IC inteiramente **acima de 0,80** | aprovado para triagem |
| IC inteiramente **abaixo de 0,60** | reprovado — Recall@K não se constrói sobre isto |
| IC **atravessa** um dos cortes | **inconclusivo com este N**, e nada mais |

*Caber não é passar.* Um κ pontual de 0,82 com IC [0,74 ; 0,89] **não** aprova —
foi assim que o `DELTA_EQUIV = 0.07` do E9b morreu, dentro de um passo cujo
propósito era rigor.

### §6.1 Declarado, não escondido (NORTE §4.3)

Com N=500 este desenho **não distingue** κ = 0,78 de κ = 0,82. A largura típica
do IC é de ~0,10, então diferenças menores que isso ficam invisíveis. Um
inconclusivo nessa faixa significa *"não separável com este N"*, não *"os dois
são iguais"*.

## §7. Independência e isolamento

Os dois caminhos rotulam **sem acesso um ao outro**, e a análise só começa com os
dois conjuntos congelados. Proibido: LLM primeiro e humano "corrigindo", ou o
inverso.

Configuração do juiz congelada antes da coleta: modelo, versão, system prompt,
temperatura, formato de saída, rubric. **Nenhuma tentativa sucessiva para
melhorar concordância depois de ver resultado** — isso é escolher o instrumento
pelo que ele produz, e é o que invalidou a lista do exp019.

Ordem dos pares embaralhada com seed congelado, igual para os dois julgadores.

## §8. Constantes congeladas (espelhadas em `rel_001.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"REL-001"` |
| `N_QUERIES` | `50` |
| `N_DOCS_POR_QUERY` | `10` |
| `N_TOPO` / `N_CAUDA` / `N_CONTROLE` | `5` / `3` / `2` |
| `GATE_APROVA` | `0.80` |
| `GATE_REPROVA` | `0.60` |
| `ALPHA` | `0.05` |
| `N_BOOTSTRAP` | `20000` |
| `SEED` | `20260830` |
| `ACORDO_ESPERADO_CONTROLE` | `0.98` |

**CONGELADO ao primeiro par rotulado. Mudou a régua → é o REL-002.**

## §9. O que este experimento NÃO responde

- **Não** mede Recall@K, MRR, nDCG, nem se o retriever funciona.
- **Não** estabelece que os rótulos são **verdadeiros**. Estabelece que dois
  procedimentos concordaram em grau medido. Concordância não é verdade.
- **Não** cobre a relevância existente no corpus inteiro — só nos candidatos
  amostrados.
- **Não** transfere entre domínios: relevância em suporte técnico e em pesquisa
  jurídica têm distribuições diferentes.

### §9.1 Auto-referência declarada

O julgador humano é **quem escreveu o rubric**. Isso não é neutro: a concordância
mede, em parte, o quanto o LLM reproduz o critério de quem o formulou.

É a mesma limitação do `§9` do EDI-001, e pela mesma razão fica escrita aqui em
vez de descoberta por quem auditar.

## §10. Bloqueio de viabilidade — a perna humano × humano

A proposta original inclui 100 pares com **dois humanos independentes**, e está
certa: sem isso, κ = 0,85 pode significar apenas que o LLM aprendeu a imitar o
critério do anotador 1.

**Essa perna não pode rodar hoje.** O projeto tem um pesquisador. E, medido:

```
100 pares, acordo real 93%  →  κ = 0,59   IC [0,37 ; 0,77]
```

Quarenta pontos de largura — cobre reprovado, inconclusivo e quase aprovado ao
mesmo tempo. **Mesmo com dois humanos, 100 pares não decidiriam nada.**

Consequência declarada, não contornada: enquanto essa perna não rodar com N
suficiente, o resultado de REL-001 vale como *"o juiz LLM concorda com ESTE
anotador"* — e **não** como *"o instrumento é confiável"*. A diferença precisa
aparecer em qualquer material comercial derivado.

## §11. Critério de parada

Interrompe e registra como resultado metodológico, não como fracasso da
hipótese, se: houver vazamento entre os caminhos; a amostra divergir do
protocolo; o estrato `controle` não atingir `ACORDO_ESPERADO_CONTROLE`; ou mais
de 10% dos pares forem inclassificáveis pela regra do `§4`.

## §12. Auditoria da proposta original (EXP-REL-001)

Mantido: congelamento prévio, H0 publicável, independência dos caminhos, unidade
`(query, documento)`, rubric binário sem escala contínua, proibição de mudar
critério pós-dado, subamostra de dois humanos, `§15` do que não responde.

Corrigido, com o motivo:

| # | o que estava | por que falha |
|---|---|---|
| 1 | gate `κ ≥ 0,80` sem prevalência declarada | exige 97,1% de acordo em prevalência realista — inalcançável por construção |
| 2 | κ sobre 500 pares como independentes | 10 pares por query são correlacionados; IC estreito demais |
| 3 | subamostra de 100 pares | IC de 40 pontos; não decide |
| 4 | sem controle negativo | §4.5 exige, com previsão pré-dado |
| 5 | sem cálculo de poder | é a ausência que gerou 1, 2 e 3 |
| 6 | veredito sobre κ pontual | *caber não é passar* (E9b) |
| 7 | prevalência como métrica secundária | ela **determina** se o gate é atingível |
