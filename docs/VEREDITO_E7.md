# VEREDITO_E7.md — repeat_rate sobre sequência conversacional real

Contrato: `docs/preregistro_experimento_e7.md` (congelado antes do dado).
Harness: `sujeitos/edp/experimentos/exp_e7.py` (`RELATORIO_E7_HARNESS.md`).
Rodada: 28/07/2026, pelo pesquisador. **Primeiro experimento nativo do
lab_edp** — pré-registrado, executado e concluído sob o próprio teto.

## Reprodutibilidade (registrado no momento da rodada)

| Item | Valor |
|---|---|
| EDP (sujeito) | `788d7f5`, branch `exp017/fase1-dedup` |
| Store | `C:\edp_data_fase0` (cópia; produção intocada) |
| sha256 da sequência | `342d22e21604f6de8bde6cb3a3c2c195b91ce657bd84005f2be8e632c81c7a7f` |
| Flags exp017 | HYBRID / CTX_SLOTS / DEDUP / SHUFFLE / RANDOM_DROP: todas `<unset>` (defaults de produção) |
| Isolamento | sessão `__lab__8ce4a93aa425`, `verify_no_leak` OK |
| Constantes (§8) | TOP_K=5, MIN_SCORE=0.20, SEED_SHUFFLE=20260728, MIN_TURNOS=20 |

Extração (PASSO 1): 133 entries totais → 27 excluídas por
`[session_summary]` → 0 excluídas por forma → **106 turnos**, 105 pares
consecutivos. O n_total = 133 bate exatamente com a episódica medida no
censo cego do exp017 (`EXP017_FASE0.md` §1).

## Resultado

| Condição | Binário | IC95% | Contínuo | n_pares |
|---|---|---|---|---|
| real | **31,4%** | [23,3%, 40,8%] | 22,7% | 105 |
| shuffled | **3,8%** | [1,5%, 9,4%] | 4,0% | 105 |
| neutra (analítica) | 5,5% | — | 5,4% | matriz completa |

- gap amostral (real − shuffled) = **+27,6pp**
- gap analítico (real − neutra) = **+25,9pp**
- gap contínuo (real − shuffled) = +18,7pp

## VEREDITO: H1 — TOPICALIDADE DOMINA

Critério congelado no §6: gap ≥ 15pp. Cumprido com folga (27,6pp), e com
três reforços que o critério exigia mas não garantia:

1. **Os IC95% não se sobrepõem** — piso do real (23,3%) fica 13,9pp acima
   do teto do shuffled (9,4%). O gap sobrevive a re-amostragem.
2. **Os dois gaps concordam** (27,6 vs 25,9pp): a permutação sorteada pela
   seed foi típica, não afortunada. O shuffled (3,8%) caiu levemente abaixo
   da expectativa analítica (5,5%) — ruído esperado de amostra n=1.
3. **Validade do instrumento OK**: a referência neutra caiu entre shuffled
   e real, como o §6 previa se H1 fosse verdadeira.

Leitura: turnos consecutivos sobre o mesmo assunto recuperam as mesmas
memórias, e essa adjacência tópica responde por praticamente todo o
repeat_rate observado. Destruir a ordem (shuffled) colapsa a métrica para
o nível do acaso. **Repetição cross-turn, nesta medição, é comportamento
correto — não patologia de retrieval.**

## PREDIÇÃO REFUTADA (registrada, não escondida)

O arquiteto previu, antes da rodada, que o binário real chegaria "perto
dos 80% do monitor histórico", o que confirmaria o H2-C de forma direta.
Deu **31,4%**. Predição REFUTADA. O gap de ~49pp entre o E7 e o monitor
não é explicado por este experimento.

## LIMITAÇÃO DESCOBERTA PÓS-DADO — o E7 é ANACRÔNICO

Identificada DEPOIS do resultado, e marcada como tal (não estava no
pré-registro, logo não é mérito do desenho):

O snapshot restaurado antes de cada turno é o **estado final** do store
(133 entries). O turno #3 consulta um store que já contém memórias
escritas no turno #100. Em produção o store CRESCE a cada turno, itens
recentes dominam o retrieve e a janela imediata/`seen_ids` opera — três
condições ausentes aqui.

**O que isso NÃO invalida:** o contraste real vs shuffled usa o MESMO
store nas duas condições, então o efeito da topicalidade está medido de
forma limpa. O veredito H1 permanece.

**O que fica sem base:** extrapolar de "topicalidade domina o gap" para
"topicalidade explica os 80% do monitor". A primeira está provada; a
segunda continua HIPÓTESE.

## Achados laterais

- **27 de 133 entries (20,3%) da episódica são `[session_summary]`** —
  uma em cada cinco. Evidência independente, por via write-side, da
  dominância que `DIAGNOSTICO_SESSION_SUMMARY.md` mediu no read-side.
- **As ordens sintéticas do exp017 subestimavam o fenômeno**: a sequência
  real (31,4%) dá mais que o DOBRO da ordem agrupada (15,4%), que era a
  melhor tentativa de mimetizar continuidade tópica. Agrupar queries por
  pool não reproduz continuidade conversacional.
- **O instrumento é estável entre corpora**: referência neutra do E7
  (5,5%) contra a do exp017 (6,6%), em conjuntos de query e stores
  diferentes.

## Desdobramento: E8 (pré-registro próprio, ainda não escrito)

Versão CRONOLÓGICA: cada turno consulta o store como ele estava naquele
instante (entries com timestamp ≤ o do turno), reproduzindo o crescimento
real. É a condição que testa se o gap E7↔monitor vem do anacronismo.
Requer desenho próprio — reconstruir estado histórico tem armadilhas
(consolidação, promoção, decay) que o E7 não enfrentou.
