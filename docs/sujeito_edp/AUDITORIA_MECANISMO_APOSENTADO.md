# Auditoria — quanto do modelo documentado descreve um caminho que não roda

**2026-08-18.** Motivada por três erros meus no mesmo dia, todos do mesmo tipo:
raciocinar sobre o caminho **cosseno** enquanto a produção roda o **híbrido**
desde 08/07/2026.

---

## §1. O fato que organiza tudo

`MemoryStore.retrieve` (`store.py:1495`) despacha na linha **1511**:

```python
from ..config import EDP_HYBRID_RETRIEVAL
if EDP_HYBRID_RETRIEVAL:
    return self._retrieve_hybrid(query, query_emb, top_k)
```

`EDP_HYBRID_RETRIEVAL` é **default `"1"`** desde a promoção de 08/07
(`config.py:53`). O comentário três linhas acima do despacho ainda diz
*"flag DESLIGADA por padrão"*.

## §2. O que cada caminho de fato usa

Contagem de ocorrências nos dois blocos (`EpisodicMemory.retrieve` e
`_hybrid_index` + `_retrieve_hybrid`):

| mecanismo | cosseno | híbrido | |
|---|---:|---:|---|
| `sim` (cosseno) | 2 | 0 | **aposentado** |
| `decay` temporal | 1 | 0 | **aposentado** |
| `prio` (prioridade) | 1 | 0 | **aposentado** |
| `access_boost` | 3 | 0 | **aposentado** |
| `epi_mult` (epistêmico) | 6 | 0 | **aposentado** |
| `src_weight` | 4 | 0 | **aposentado** |
| `dom_penalty` | 4 | 0 | **aposentado** |
| `anchor_boost` | 5 | 0 | **aposentado** |
| `session_boost` | 10 | 0 | **aposentado** |
| `nf_floor` (piso 20×) | 8 | 0 | **aposentado** |
| filtro adaptativo de sessão | 1 | 0 | **aposentado** |
| `min_score` | 7 | 2 | nos dois (escalas diferentes) |
| `filtro_recusa` | 9 | 8 | nos dois |
| exclusão `contradicted`/`quarantined` | 5 | 2 | nos dois |
| exclusão `answer_class` tóxico | 3 | 2 | nos dois |
| BM25 | 0 | 3 | só no vivo |
| RRF | 0 | 4 | só no vivo |
| dedup exp017 | 3 | 3 | nos dois |

> **Onze de dezoito mecanismos não decidem nada em produção** — incluindo os
> **dez fatores multiplicativos inteiros**.

O que sobrevive da governança epistêmica é **exclusão binária no índice**
(`store.py:1645-1662`): entra ou não entra. O rebaixamento graduado do
`nf_floor` não existe no caminho vivo.

## §3. O que isso faz com cada pré-registro

### exp008 — **a fórmula do tratamento quebra por escala**

```
treatment_score = ranking_score + BETA * overlap        BETA = 0.25
```

`ranking_score` em cosseno é ~0,4. Em RRF é **~0,016** — o próprio
`config.py:50` declara isso como dívida assumida, mas **só para dashboards e
telemetria Gauss**, não para a fórmula congelada do exp008.

Com RRF, o termo `BETA × overlap` chega a **0,25 contra uma base de 0,016** —
até **16× maior que o escore que ele deveria ajustar**. O tratamento deixa de
medir *"casar contra concepts/domain melhora o ranking existente"* e passa a
medir *"overlap sozinho vence o RRF"*. **São perguntas diferentes.**

Some-se ao desvio já declarado no §9-bis (`POOL_SIZE` 50 congelado, 100
rodando) e à errata do §9-ter (o abort por corpus foi diagnosticado no store
errado). **Três notas obrigatórias antes de qualquer disparo.**

### exp009 — **mede a remoção de privilégios que a produção não concede**

O `trat_gravador` altera `prioridade → "media"` e
`epistemic_status → "hypothesis"`; o exploratório mexe em `src_weight`. Os
**três têm zero ocorrências** no ranking híbrido.

H1 como especificada — *"remover os privilégios de nascença reduz a fração de
`session_summary` no top-5"* — não é mensurável no caminho vivo. Não por
refutação: **por mudança de substrato**.

E há um agravante empírico, observado hoje: uma `session_summary` dominou o
retrieval **sem** ter os privilégios (`prioridade='media'`,
`epistemic='hypothesis'`, `answer_class=None`). Ela venceu por **similaridade
pura** — resumos longos e genéricos ganham no BM25 e no vetor quando a query é
vaga. **Não há privilégio para remover.**

### exp012 / exp016 — **metade sobrevive**

A exclusão por `answer_class` tóxico **roda** no híbrido
(`store.py:1656`, sob `EDP_TOXIC_GUARDS`). O **piso de 20×**
(`NOT_FOUND_FLOOR`) **não existe** ali.

Consequência: a governança tóxica em produção é binária. Uma entrada
carimbada é excluída; uma sem carimbo compete em pé de igualdade. Não há o
meio-termo que o piso implementava — e as 32 `session_summary` do store têm
`answer_class = None`.

### exp010 — **é o experimento que criou o caminho vivo**. Íntegro.

### exp017 — **dedup/shuffle estão nos dois caminhos**. Íntegro.

### Fase 1/2 de tokens, E7, arco E9/E9b/E9c, E10 — **independentes do caminho**

Medem tamanho de prompt, tempo de motor local e verificação léxica. Nenhum
depende de qual retrieve roda.

## §4. O que isso faz com documentos de diagnóstico

- **`DIAGNOSTICO_SESSION_SUMMARY.md §4`** descreve "a pilha de score" com os
  nove fatores (dez, ver errata) — **a pilha aposentada**. As medições
  empíricas do §2 daquele documento continuam válidas como observação; a
  atribuição causal aos boosts, não.
- **`AUDITORIA_CONSTANTES_NAO_CALIBRADAS.md`** censa ~90 constantes tier A.
  Uma fração delas governa mecanismos que não rodam — calibrá-las seria
  calibrar o que não decide.
- **A telemetria de ranking de 13/08** foi desenhada em torno dos dez
  fatores. Em produção ela emite `{method, bm25, vec}`. O esquema já
  distingue por `metodo` (corrigido em 18/08), mas **a guarda dos dez fatores
  vigia o caminho aposentado**.

## §5. O que NÃO é conclusão desta auditoria

- **Não** diz que o híbrido é pior. O exp010 mediu ganho real (Recall@5
  25%→87,5%) e foi por isso que ele virou default.
- **Não** diz que os mecanismos aposentados são inúteis. Eles rodam se
  `EDP_HYBRID_RETRIEVAL=0`, e a flag é a rede de rollback declarada.
- **Não** mede nada novo. É leitura de código e contagem — Tier C
  (argumentado), não Tier D.

## §6. A consequência prática

Antes de disparar qualquer experimento de retrieval, a pergunta obrigatória
passa a ser: **este tratamento toca algo que o caminho vivo usa?**

Para exp008 e exp009 a resposta é **não, como estão congelados**. Redisparar
qualquer um sem redesenho gastaria rodada para medir mecanismo que não decide.

E a causa-raiz é barata de consertar: **o comentário do `store.py:1504` mente
sobre o default desde 08/07**, e foi ele que me enganou. Um comentário errado
no ponto de despacho custou três erros num dia.
