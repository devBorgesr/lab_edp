# RELATÓRIO — exp018 HARNESS (T1-T6)

Pré-registro: `docs/preregistro_experimento_018.md`, commit
`f578b45554c0a8b6ac6d6caf6d2ea9a694a01d40` (congelado, não alterado por
este trabalho). T1 completo em `docs/RELATORIO_EXP018_T1.md`.

## Achados do T1 (recap com file:line — detalhe completo no RELATORIO_EXP018_T1.md)

Confirmado em `/mnt/edp_v5_main` @ `788d7f58f3c6571c97839e3ba82a523a36b587b5`
(branch `exp017/fase1-dedup`), só leitura:

- `cluster_entries()` (`consolidation.py:22-54`): greedy ANCORADO no primeiro
  elemento não-visitado (não é single-linkage transitivo). Sem mínimo de
  cluster — `CONSOLIDATION_CLUSTER_MIN` é import morto. Não ameaça C7.
- `consolidate()` (`:157-212`): dois branches de promoção, `:188`
  (pós-merge) e `:195` (entry sozinha), nenhum menciona `answer_class`.
- `merge_cluster()` (`:95-153`): dict de retorno com dez chaves, sem
  `answer_class` (`:142-153`); `total_acessos` soma em `:119`. H3 não
  refutada na leitura.
- `SemanticMemory.promote()` (`memory/semantic.py:63-86`): `entry=dict(entry)`
  em `:81`. Achado extra (fora do pré-registro): guard anterior (Dívida
  #49, `:69-80`) recusa promover texto que bata frases exatas de "confiança
  alta" do `echo_chamber` — o dataset (T2) evita essas frases de propósito.
- `apply_actions()` (`cognitive_scheduler.py:169-172`): o branch
  `"consolidate"` ignora `target_ids` e chama a MESMA `consolidate()` já
  analisada — testar o caminho do scheduler não mediria nada que C1/C2
  (chamada direta) já não meçam. **Escopo decidido: caminho do scheduler
  fica para exp018b; C1-C7 usam `consolidate()`/`consolidate_promote_only()`
  diretos**, exatamente como o pré-registro previa como saída válida do T1.

Nenhum GATE disparado. Discrepâncias de citação encontradas (não bloqueiam
nada): `EDP_CLUSTER_THRESH` está em `config.py:161`, não `:122`;
`consolidate()` termina em `:212`, não `:229`.

## Cosseno real de C7 (prova exigida pelo §5)

`cosseno_c7()` recalcula a partir dos embeddings plantados (nunca
hardcoded): **0.824027** — acima de `CLUSTER_THRESH_ALVO=0.80`, com folga
de ~2,4pp (nem raso demais para ser frágil a arredondamento, nem tão perto
de 1.0 que pareça um artefato). Construção: vetor base determinístico (hash
do texto de A) + perturbação determinística pequena (hash de uma string
fixa) × `_ALPHA_PERTURBACAO_C7=0.68`, renormalizado — nunca do hash do
próprio texto de B (`sujeitos/edp/experimentos/exp018_dataset.py`, função
`_par_c7()`).

## Reuso vs código novo

**Reusado sem reimplementação:**
- `bancada/isolamento.py::experimental_session`/`verify_no_leak` e
  `sujeitos/edp/adaptador.py::SujeitoEDP` — sessão `__lab__`, fingerprint
  antes/depois, purge. Mesmo padrão de `exp008.py`/`exp_e7.py`.
- `edp.consolidation.consolidate`/`consolidate_promote_only` e
  `edp.runtime.registry.get_memory` — importados diretos e reais (§10,
  anti-mock não-negociável). `exp018.py` acessa `memory` bruto (fora do
  Protocol `Sujeito`, que não expõe isso) porque `consolidate()` precisa do
  objeto `MemoryStore`, não de um `session_id` via `sujeito.consultar()`.

**Novo:**
- `exp018_dataset.py` (T2): `build_dataset()`, `cosseno_c7()` — dataset
  congelado do §8, zero import de `edp`.
- `exp018.py` (T3): `posicao_flag_atual()`/`condicoes_para_posicao()`/
  `valida_flag()` (guarda de flag do §5), `inspeciona_resultado()` (métricas
  puras do §9), `_roda_condicao_funcao()` (orquestração real).
- `exp018_veredito.py` (T4): `valida_instrumento()`, `classifica_h1/h2/h3/h0()`,
  `divergencia_classes()`, `calcula_veredito()` — critério travado do §6,
  script separado, só lê o JSON acumulado.

**Achado de desenho durante a implementação (não estava no pré-registro,
não muda nenhuma régua — é só COMO medir "fundiu", que o §5/§9 não
detalham até esse nível):** checar só `memory.semantic.entries` para
"fundiu" conflaria "o cluster fundiu" com "a fundida foi promovida" —
inspecionar SÓ o semântico não deixa representar o caso em que o merge
ocorre no episódico (`merged_from==2` sobrevive em `memory.episodic.entries`
por construção de `consolidate()`, linha `:199`) mas a promoção é bloqueada
por algum caminho não mapeado. Isso é exatamente o que o H0 do §6 precisa
poder representar sem contradição. `inspeciona_resultado()` por isso
inspeciona os DOIS: `fundiu` vem do episódico, `promovida_fundida` e
`answer_class_presente` vêm do semântico, casados pelo id novo que o merge
gera. `test_inspeciona_resultado_c7_distingue_fundiu_de_promovida` prova a
distinção com um fixture sintético.

## Testes

`tests/test_exp018.py` — 12 testes, todos sobre lógica pura (dataset,
`inspeciona_resultado`, guarda de flag, veredito via fixtures sintéticas):
contagens/ids/classes por condição batendo o §11, textos distintos por
condição, `cosseno_c7()>0.80` recalculado, embeddings determinísticos +
dimensão real (384), `inspeciona_resultado` contando por classe e
distinguindo fundiu/promovida em C7, `condicoes_para_posicao` batendo
`FLAG_REQUERIDA`, guarda de flag abortando (`SystemExit`), e os cinco
desfechos do §6 (H1, H2+H3, H0, os dois INCONCLUSIVOs) mais a divergência
de classes tóxicas como achado lateral de um dos fixtures.

`pytest tests/ -q`: **50 passed** (38 pré-existentes + 12 novos).

## Comandos exatos da rodada (Windows — do pesquisador)

O dataset é 100% sintético (§8: "não depende do conteúdo de produção, só da
mecânica") — `EDP_BASE_DIR` pode apontar para qualquer diretório gravável
dedicado a este experimento (não precisa ser cópia de produção; ainda assim
NUNCA aponte para `C:\edp_data`, por disciplina — nenhuma condição escreve
lá, mas a distância de segurança é gratuita).

```powershell
# Processo 1 — posição de flag 1 (C1, C3, C5, C6, C7)
$env:EDP_BASE_DIR = "C:\edp_data_exp018_scratch"
$env:EDP_WRITE_PROVENANCE = "1"
python -m sujeitos.edp.experimentos.exp018 --todas --out exp018_resultados.json

# Processo 2 — posição de flag 0 (C2, C4) — PROCESSO SEPARADO,
# a flag é lida no import de config.py (§5)
$env:EDP_WRITE_PROVENANCE = "0"
python -m sujeitos.edp.experimentos.exp018 --todas --out exp018_resultados.json

# Veredito — le o JSON acumulado dos dois processos, aplica o §6
python -m sujeitos.edp.experimentos.exp018_veredito --resultados exp018_resultados.json
```

Ordem entre os dois processos não importa (o JSON acumula por chave
`condicao/funcao`); os DOIS precisam rodar antes do veredito para H2 (que
exige C3 e C4) ficar classificável — H1 e H3 já ficam decidíveis só com o
processo 1.

**PARAR — a rodada é do pesquisador.** Nada disto foi executado de verdade
aqui: nenhuma sessão `__lab__` foi aberta, nenhum `consolidate()` real
rodou. Verificado antes de escrever qualquer coisa: `edp` está pip-instalado
neste ambiente (3.21.0) e `/mnt/edp_v5_main` está no commit exato do
pré-registro — usados SÓ para leitura de código (T1) e para checar, por
inspeção de `edp/memory/store.py:1191-1298`, que `MemoryStore.episodic`/
`.semantic` são properties públicas que resolvem para o `_ScopedView`
correto (confirma que `_roda_condicao_funcao()` está correto). O harness
foi validado só pelos 12 testes puros acima — nenhum disparo real.
