# Acervo de Experimentos — cobertura de pré-registro

FASE C, T3. Uma linha por experimento presente em
`sujeitos/edp/experimentos/` (arquivos `expNNN*.py`). O acervo é
**heterogêneo por construção**: a disciplina de pré-registro em arquivo
começou no 008. Os experimentos anteriores (001/003/004/006/006b/007) **não
são reconstruídos retroativamente** — um pré-registro escrito depois do dado
não é pré-registro; fabricá-lo destruiria a garantia que a categoria existe
para dar (ver T3 do prompt desta fase). Esta tabela é o registro honesto do
que existe, não uma correção do passado.

| exp | tem pré-registro em arquivo? | onde | disciplina aplicada |
|---|---|---|---|
| 001 | **NÃO** | — | Anterior à adoção da disciplina (008+). `exp001.py` cita no docstring "Espelha preregistro_experimento_001.md" — **esse arquivo nunca existiu** (confirmado: ausente em `docs_edp_v5/` e em `git log --all` do clone `edp_v5`). A frase é aspiracional/copiada do padrão que só se cumpriu a partir do 008. O código é CONGELADO pós-1º-disparo (convenção seguida), mas sem documento prévio. |
| 003 | **NÃO** | — | Mesmo padrão do 001: docstring cita `preregistro_experimento_003.md`, nunca existiu. |
| 004 | **NÃO** | — | Mesmo padrão: docstring cita `preregistro_experimento_004.md`, nunca existiu. |
| 006 | **NÃO** | — | Mesmo padrão: docstring cita `preregistro_experimento_006.md`, nunca existiu. |
| 006b | **NÃO** | — | Mesmo padrão: docstring cita `preregistro_experimento_006b.md`, nunca existiu. |
| 007 | **NÃO** | — | Mesmo padrão: docstring cita `preregistro_experimento_007.md`, nunca existiu. |
| 008 | **SIM** | `docs_edp_v5/preregistro_experimento_008.md` | Formal e completo — as 11 seções de `docs/TEMPLATE_PREREGISTRO.md` presentes (inaugura a categoria RETRIEVAL-QUALITY e a disciplina de arquivo). |
| 009 | **SIM** | `docs_edp_v5/preregistro_experimento_009.md` | Formal e completo. Inclui histórico de refino da regra "trivial" (v1→v2) registrado **antes de armar**, não depois de ver o resultado. |
| 010 | **SIM** | `docs_edp_v5/preregistro_experimento_010.md` | Formal e completo. Reusa o dataset validado do 009 com transparência sobre o que foi descartado (needle FAISS omitida, motivo documentado). |
| 011 | **NÃO** (só validação) | `docs_edp_v5/VALIDACAO_EXP011.md` | O relatório referencia "critérios §1.4 congelados no pré-registro da Fase 1" — **esse documento-fonte não foi localizado** em `docs_edp_v5/` nem no clone `edp_v5`. O que existe é o veredito (guardas §1.4/§1.5, binário PASSA/FALHA), não o pré-registro em si. |
| 012 | **NÃO** (só relatórios de etapa) | `docs_edp_v5/ESTADO_EXP012.md`, `RELATORIO_ETAPA0_EXP012V2.md` | Sem arquivo de pré-registro dedicado, mas com postura equivalente: critério de congelamento declarado inline ("100% ou reavaliar, nunca afrouxar" — §2.3) e a regra v1 tratada como **REFUTADA** (não remendada) quando não bateu na calibração. |
| 016 | **NÃO** (só relatório de etapa) | `docs_edp_v5/RELATORIO_ETAPA0_EXP016.md` | Sem pré-registro dedicado; disciplina de dry-run-antes-de-aplicar seguida (`exp016_dryrun.py` → autorização do pesquisador registrada por data → `exp016_backfill_apply.py`). |

## Nota — exp017 (fora desta tabela por escopo, citado por completude)

`PRE_REGISTRO_EXP017.md` (e os relatórios `EXP017_FASE0.md`,
`EXP017_FASE2.md`, `RELATORIO_*_EXP017.md`) existem em `docs_edp_v5/` e foi
uma das 4 fontes do template (T2) — mas **não tem script correspondente em
`sujeitos/edp/experimentos/`**: sua "encarnação" é uma feature flag no core
do `edp_v5` (`EDP_RETRIEVE_DEDUP`/`EDP_RETRIEVE_SHUFFLE`), não um harness de
laboratório como os demais. Por isso fica fora da tabela acima (que é
estritamente sobre `sujeitos/edp/experimentos/`), registrado aqui para não
desaparecer silenciosamente do acervo.

## Nota — E7 (primeiro experimento nativo; fora da tabela por ainda não ter código)

`docs/preregistro_experimento_e7.md` — "Quanto do repeat_rate de 80% em uso
real é topicalidade legítima, e não patologia de retrieval?" — pré-registrado
em 2026-07-28. **Primeiro pré-registro NATIVO do `lab_edp`** (todos os
anteriores nesta tabela foram herdados do `edp_v5`); vive em `docs/`, não em
`docs_edp_v5/`. Formal e completo: as 11 seções de
`docs/TEMPLATE_PREREGISTRO.md` estão presentes (as 6 obrigatórias e as 5
recomendadas — nenhuma faltando, ao contrário do exp017). Reusa
deliberadamente os cortes de decisão (15pp/5pp) já congelados no
`PRE_REGISTRO_EXP017.md` em vez de escolher novos limiares para este dado.

Fica **fora da tabela principal** pelo mesmo motivo do exp017, mas na direção
oposta: o exp017 tem pré-registro sem script; o E7 tem pré-registro e
`sujeitos/edp/experimentos/exp_e7.py` **ainda não foi escrito** — por
decisão explícita, respeitando a régua do próprio documento (pré-registro
antes do código; a encarnação só nasce depois, e congela no 1º disparo
real). Quando o código existir, esta linha migra para a tabela principal.

## Nota — numeração não-contígua

`002`, `005`, `013` e `014` não aparecem em nenhum lugar (nem código, nem
doc) nos dois repositórios. `015` existe como branch remota no `edp_v5`
(`origin/exp015`, sem arquivo/doc neste checkout) e é citado de passagem no
docstring de `exp016_dryrun.py` como "exp015 REFUTADO, 14/07" — um
experimento real que não deixou artefato rastreável neste acervo. Não
investigado além disto (fora do escopo desta fase, que é documental, não
arqueológica).
