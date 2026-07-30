# VEREDITO_EXP018.md — Promoção tóxica pelo caminho automático

Contrato: `docs/preregistro_experimento_018.md` @ `f578b45` (congelado).
T1: `docs/RELATORIO_EXP018_T1.md` @ `317fed3`. Harness:
`docs/RELATORIO_EXP018_HARNESS.md` @ `aca38e5`.
Rodada: 29/07/2026, pelo pesquisador. Segundo experimento nativo do lab_edp.

## Reprodutibilidade

| Item | Valor |
|---|---|
| EDP (sujeito) | `788d7f5`, branch `exp017/fase1-dedup` |
| EDP_BASE_DIR | `C:\edp_data_fase0` (cópia; dataset é sintético, produção não lida) |
| Cosseno real de C7 | 0.824027 (> 0.80 = `CONSOLIDATION_SIM_THRESH`) |
| Isolamento | 9 sessões `__lab__` distintas, `leak_ok=True` em todas |
| pytest | 50 passed |
| Processos | 2 (flag ON e OFF separados, §5) |

## Validade do instrumento (§6, ordem obrigatória)

| Controle | consolidate | promote_only | Veredito |
|---|---|---|---|
| C5 (+, normais, acessos=3) | 2 promovidas | 2 promovidas | OK — a promoção funciona |
| C6 (−, tóxicas, acessos=2) | 0 | 0 | OK — o threshold é respeitado |

Instrumento válido. Os três Hs são interpretáveis.

## Resultado

| Cond. | Função | flag | promovidas | not_found | disqualification |
|---|---|---|---|---|---|
| C1 | `consolidate()` | 1 | **4/4** | 2 | 2 |
| C2 | `consolidate()` | 0 | **4/4** | 2 | 2 |
| C3 | `consolidate_promote_only()` | 1 | **0/4** | 0 | 0 |
| C4 | `consolidate_promote_only()` | 0 | **4/4** | 2 | 2 |
| C7 | `consolidate()` | 1 | fundiu=True, merged_from=2, promovida_fundida=True, `answer_class` AUSENTE |

## VEREDITOS

**H1 CONFIRMADA.** `consolidate()` promove entry tóxica com `acessos >= 3`
em 100% dos casos, e a posição de `EDP_WRITE_PROVENANCE` é irrelevante
(4/4 nas duas) — porque não há guarda que a flag possa condicionar. Como os
três caminhos do §3 item 3 (`cognitive_scheduler.py:171`,
`auto_consolidate():326` no job do lifespan, `api/routes/memory.py:492`)
chamam a MESMA função, o vazamento é dos três.

**H2 CONFIRMADA.** C3 = 0 e C4 = 4: a guarda de `consolidation.py:290`
protege exatamente enquanto a flag está ON e desliga com ela. Dívida
arquitetural nomeada: **guarda de segurança não pode compartilhar flag com
rollback de feature**. Segunda ocorrência medida do padrão; a primeira é
`SemanticMemory.retrieve()` (`semantic.py:99-150`) sob
`EDP_HYBRID_RETRIEVAL=0`.

**H3 CONFIRMADA.** C7: duas entries com `acessos=2` cada — nenhuma cruza o
threshold sozinha — fundiram (`merged_from=2`), somaram para 4, e a fundida
foi promovida **sem `answer_class`**. Portar a guarda de `:290` para dentro
de `consolidate()` NÃO fecha o furo: `merged.get("answer_class")` seria
sempre `None`.

**H0 REFUTADA.** Não há filtro anterior não mapeado.

**Divergência entre classes tóxicas: NENHUMA.** `not_found` e
`disqualification` se comportaram idêntico em todas as condições — a guarda
trata o set uniformemente.

## Predições pré-dado: 5 de 5 confirmadas

Todas as cinco predições do §4 bateram (C1/C2 100%, C3 0% / C4 100%, C6 0%,
C7 fundida-promovida-sem-carimbo, classes idênticas).

**Ressalva de honestidade:** o mecanismo era legível no código antes da
medição (T1 leu as linhas). Isso é confirmação de leitura correta, não
previsão sobre sistema opaco — o valor do exp018 é a prova executável com
números exatos, e a descoberta de que o conserto exige três mudanças, não
uma.

## O achado de instrumentação que mudou um veredito

O output de C7 traz `promovidas=0` E `promovida_fundida=True`. Não é
contradição: `promovidas` conta as entries PLANTADAS (ids originais de A e
B), consumidas pelo merge; `promovida_fundida` rastreia a entry NOVA, com
uuid4 gerado por `merge_cluster():143`. O §9 do pré-registro dizia apenas
"inspecionar `memory.semantic.entries`" — seguindo isso à letra, C7 teria
sido lido como "não promoveu" e **H3 daria falso negativo**. O harness
(`inspeciona_resultado()`) inspeciona os DOIS layers: `fundiu` do episódico,
`promovida_fundida`/`answer_class_presente` do semântico. Crédito ao
executor; registrado como refinamento de instrumentação (não muda régua).

## Consequência: o fix é TRIPLO e tem ordem

1. **Guarda dentro de `consolidate()`**, nos dois branches de promoção
   (`:188` pós-merge e `:195` entry-sozinha).
2. **`merge_cluster()` propaga `answer_class` conservadoramente** — molde do
   `melhor_prio` (`:117`): qualquer tóxico no cluster ⇒ fundida tóxica. Sem
   isto, o item 1 é cego (H3).
3. **Desacoplar a guarda da flag de rollback** — a proteção de `:290` não
   pode morrer quando `EDP_WRITE_PROVENANCE=0` (H2). Mesmo tratamento devido
   ao furo do piso semântico sob `EDP_HYBRID_RETRIEVAL=0`.

**Ordem (§3 item 9):** os três furos são DORMENTES hoje — o store não tem
carimbo (`C:\edp_data_fase0`: 133/133 e 51/51 sem `answer_class`;
`merged_from`=0). O backfill de produção, pendente
(`ESTADO_EXP012.md:92,163-164`), os torna ATIVOS. **Fechar os três é
pré-requisito do backfill**, não trabalho paralelo.

## Limitações declaradas

- **Sintético, não observacional:** dataset plantado, `acessos` e
  `answer_class` definidos por desenho. Prova que o mecanismo vaza, não que
  vazou.
- **Caminho do scheduler não exercitado diretamente** (T1e): `apply_actions`
  ignora `target_ids` e chama a mesma `consolidate()`, então C1/C2 cobrem-no
  por identidade de função, não por execução. Side-effects próprios do
  `evaluate()` ficam para exp018b.
- **Confound da Dívida #49 eliminado POR DESENHO, não por medição:**
  `SemanticMemory.promote()` tem guard que recusa texto batendo frases
  exatas de "confiança alta" do `echo_chamber` (`semantic.py:69-80`). Os
  textos do dataset evitam essas frases de propósito. **Se alguém reescrever
  os textos, o confound volta** — qualquer exp018b precisa preservar essa
  restrição.
- **Discrepâncias de citação corrigidas na rodada:** `EDP_CLUSTER_THRESH`
  está em `config.py:161` na branch do sujeito (`:122` no main — árvores
  diferentes, ambas válidas para sua árvore); `consolidate()` termina em
  `:212`, não `:229` (erro do pré-registro). Lição: citação file:line vale
  apenas com a árvore declarada.