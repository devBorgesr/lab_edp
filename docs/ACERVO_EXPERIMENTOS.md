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
| E7 | **SIM** | `docs/preregistro_experimento_e7.md` | Formal e completo (11 seções do template, nenhuma faltando) — **primeiro pré-registro NATIVO do lab_edp**, escrito ANTES do harness. Harness em `sujeitos/edp/experimentos/exp_e7.py` (`docs/RELATORIO_E7_HARNESS.md`), veredito em `docs/VEREDITO_E7.md`: rodada real de 28/07/2026, H1 confirmada (gap +27,6pp), régua não alterada. |

## Nota — exp017 (fora desta tabela por escopo, citado por completude)

`PRE_REGISTRO_EXP017.md` (e os relatórios `EXP017_FASE0.md`,
`EXP017_FASE2.md`, `RELATORIO_*_EXP017.md`) existem em `docs_edp_v5/` e foi
uma das 4 fontes do template (T2) — mas **não tem script correspondente em
`sujeitos/edp/experimentos/`**: sua "encarnação" é uma feature flag no core
do `edp_v5` (`EDP_RETRIEVE_DEDUP`/`EDP_RETRIEVE_SHUFFLE`), não um harness de
laboratório como os demais. Por isso fica fora da tabela acima (que é
estritamente sobre `sujeitos/edp/experimentos/`), registrado aqui para não
desaparecer silenciosamente do acervo.

## Nota — E8 (planejado, não executado, ID reservado)

`E8` — baseline externa de retrieval (EDP vs. contexto-longo-ingênuo vs.
padrão LLM Wiki de Karpathy, com zero-contexto como filtro de validade
das perguntas) — está **planejado em `docs/plano_experimento_e8.md`, mas
NÃO executado e NÃO pré-registrado**. Segue a nomenclatura por letra do
E7 (nativo do `lab_edp`, não portado do `edp_v5`), por isso fica fora da
tabela acima (que é sobre `sujeitos/edp/experimentos/`) e desta nota em
diante, não da numeração `expNNN`.

**Status: PLANEJADO — NÃO EXECUTADO — bloqueado por `NORTE.md` até
02/09/2026** (ou antes, se a meta comercial descrita lá for atingida
primeiro). O documento de plano existe para não perder o desenho e para
**reservar o ID** — a última rodada de verificação quase colidiu com o
`exp018` já fechado (`docs/VEREDITO_EXP018.md`, promoção tóxica, assunto
não relacionado) por falta exatamente deste registro. Ver
`docs/ACHADO_PREMISSAS_RETRIEVAL.md` para os achados de Passo 0 que
sobreviveram à interrupção.

## Nota — numeração não-contígua

`002`, `005`, `013` e `014` não aparecem em nenhum lugar (nem código, nem
doc) nos dois repositórios. `015` existe como branch remota no `edp_v5`
(`origin/exp015`, sem arquivo/doc neste checkout) e é citado de passagem no
docstring de `exp016_dryrun.py` como "exp015 REFUTADO, 14/07" — um
experimento real que não deixou artefato rastreável neste acervo. Não
investigado além disto (fora do escopo desta fase, que é documental, não
arqueológica).

---

## Adendo — 07/08/2026: frente da wiki (4 pré-registros nativos do kernel)

Quatro pré-registros escritos em `edp_v5_main` em 06–07/08/2026, espelhados
em `docs_edp_v5/`. **Não seguem o `TEMPLATE_PREREGISTRO.md` deste repo** —
foram escritos sem que eu soubesse que o template existia aqui, o que é
falha de Passo 0 minha e fica registrado como tal, não corrigido
retroativamente. As 6 seções obrigatórias estão presentes em substância
(pergunta, régua, motivação, hipótese, desenho, critério PASSA/FALHA); a
numeração e os nomes de seção divergem.

| exp | pré-registro | onde | resultado | disciplina |
|---|---|---|---|---|
| Degrau 1 — honeypot | **SIM** | `docs_edp_v5/preregistro_degrau1_honeypot.md` | **H0**, 0/14 (`dd06b87`) | Critério congelado antes do dado. Predição do arquiteto registrada e **refutada**. Achado principal (R1, seletividade invertida) **não previsto**: das 14 queries, as 4 que passariam o gate de similaridade eram todas anafóricas, nenhuma factual. |
| Gate de especificidade | **SIM** | `docs_edp_v5/preregistro_gate_especificidade.md` | **não executado** | Hipótese livre de limiar (`min([N]) > max([R3])`) para impedir overfitting em 14 pontos. Emenda E1 pré-dado após smoke test. Checagem de sanidade do instrumento congelada (§3-bis.1): >20% de OOV nas [R3] ⇒ INSTRUMENTO INVÁLIDO. Superado pela errata do design. |
| Wiki — pré-condição | **SIM** | `docs_edp_v5/design_wiki_conversas.md` §11 | **PARAR**, 1/5 (`ad6d8ec`) | Teste de pré-condição assimétrico (pode refutar, não confirmar). Predição refutada. Rodada 2 contra produção: 1/5 de novo (`404429c`), mas varredura de texto cru deu 5/5 — problema de **cobertura da extração**, não ausência de conteúdo. |
| Wiki — E-2 extração | **SIM** | `docs_edp_v5/design_wiki_conversas.md` E-2/E-2.1 | **FALHA**, 2/5 (`366e337`) | Amostragem estratificada (emenda E-2.1 pré-dado, corrigindo defeito **estatístico** da E-2: aleatória daria 0,43 turnos esperados de um dos alvos). Controle negativo 0/20 FP, 0/108 falhas de parse. US$0,14. |
| Wiki — rodagem cruzada | **SIM** | `docs_edp_v5/preregistro_rodagem_cruzada_wiki.md` | **parcial** — condição W fechada | 12 perguntas + 3 controles negativos congelados antes de compilar. Emenda E-1 pré-dado: orçamento igual por condição e separação nota bruta/diferencial. |

### Errata que atravessa os quatro

`docs_edp_v5/design_wiki_conversas.md` registra que o design da wiki foi
escrito contra descrição de **segunda mão** do método `llm-wiki`, sem ler
o gist original. O E-2 mediu corretamente uma peça que o método **não
tem** — é irrelevante, não errado. O veredito "camada 3 cai" fica anulado
por justificativa documental, não por dado novo.

O que **sobrevive** do E-2 e vale por si: `cognitive_decisions` extrai
conceitos gerais e não entidades específicas (`exp016` 0/20,
`NOT_FOUND_FLOOR` 0/20, `Mongólia` 0/8, controle limpo).

### Scripts de medição — permanecem no kernel

`avaliador_honeypot_14q.py`, `medir_repeticao_honeypot.py`,
`medir_gate_especificidade.py`, `precondicao_wiki_conversas.py`,
`e2_extracao_alvos.py` seguem em `edp_v5_main/scripts/`. Importam
`edp.embeddings`/`edp.wiki` diretamente e um importa o outro; movê-los
exigiria reescrever imports e quebraria as citações nos pré-registros.
Registrado onde estão em vez de duplicado — **uma fonte, um lugar**.
