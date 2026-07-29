# RELATÓRIO — E7 HARNESS (T1-T5)

Implementa §3, §5, §6 de `docs/preregistro_experimento_e7.md` sobre a
sequência já extraída pelo PASSO 1 (`e7_extrai_sequencia.py`). Pré-registro
**não foi alterado** — mudou a régua seria E7b.

## Decisão de desenho (registrada aqui, conforme pedido)

`restore()` roda ANTES de cada query (`SujeitoEDP.carregar_snapshot` recarrega
o clone), então o resultado do retrieve depende só de `(store, query)` — nunca
da vizinhança. Logo o retrieve roda **uma vez por turno** (n_turnos chamadas,
não 2n): a condição `shuffled` é uma **PERMUTAÇÃO** da mesma lista de
resultados já coletados (`random.Random(SEED_SHUFFLE).shuffle`), não uma
segunda rodada de retrieve. Isso é fiel ao §3 ("os MESMOS turnos, ordem
embaralhada"), elimina variância entre condições, e é o mesmo invariante que a
matriz do exp017 provou: overlap depende só do PAR DE CONJUNTOS de resultados,
nunca de quando foram medidos. Consequência direta: a **referência neutra**
(matriz completa par-a-par) é idêntica em `real` e `shuffled` por construção —
testado em `test_referencia_neutra_e_invariante_a_permutacao`.

## Reuso vs código novo

**Reusado sem reimplementação** (nenhuma lógica de análise nova):
- `bancada/auditoria.py::analyze_cross_query_repetition` — binário
  (`overlap >= min(2,k)`), contínuo (`|∩|/k`), matriz completa par-a-par e
  referência neutra (`ref_binary_rate`/`ref_continuous_mean`). É exatamente
  a instrumentação do §5; `exp_e7.py` só extrai contagens dos pares
  consecutivos para alimentar o Wilson.
- `bancada/scorer.py::wilson` — IC95% sobre o binário de cada condição.
- `bancada/isolamento.py::experimental_session`/`verify_no_leak` e
  `sujeitos/edp/adaptador.py::SujeitoEDP` — sessão `__lab__`, fingerprint
  antes/depois, purge. Mesmo padrão de `exp008.py`.

**Novo** (o que faltava para o §5/§6):
- `calcula_condicao()` — costura `analyze_cross_query_repetition` + `wilson`
  em um resultado por condição.
- `permuta_shuffled()` — a permutação com seed congelada (§3).
- `classifica_veredito()` / `instrumento_valido()` — o critério travado do §6,
  isoladas como funções puras para teste de fronteira exato (15pp/5pp).
- `imprime_relatorio()` — os três brutos + IC + gap + veredito + validade do
  instrumento. Nunca imprime a matriz completa (só usa os dois agregados dela).

**Mudança fora de `bancada/`** (permitida — só `bancada/` era vedado):
`SujeitoEDP.consultar` ganhou `min_score: float = 0.0` (default preserva
comportamento de `exp008.py`). O §7 do pré-registro exige
`MemoryStore.retrieve(..., min_score=0.20)`, e o método não expunha esse
parâmetro — parâmetro aditivo, nenhum chamador existente quebra.

## Testes

`tests/test_exp_e7.py` — 8 testes, todos sobre as partes PURAS (nenhum toca
`edp`; mesmo precedente de exp008/009/010, que não têm suíte de pipeline
completo por exigirem o pacote `edp` instalado — ver FASE B1):
métricas batendo à mão (fixture de 6 turnos, 3 pares com overlap 2/5 + 2 sem),
invariância da referência neutra à permutação, reprodutibilidade da seed,
cortes exatos de `classifica_veredito` (15pp/5pp, incl. veredito H1 de ponta
a ponta), `instrumento_valido` dentro/fora do intervalo, guarda de poder
(`n < MIN_TURNOS` para SEM importar `edp`), e falha explícita se a sequência
não existir.

`pytest tests/ -q`: 38 passed (30 pré-existentes + 8 novos).

## Comando exato da rodada (Windows — do pesquisador)

```powershell
$env:EDP_BASE_DIR = "C:\edp_data_fase0"
python -m sujeitos.edp.experimentos.e7_extrai_sequencia --out e7_sequencia.jsonl
python -m sujeitos.edp.experimentos.exp_e7 --sequencia e7_sequencia.jsonl --out e7_resultados.jsonl
```

Produz `e7_resultados.jsonl` (export no formato de `bancada/auditoria.py`,
ordem real) e imprime o relatório com os três brutos, IC95%, gap e veredito.

**PARAR — a rodada é do pesquisador.** Nada disto foi executado aqui: não há
`EDP_BASE_DIR` nem o pacote `edp` neste ambiente (confirmado antes de
começar). O harness foi validado só pelos testes puros acima.
