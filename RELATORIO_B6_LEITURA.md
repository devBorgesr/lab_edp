# Relatório B6 — Leitura obrigatória (T1)

Lido ANTES de qualquer edição de código, conforme exigido pelo REPARO CENÁRIO B.
Achado confirmado ao vivo (não inferido):

```
$ python -m pytest -q
13 passed in 7.61s

$ python -c "from bancada.scorer import score_autoridade_004; score_autoridade_004()"
ImportError: cannot import name 'exp004' from 'bancada' (bancada/__init__.py)
```

O suite atual (13 testes) passa verde porque nenhum teste hoje *chama* as
funções quebradas — elas só explodem em uso real (`run_once.py --score-exp
004/006/006b/007` e `--audit-exp` correspondentes). Isso é exatamente o ponto
cego que a T5 fecha.

## a) Mapa de `bancada/scorer.py` (1037 linhas) — genérico vs específico

### GENÉRICO (fica em `bancada/scorer.py`)

| Símbolo | Linhas (antes) | Nota |
|---|---|---|
| `_ACCEPT_SET`, `set_accept_set` | 32–38 | injeção do accept-set (padrão do relógio) |
| `_normalize` | 42–47 | renomeia para `normalize` (pública — T3) |
| `score_fidelity` | 50–53 | |
| `_RUIDO_TERMOS`, `_INCERTEZA`, `_HORARIO_RE`, `extract_signals` | 57–78 | sinais exploratórios §8, do 001, mas não referencia nenhum expNNN |
| `_wilson` | 82–89 | renomeia para `wilson` (pública — T3) |
| `CondicaoFidelidade` (dataclass) | 93–102 | |
| `ScorerResultado` (dataclass) | 105–120 | |
| `score_prontuario` | 123–207 | genérico, parametrizado por `experimento` (001/003) |
| `report` (morta, 1ª definição) | 210–216 | **REMOVER** — sombreada pela 2ª (linha 218), nunca executa |
| `report` (2ª definição, a que vale) | 218–272 | fica, sem mudança de corpo |
| `valor_concluido` | 816–835 (embutida no meio da seção "006b" original, mas genérica: recebe `valores_fn`) | fica; consumida por 007 e 006b |

### ESPECÍFICO (sai para `sujeitos/edp/analise/`)

| Símbolo | Linhas (antes) | Destino | Nota |
|---|---|---|---|
| `CamadaAutoridade` (dataclass) | 279–285 | `analise_004.py` | **não estava listada na T2** — é consumida por `Autoridade004`, `Eco006` **e** `DataPosicao006b`. Ver decisão de desenho abaixo. |
| `Autoridade004`, `score_autoridade_004`, `report_004`, `audit_004` | 288–460 | `analise_004.py` | usa `from . import exp004` quebrado nas linhas 308, 432 |
| `Eco006`, `_coleta_006`, `score_eco_006`, `_tab`, `report_006`, `audit_006` | 466–647 | `analise_006.py` | `from . import exp006` quebrado nas linhas 484 (import morto, nunca usado dentro de `_coleta_006`), 510, 626 |
| `CondSeg` (dataclass), `Seguranca007`, `score_seguranca_007`, `report_007`, `audit_007` | 653–800 | `analise_007.py` | **`CondSeg` também não estava listada na T2** — é o tipo de `Seguranca007.condicoes`. `from . import exp007` quebrado nas linhas 681, 773 |
| `_H4_MARCADORES`, `_tem_marcador_h4`, `valor_concluido_006b`, `CondDP`, `DataPosicao006b`, `_classifica_cond_006b`, `score_data_posicao_006b`, `report_006b`, `audit_006b` | 808–1037 | `analise_006b.py` | `from . import exp006b` quebrado nas linhas 840, 878 (import morto, nunca usado dentro de `_classifica_cond_006b`), 897, 1005 |

**Decisão de desenho (gap na especificação da T2):** `CamadaAutoridade` e
`CondSeg` não apareceram na lista de símbolos de nenhum módulo do T2, mas são
tipos exigidos pelos dataclasses de resultado. `CondSeg` é usada só dentro de
`analise_007.py` — vai para lá sem ambiguidade. `CamadaAutoridade` é
compartilhada por 004, 006 e 006b — resolvida por analogia ao padrão **já
existente** no próprio repo (`exp006.py`/`exp006b.py` fazem `from .exp004
import valor_unico, valores_na_resposta` — sujeito reaproveitando sujeito):
`CamadaAutoridade` é definida em `analise_004.py` e importada por
`analise_006.py`/`analise_006b.py` (`from .analise_004 import
CamadaAutoridade`). Nenhuma duplicação de corpo — import, não cópia.

Os 12 `from . import expNNN`/lazy-imports quebrados desaparecem: viram import
de módulo (`from ..experimentos import expNNN`) no topo de cada
`analise_00X.py`, como pede a T2. Dois deles (linha 484 de `_coleta_006` e
878 de `_classifica_cond_006b`) eram *mortos* — importavam o módulo e nunca o
usavam dentro daquela função especificamente (pyflakes confirma: `'.exp006'
imported but unused`, `'.exp006b' imported but unused`) — o uso real
acontecia nas outras funções da mesma seção, que já tinham seu próprio import
lazy repetido. Isso desaparece de graça ao virar import único de módulo.

## b) Interface consumida — confirmada por leitura de
`sujeitos/edp/experimentos/exp004.py`, `exp006.py`, `exp006b.py`, `exp007.py`

- **exp004**: `mapa_da_condicao(rotulo) -> Dict[str,str]`,
  `camada_do_valor(mapa, valor) -> Optional[str]`,
  `valores_na_resposta(texto) -> Set[str]`, `valor_unico(texto) ->
  Optional[str]`. Todas definidas localmente em `exp004.py`.
- **exp006**: `meta_da_condicao(rotulo) -> (maioria, recencia, tipo)`.
  `valor_unico`/`valores_na_resposta` **reaproveitados de exp004** via `from
  .exp004 import valor_unico, valores_na_resposta  # noqa: F401` (linha 18 —
  já tem o noqa).
- **exp006b**: `meta_da_condicao(rotulo) -> (valor_data_nova,
  valor_ultima_posicao, tipo)`. `valor_unico`/`valores_na_resposta`
  reaproveitados de exp004 via `from .exp004 import valor_unico,
  valores_na_resposta` (linha 15 — **sem** noqa ainda; pyflakes acusa unused;
  T3 pede para acrescentar).
- **exp007**: `tipo_da_condicao(rotulo) -> str`, `valores_na_resposta(texto)
  -> Set[str]`, `valor_unico(texto) -> Optional[str]`. **Não** reaproveita de
  exp004 — define os três localmente.

Confirmado por `pyflakes`:
```
sujeitos/edp/experimentos/exp006.py:18:1: '.exp004.valor_unico' imported but unused
sujeitos/edp/experimentos/exp006.py:18:1: '.exp004.valores_na_resposta' imported but unused
sujeitos/edp/experimentos/exp006b.py:15:1: '.exp004.valor_unico' imported but unused
sujeitos/edp/experimentos/exp006b.py:15:1: '.exp004.valores_na_resposta' imported but unused
```
(pyflakes não respeita `# noqa` — só flake8 respeita; por isso exp006 aparece
"unused" mesmo já tendo o noqa. Confirma que o noqa em exp006b é o que falta.)

## c) Achado que decide o desenho — CONFIRMADO

```python
# exp004.py
VALORES = ("14h30", "15h", "16h")
VALOR_REGEX = {"14h30": ..., "15h": ..., "16h": ...}

# exp007.py
VALOR_REGEX = {"14h30": ..., "18h": ...}
```

Mesma assinatura (`valores_na_resposta(texto) -> Set[str]`, `valor_unico(texto)
-> Optional[str]`), semânticas **distintas** por experimento — 004 discrimina
autoridade entre 3 valores neutros; 007 discrimina sequestro (14h30 legítimo
vs. 18h malicioso injetado). Isso é o que **proíbe** um scorer único
genérico-por-nome: cada `score_*` precisa do detector do seu próprio
experimento, nunca do de outro. exp006/exp006b reaproveitam o detector do 004
porque usam os mesmos dois valores (14h30/15h); exp007 não pode, porque usa
um par diferente (14h30/18h). Confirma que mover cada `score_*`/`audit_*`
para o pacote do seu próprio experimento (e deixar exp006/006b importarem de
exp004 como já fazem) é o desenho certo — não dá para generalizar por cima
sem perder a distinção semântica.

## d) Método de referência — `edp_v5`, Fase 4 (`RELATORIO_FASE4.md`)

Lido em `/mnt/edp_v5_main/RELATORIO_FASE4.md` (montagem local do repo
`edp_v5`, branch `hardening/fase4-memoria-e-clock`) — split de `memory.py`
(1991 linhas) em pacote `edp/memory/` (`atomic_io.py`, `semantic.py`,
`store.py`, `__init__.py`). Padrão a replicar aqui, **não o código**:

- Gate: pytest completo verde após cada commit, sem push, sem PR.
- Tabela explícita **linha-de-origem → módulo-destino** antes de mover
  qualquer coisa (replicada acima, seção a).
- MOVE-ONLY: nenhuma "melhoria de passagem" — só o corte de arquivo.
- **Choke-point documentado**: quando duas peças têm que ficar juntas por uma
  restrição real (no edp_v5, `NOT_FOUND_FLOOR` e a exclusão do índice híbrido
  tiveram que ficar adjacentes no mesmo arquivo — o corte proposto original
  em `episodic.py` separado foi **proibido** pela restrição, e isso foi
  documentado explicitamente no relato, não escondido). Aqui o choke-point
  análogo é `CamadaAutoridade`: não pode ser triplicada em 004/006/006b nem
  fica na bancada (não está na lista de primitivos da T3) — mora em
  `analise_004.py` e é importada pelos outros dois, documentado acima.
- ALERTA sobre nomes vinculados por import (`from X import Y` cria uma cópia
  do nome no módulo importador, não uma referência viva) — não se aplica
  aqui da mesma forma (não há injeção de clock/base_dir por módulo neste
  split), mas o princípio de "cada módulo que importa `expNNN` importa o
  módulo inteiro, não os símbolos soltos" evita essa classe de problema.
- Medição antes/depois reportada mesmo quando não bate a meta ideal —
  reportar o número real, não maquiar.
- Termina com `PARAR.`

## GATE DE PARADA — avaliado, NÃO disparado

- (c) confirmado: os `VALOR_REGEX` de exp004 e exp007 divergem. Desenho
  segue como especificado na T2.
- Nenhuma dependência entre as funções específicas (`score_autoridade_004`,
  `score_eco_006`, `score_seguranca_007`, `score_data_posicao_006b`) e estado
  interno de `bancada/` foi encontrada além de `get_prontuario()` (função
  pública, já usada do jeito certo) e `_wilson`/`valor_concluido`
  (primitivos que a própria T3 manda exportar publicamente). Nenhuma delas
  toca `_ACCEPT_SET`, `_store` (singleton do prontuário) ou qualquer outro
  estado privado de `bancada/`. **Não há motivo para parar** — prosseguindo
  para T2.

## Decisão de nomenclatura sinalizada (não é gate, é uma nota para o
pesquisador conferir)

A T3 lista os primitivos a exportar como "..., `ScorerResultado`,
`CondResultado`, `set_accept_set`". Não existe (e nunca existiu) uma classe
`CondResultado` em `bancada/scorer.py` — a classe correspondente
(`condição` + `resultado de fidelidade`) chama-se `CondicaoFidelidade` desde
a origem (linha 94), e é a única classe cujo "renomear de X" **não** foi
anotado explicitamente (ao contrário de `_wilson`→`wilson` e
`_normalize`→`normalize`, que vieram com a nota entre parênteses). Tratado
como nome já correto/já público (não tem underscore, já é exportável) —
mantido `CondicaoFidelidade` sem renomear. Se a intenção era
`CondicaoFidelidade` → `CondResultado`, é uma troca de nome de baixo risco
(só usada dentro de `score_prontuario`/`report`, que ficam juntas em
`bancada/scorer.py`) e trivial de aplicar depois.
