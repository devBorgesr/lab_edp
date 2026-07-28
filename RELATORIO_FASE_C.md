# Relatório — FASE C: Importação da Metodologia

Repo de trabalho: `lab_edp`. Repo de origem (read-only, nunca alterado):
`devBorgesr/edp_v5`, clone montado em `/mnt/edp_v5_main`,
`HEAD = 788d7f58f3c6571c97839e3ba82a523a36b587b5` (branch
`exp017/fase1-dedup`, commit de 2026-07-24). Nenhum arquivo de código foi
alterado nesta fase — só importação e extração documental. Gate `pytest`
verde após cada commit (22 passed, inalterado do fim da FASE B). Sem push.

## T1 — Documentos importados

| Arquivo | Linhas | Destino | Fonte (sha) |
|---|---|---|---|
| `edp_metodologia.md` | 447 | `docs_edp_v5/` | `edp_v5@788d7f5:docs/edp_metodologia.md` |
| `MARCOS_EPISTEMICOS.md` | 339 | `docs_edp_v5/` | `edp_v5@788d7f5:docs/MARCOS_EPISTEMICOS.md` |
| `DIVIDAS.md` | 60 | `docs_edp_v5/` | `edp_v5@788d7f5:docs/DIVIDAS.md` |

Contagem de linhas confirmada por `wc -l` no clone antes de copiar — bate
exatamente com o contexto verificado do prompt (447/339). Corpo comparado
programaticamente (string a string, após normalizar quebra de linha):
**idêntico**, à exceção de uma diferença de convenção — a fonte usa CRLF sem
newline final; a cópia usa LF com newline final, mesma convenção dos
pré-registros já presentes em `docs_edp_v5/` desde antes desta fase. Nenhuma
palavra, número ou caractere de conteúdo alterado. Cada arquivo recebeu o
bloco de proveniência de 3 linhas pedido, com o sha real (não placeholder).

## T2 — Estrutura do template (`docs/TEMPLATE_PREREGISTRO.md`)

Derivada por comparação seção-a-seção dos 4 pré-registros existentes.
Contagem final:

| Seção | 008 | 009 | 010 | 017 | Classificação |
|---|---|---|---|---|---|
| Título + pergunta de pesquisa | ✓ | ✓ | ✓ | ✓ | **OBRIGATÓRIA (4/4)** |
| Régua/nota de método | ✓ | ✓ | ✓ | ✓* | **OBRIGATÓRIA (4/4)** |
| Motivação/Contexto provado | ✓ | ✓ | ✓ | ✓ | **OBRIGATÓRIA (4/4)** |
| Hipótese(s) e predições | ✓ | ✓ | ✓ | ✓ | **OBRIGATÓRIA (4/4)** |
| Condições/Desenho | ✓ | ✓ | ✓ | ✓* | **OBRIGATÓRIA (4/4)** |
| Critério de decisão PASSA/FALHA | ✓ | ✓ | ✓ | ✓ | **OBRIGATÓRIA (4/4)** |
| Data de pré-registro explícita | ✓ | ✓ | ✓ | ✗ | RECOMENDADA (3/4) |
| Dataset | ✓ | ✓ | ✓ | ✗ | RECOMENDADA (3/4) |
| Métricas | ✓ | ✓ | ✓ | ✗ | RECOMENDADA (3/4) |
| Anti-mock e Isolamento | ✓ | ✓ | ✓ | ✗ | RECOMENDADA (3/4) |
| Constantes congeladas (tabela) | ✓ | ✓ | ✓ | ✗ | RECOMENDADA (3/4) |

(✓* = presente com forma diferente da numeração `§N` dos outros 3, mas
cumprindo a mesma função — detalhado no template.)

Seções descartadas por não atingirem 3/4: **"Fora de escopo"** (só em
`PRE_REGISTRO_EXP017.md`, 1/4) e **"Disparo e prova-no-espelho"** como seção
própria (só em 008; 009/010 dobram essa função dentro de
"Anti-mock/Isolamento", 1/4 isolada). Nenhuma seção foi inventada — as 11
que entraram são as que passaram no critério declarado (≥3/4).

Cada seção do template traz: nome canônico, frase do conteúdo, um exemplo
real citado por arquivo+seção de origem, e o critério de preenchimento.
Termina com checklist de 1 linha por seção.

## T3 — Acervo de experimentos (`docs/ACERVO_EXPERIMENTOS.md`)

Tabela por `expNNN*.py` em `sujeitos/edp/experimentos/`:

| Cobertura | Experimentos |
|---|---|
| **SEM** pré-registro em arquivo (pré-disciplina) | 001, 003, 004, 006, 006b, 007 |
| **SEM** pré-registro dedicado, só relatório de etapa/validação | 011, 012, 016 |
| **TEM** pré-registro formal completo | 008, 009, 010 |

Nenhum pré-registro retroativo foi fabricado para os experimentos sem
arquivo — a tabela documenta a heterogeneidade real, não a corrige.

**Achado adicional (não pedido, mas relevante para a lacuna):** os
docstrings de `exp001.py`/`exp003.py`/`exp004.py`/`exp006.py`/`exp006b.py`/
`exp007.py` citam "Espelha preregistro_experimento_NNN.md" como se esse
arquivo existisse — busca em `docs_edp_v5/` e `git log --all` do clone
`edp_v5` confirma que **nenhum desses arquivos jamais existiu**. É frase
aspiracional, copiada do padrão que só se cumpriu a partir do 008.

Notas de completude registradas no arquivo (fora da tabela principal, por
escopo): `exp017` tem pré-registro mas nenhum script em
`sujeitos/edp/experimentos/` (é feature flag no core do edp_v5, não harness
de laboratório); `002`/`005`/`013`/`014` não aparecem em lugar nenhum;
`015` existe só como branch remota no `edp_v5` (`exp015`, citado como
"REFUTADO" no docstring de `exp016_dryrun.py`), sem artefato rastreável
neste acervo.

## T4 — Decisão de proveniência (`docs/PROVENIENCIA_LAB.md`)

`lab_edp` declarado canônico daqui em diante; `edp/lab/` no `edp_v5` é
ancestral congelado (origem do `git subtree split -P edp/lab`).

Diferença verificada e é a causa-raiz do bug corrigido na FASE B6: `edp/lab/`
no edp_v5 é um pacote **flat** de 21 arquivos (confirmado por listagem —
22 entradas menos `__pycache__`) onde `scorer.py` faz `from . import
exp001` (topo do módulo) e `from . import exp004/exp006/exp006b/exp007`
(lazy, dentro de funções) — todos resolvem porque os `expNNN.py` são
**irmãos de pasta** do `scorer.py`. `lab_edp` separou isso em `bancada/` +
`sujeitos/edp/experimentos/` na FASE B2; as mesmas linhas de import,
copiadas sem ajuste para o novo layout, viraram `ImportError` garantido —
exatamente o bug fechado na FASE B6.

## T5 — README

Seção "Metodologia" acrescentada, apontando para
`docs/TEMPLATE_PREREGISTRO.md`, `docs_edp_v5/edp_metodologia.md` e
`docs/ACERVO_EXPERIMENTOS.md`, com a distinção explícita herdado
(`docs_edp_v5/`) vs nativo (`docs/`).

## Commits (branch `main`, sem push)

1. `517b675` — T1: importa documentos fundadores do edp_v5
2. `04b41c2` — T2: extrai TEMPLATE_PREREGISTRO.md
3. `cbf38d7` — T3: registra a lacuna de pré-registro por experimento
4. `a3b519a` — T4: resolve a duplicação lab_edp vs edp/lab (edp_v5)
5. `44d07d4` — T5: README ganha seção Metodologia
6. (este commit) — T6: `RELATORIO_FASE_C.md`

`pytest`: 22 passed em todos os 6 commits (nenhum arquivo de código tocado
na fase inteira). `edp_v5` permanece intocado — read-only durante toda a
fase.

---

PARAR.
