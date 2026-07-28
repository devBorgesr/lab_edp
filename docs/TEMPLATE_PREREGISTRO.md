# Template de Pré-registro — extraído dos 4 pré-registros existentes

FASE C, T2. Estrutura **derivada por comparação**, não inventada: os quatro
pré-registros que existem em `docs_edp_v5/` —
`preregistro_experimento_008.md`, `preregistro_experimento_009.md`,
`preregistro_experimento_010.md` e `PRE_REGISTRO_EXP017.md` — foram lidos
seção a seção e comparados. Uma seção só entra aqui se aparece em **pelo
menos 3 dos 4**. Nomes de seção variam de documento para documento (ex.:
"Motivação" em 008/010 vs "Contexto provado" em 009); o critério de
contagem é a **função da seção**, não a string exata do cabeçalho — cada
entrada abaixo cita onde o nome varia.

`PRE_REGISTRO_EXP017.md` é o mais distante do padrão comum: não usa
numeração `§N`, e é o único dos 4 sem seções próprias de **Dataset**,
**Métricas**, **Anti-mock/Isolamento** e **Constantes congeladas** — essas
informações existem no documento, mas espalhadas dentro de "Desenho" e dos
aditivos ("ERRATA", "E6") em vez de isoladas. Por isso essas 4 seções caem
em RECOMENDADA (3/4), não OBRIGATÓRIA.

---

## Seções OBRIGATÓRIAS (presentes nos 4/4 pré-registros)

### 1. Título + pergunta de pesquisa

**Contém:** o nome do experimento e, como subtítulo, a pergunta que o
experimento responde — formulada de um jeito que admite resposta
sim/não (ou H1/H0), citando o mecanismo em teste.

**Exemplo real:** *"Retrieval híbrido (BM25 + vetorial + RRF, MMR opcional)
melhora a recuperação vs cosine puro?"* — de `preregistro_experimento_010.md`
(título/subtítulo).

**Critério de preenchimento:** a pergunta cita o mecanismo concreto sendo
testado (não "isso funciona melhor?" genérico) e é redigida de forma que o
próprio critério de decisão (seção 6) responda sim ou não a ela.

---

### 2. Régua / nota de método (compromisso de pré-registro)

**Contém:** a declaração explícita de que hipótese, condições, métricas e
critério de decisão são fixados **antes de qualquer dado**, e de que a
encarnação em código (`expNNN.py`) **congela no primeiro disparo real**.

**Exemplo real:** *"Régua da Bancada (método): este documento declara
hipótese, condições, métricas, dataset e critério de decisão ANTES de
qualquer dado. A encarnação (`exp008.py`) espelha este `.md` e é CONGELADA
após o 1º disparo."* — de `preregistro_experimento_008.md` (bloco de
citação logo após o título).

**Critério de preenchimento:** declara (a) que nada aqui foi ajustado após
ver dado, e (b) o gatilho exato de congelamento ("ao primeiro disparo
real"). Em `PRE_REGISTRO_EXP017.md` esta função aparece em prosa no
parágrafo de abertura ("Registrado ANTES de qualquer implementação...";
"NÃO se descongela para ajustar parâmetros depois de ver resultado" está
em `preregistro_experimento_010.md`), não em bloco de citação — a forma
varia, a função (compromisso + congelamento) está nos 4.

---

### 3. Motivação / Contexto provado

**Contém:** a evidência concreta e já verificada (medição real ou leitura
de código com `arquivo:linha`) que justifica rodar o experimento — não
uma suposição.

**Exemplo real:** *"Auditoria de diagnóstico anterior provou, com
evidência `file:line`, que o campo `entry["cognitive_decisions"]`
(produzido por `edp/runtime/cognitive_decisions.py`) é gravado e
persistido em disco, mas nenhuma leitura age sobre o hot path de
retrieval"* — de `preregistro_experimento_008.md` §1 ("Motivação").

**Critério de preenchimento:** toda alegação cita sua fonte verificável
(linha de código, log de medição, ou experimento anterior) — nada
"assumido". Em `preregistro_experimento_009.md` a seção equivalente
chama-se §1 "Contexto provado (não re-derivado; código + medição real)"
— nome diferente, mesma função.

---

### 4. Hipótese(s) e predições

**Contém:** H1 (o efeito esperado) e H0 (a hipótese nula), declaradas
antes de qualquer dado. H0 vencer é tratado como achado válido, não como
fracasso do experimento.

**Exemplo real:** *"H1: Remover os privilégios de nascença das
`session_summary` (prioridade alta + verified) reduz drasticamente a
fração delas no top-5 [...] H0: A dominância persiste mesmo sem os
privilégios [...] (H0 vencer também é achado: aponta o fix para outro
lugar)"* — de `preregistro_experimento_009.md` §2.

**Critério de preenchimento:** H1 e H0 são mutuamente exclusivas, cada
uma prediz um resultado observável, e o texto declara explicitamente que
H0 vencer não invalida o experimento.

---

### 5. Condições / Desenho experimental

**Contém:** as condições que serão comparadas (rótulo + papel de cada
uma), incluindo controle negativo quando aplicável.

**Exemplo real:** tabela de 3 condições — `baseline` (controle),
`tratamento` (variante experimental), `tratamento_control_shuffle`
(controle negativo de validade: "se o control também melhorar [...] →
setup SUSPEITO, nenhum achado é afirmado") — de
`preregistro_experimento_008.md` §3.

**Critério de preenchimento:** cada condição tem rótulo único usado depois
no scorer (`condicao_rotulo`), papel declarado em uma frase, e — quando o
desenho permite — um controle negativo que, se "vencer", invalida o
achado em vez de confirmá-lo. Em `PRE_REGISTRO_EXP017.md` esta função é a
seção "Desenho" (estruturada em FASE 0/1/2 em vez de uma tabela de
condições) — a diferença de forma reflete que o 017 mede um sistema
inteiro (dedup no retrieve), não condições de prompt isoladas.

---

### 6. Critério de decisão (PASSA/FALHA)

**Contém:** os limiares numéricos exatos que decidem H1 vs H0, fixados
antes do dado, sem reabertura depois de ver o resultado.

**Exemplo real:** *"PASSA H1 sse, com flag ON: dup_rate@10 = 0 (por ID E
por hash) nos retrieves de calibração [...] suite pytest verde, incluindo
novo teste flag-off"* — de `PRE_REGISTRO_EXP017.md`, seção "Critérios
PASSA/FALHA".

**Critério de preenchimento:** todo limiar é um número ou uma fórmula
(não "melhora visivelmente"), e o texto declara que o critério não pode
ser reaberto após ver o resultado (`preregistro_experimento_010.md`:
"NÃO se descongela para ajustar parâmetros depois de ver resultado (bug
que invalide ⇒ exp010b novo)").

---

## Seções RECOMENDADAS (presentes em 3/4 — falta em `PRE_REGISTRO_EXP017.md`)

### 7. Data de pré-registro explícita

**Contém:** uma linha isolada com a data em que o documento foi
congelado, anterior ao primeiro disparo real.

**Exemplo real:** *"Data de pré-registro: **2026-06-27** (antes do
disparo). Congelar ao primeiro fire."* — de
`preregistro_experimento_008.md`.

**Critério de preenchimento:** uma data explícita, isolada (não misturada
em prosa), anterior à data do primeiro disparo real registrado no
prontuário.

**Por que falta no 017:** o documento tem datas pontuais de decisão
("congeladas em 19/07/2026") e uma ERRATA datada (20/07/2026), mas
nenhuma linha única "Data de pré-registro:" no topo.

---

### 8. Dataset (CONGELADO)

**Contém:** as queries/casos de teste exatos, com regra determinística de
construção quando o conteúdo depende do store real, e resolução de
qualquer pendência (needle que não resolveu, etc.) **antes de armar**.

**Exemplo real:** dataset em 4 blocos — VAGAS (n=6, lista literal),
REDIS (n=3, ids reais), ESPECÍFICAS (n=6, needle→id), GUARDA (n=3) — de
`preregistro_experimento_009.md` §4.

**Critério de preenchimento:** toda query/caso é reproduzível (lista
literal ou regra determinística), e qualquer decisão pendente (ex.: "needle
`faiss` não resolveu") tem uma resolução registrada **antes** do disparo
real, não depois.

**Por que falta no 017:** as queries usadas aparecem dentro do aditivo
"E6 — Segunda rodada" (lista literal de 14 queries), não numa seção
"Dataset" isolada da Fase 1/2.

---

### 9. Métricas

**Contém:** a definição operacional de cada métrica (fórmula) e o método
de agregação com intervalo de confiança.

**Exemplo real:** *"Recall@3 (binário): a memória-alvo está no top-3?
[...] Reciprocal Rank: `1/posição_do_alvo` [...] MRR = média dos
reciprocal ranks [...] Recall@3 e Recall@5 com intervalo de confiança de
Wilson 95%"* — de `preregistro_experimento_008.md` §4.

**Critério de preenchimento:** cada métrica citada no critério de decisão
(seção 6) tem aqui sua fórmula e o método de agregação/IC declarados —
nada calculado "ad hoc" na hora do relatório.

**Por que falta no 017:** as métricas (`dup_rate@10`, `repeat_rate`,
`overlap_frac`) são definidas dentro da seção "Critérios PASSA/FALHA" e do
aditivo E6, sem uma seção "Métricas" própria.

---

### 10. Anti-mock e Isolamento

**Contém:** a declaração de que o experimento roda sobre o mecanismo REAL
(não reimplementado) e o dispositivo que impede vazamento para produção
(sessão `__lab__`, cópia + snapshot/restore, fingerprint de no-leak).

**Exemplo real:** *"Isolamento por construção: `MemoryStore.retrieve`
muta e persiste [...] Por isso NUNCA se chama retrieve sobre o store de
produção. O clone é injetado numa sessão `__lab__` dedicada [...],
purgada ao fim"* — de `preregistro_experimento_008.md` §7.

**Critério de preenchimento:** nomeia a função/classe real testada (não
mock) por `arquivo:linha`, e descreve o mecanismo de isolamento com
verificação de no-leak (hash antes/depois, ou equivalente).

**Por que falta no 017:** os "INVARIANTES DE SEGURANÇA" (ex.: "Dedup
roda DEPOIS de piso NOT_FOUND_FLOOR [...] Flag OFF = byte-idêntico")
estão embutidos dentro de "Desenho → FASE 1 → c", não numa seção própria.

---

### 11. Constantes congeladas (tabela)

**Contém:** tabela `constante | valor` com todo número usado no critério
de decisão, espelhado no código do experimento (`expNNN.py`).

**Exemplo real:** tabela com `EXPERIMENTO`, `BETA=0.25`, `POOL_SIZE=50`,
`K3`/`K5`, `MIN_PAIRS`/`MAX_PAIRS`, `STOPWORDS`, etc. — de
`preregistro_experimento_008.md` §9.

**Critério de preenchimento:** toda constante numérica citada em Condições
(5), Métricas (9) ou Critério de decisão (6) aparece nesta tabela, e o
texto declara que a tabela é imutável após o primeiro disparo ("Mudou a
régua → é o Experimento NNN+1").

**Por que falta no 017:** constantes como o corte de H2 (15pp) e a seed
(`EDP_SHUFFLE_SEED=20260719`) aparecem em prosa espalhada pelo documento,
não numa tabela dedicada.

---

## Checklist (colar em pré-registro novo)

```
[ ] 1.  Título + pergunta de pesquisa (sim/não, cita o mecanismo)
[ ] 2.  Régua/nota de método (compromisso pré-dado + gatilho de congelamento)
[ ] 3.  Motivação/Contexto provado (toda alegação cita arquivo:linha ou medição)
[ ] 4.  Hipótese(s): H1 + H0, H0 vencer é achado válido
[ ] 5.  Condições/Desenho: rótulos únicos + controle negativo se aplicável
[ ] 6.  Critério de decisão: limiares numéricos, sem reabertura pós-dado
[ ] 7.  Data de pré-registro explícita, anterior ao 1º disparo real
[ ] 8.  Dataset CONGELADO: reproduzível, pendências resolvidas antes de armar
[ ] 9.  Métricas: fórmula + método de agregação/IC para cada uma
[ ] 10. Anti-mock e Isolamento: mecanismo real citado + no-leak verificado
[ ] 11. Constantes congeladas: tabela completa, espelhada no expNNN.py
```
