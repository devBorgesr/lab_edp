# Proveniência — lab_edp vs `edp/lab/` no edp_v5

FASE C, T4. `edp_v5` (https://github.com/devBorgesr/edp_v5) é **read-only**
nesta análise — nada nele foi alterado; tudo abaixo vem de leitura do clone
montado localmente (`edp_v5` @ `788d7f5`, branch `exp017/fase1-dedup`).

## Declaração de proveniência

**`lab_edp` é o canônico daqui em diante** para a Bancada de Contexto
(prontuário, isolamento, scorer, sampler, repeater, rodízio, auditoria) e
para os experimentos que ela roda. **`edp/lab/` dentro de `edp_v5` é
ancestral congelado**: o ponto de onde `lab_edp` foi extraído (`git subtree
split -P edp/lab`, citado no `README.md` deste repo), preservado ali como
histórico, não como um segundo lugar de desenvolvimento ativo. Mudanças na
Bancada acontecem em `lab_edp`; `edp/lab/` no `edp_v5` não recebe mais
commits pela disciplina desta bancada.

## As duas cópias, verificadas lado a lado

| | `edp_v5` → `edp/lab/` (ancestral) | `lab_edp` (canônico) |
|---|---|---|
| Layout | **flat**: 21 arquivos (código + 3 `.md` de pré-registro) num único pacote `edp/lab/` | **dividido**: `bancada/` (agnóstico de sujeito) + `sujeitos/edp/experimentos/` (código específico do EDP) + `docs_edp_v5/` (`.md`), separados na FASE B2 |
| `scorer.py` | funciona: `from . import exp004/exp006/exp006b/exp007` resolve porque `exp004.py` etc. são **irmãos de pasta** de `scorer.py` no mesmo `edp/lab/` | **era o bug da FASE B6**: os mesmos `from . import expNNN` foram copiados byte-a-byte para `bancada/scorer.py` na B2, mas `bancada/` e `sujeitos/edp/experimentos/` são pacotes **separados** — `exp004` nunca existiu dentro de `bancada/`. `ImportError` garantido, só corrigido na FASE B6 (`sujeitos/edp/analise/`) |
| `isolation.py` / `window_formats.py` | nomes em inglês | renomeados para `isolamento.py` / `formatos.py` (pt-BR, consistente com o resto do código) |
| `run_once.py` | dentro do próprio `edp/lab/` (a "porta" mora junto do núcleo) | movido para `sujeitos/edp/experimentos/run_once.py` — reflete a separação bancada/sujeito: a porta que dispara contra o EDP de verdade é conhecimento de sujeito, não do núcleo agnóstico |
| Pré-registros (008/009/010) | 3 arquivos `.md` **dentro** de `edp/lab/`, junto do código | movidos para `docs_edp_v5/` — documentação separada de código |
| Protocolo `Sujeito` (`bancada/sujeito.py`) | **não existe** — `edp/lab/` fala diretamente com `edp.*`, sem abstração | existe desde a FASE B3: é o que permite `bancada/` nunca importar `edp.*`/`sujeitos.*` (invariante travado em `tests/test_fronteira.py`) |
| `auditoria.py` (auditoria offline de retrieval JSONL) | não existe em `edp/lab/` | adicionado na FASE B4, nativo de `lab_edp` |
| Import de `exp001` no scorer | `from . import exp001` no **topo do módulo** (linha 23) — eager, funciona pelo mesmo motivo (irmão de pasta) | não se aplica — `lab_edp` nunca teve essa linha; a bancada é agnóstica por design desde a B2 |

## A causa-raiz, em uma frase

`edp/lab/` nunca teve um bug de import porque nunca separou "o que é
genérico" de "o que é do EDP" — tudo mora no mesmo pacote. `lab_edp` fez
essa separação (o ponto do projeto: uma bancada reusável para *qualquer*
sujeito, não só o EDP) e a separação, feita na FASE B2 sem atualizar os 11
`from . import expNNN`, é exatamente onde o bug nasceu. O ancestral não
tinha o bug porque não tinha a arquitetura que o `lab_edp` existe para ter.

## O que isso implica daqui pra frente

- Achados/lições metodológicas do `edp_v5` (`edp_metodologia.md`,
  `MARCOS_EPISTEMICOS.md`, `DIVIDAS.md` — importados na T1) continuam
  valendo como referência histórica e de método.
- Código de `edp/lab/` no `edp_v5` **não deve ser copiado** para `lab_edp`
  daqui pra frente — se algo de lá for útil, é **reimplementado** contra a
  arquitetura atual (`bancada/` + `sujeitos/`), não colado.
- Divergência futura entre as duas cópias é esperada e aceita: `edp/lab/`
  fica congelado no estado do subtree split; `lab_edp` evolui.
