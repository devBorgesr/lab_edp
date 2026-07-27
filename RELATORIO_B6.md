# Relatório B6 — Reparo dos imports quebrados de `bancada/scorer.py`

Ver `RELATORIO_B6_LEITURA.md` para a leitura obrigatória (T1) que precedeu
qualquer edição de código. Este relatório cobre T2–T8. Commits separados por
T, gate `pytest` verde depois de cada um, sem push.

## Achado confirmado (reproduzido ao vivo antes de qualquer edição)

```
$ python -c "from bancada.scorer import score_autoridade_004; score_autoridade_004()"
ImportError: cannot import name 'exp004' from 'bancada' (bancada/__init__.py)
```

`bancada/scorer.py` tinha `from . import expNNN` em 11 pontos (não 12 — ver
nota de contagem abaixo), resolvendo dentro de `bancada/` — pacote que nunca
teve `exp004`/`exp006`/`exp006b`/`exp007`. `ImportError` garantido em
`score_autoridade_004`, `audit_004`, `score_eco_006`, `audit_006`,
`score_seguranca_007`, `audit_007`, `score_data_posicao_006b`, `audit_006b` —
os 8 caminhos alcançáveis via `run_once.py --score-exp`/`--audit-exp`.

O fix ingênuo (apontar para `sujeitos.edp.experimentos`) foi rejeitado:
`tests/test_fronteira.py` lista `"sujeitos"` em `NOMES_PROIBIDOS` — a bancada
não pode importar sujeito. Resolvido movendo o código para dentro de
`sujeitos/`, não trazendo `sujeitos` para dentro de `bancada/`.

## Tabela origem → destino (T2 + T3)

| Símbolo | Origem (`bancada/scorer.py`, antes) | Destino |
|---|---|---|
| `CamadaAutoridade`, `Autoridade004`, `score_autoridade_004`, `report_004`, `audit_004` | linhas 279–460 | `sujeitos/edp/analise/analise_004.py` |
| `Eco006`, `_coleta_006`, `score_eco_006`, `_tab`, `report_006`, `audit_006` | linhas 466–647 | `sujeitos/edp/analise/analise_006.py` (`CamadaAutoridade` importada de `analise_004.py`) |
| `CondSeg`, `Seguranca007`, `score_seguranca_007`, `report_007`, `audit_007` | linhas 653–800 | `sujeitos/edp/analise/analise_007.py` |
| `_H4_MARCADORES`, `_tem_marcador_h4`, `valor_concluido_006b`, `CondDP`, `DataPosicao006b`, `_classifica_cond_006b`, `score_data_posicao_006b`, `report_006b`, `audit_006b` | linhas 808–1037 | `sujeitos/edp/analise/analise_006b.py` (`CamadaAutoridade` importada de `analise_004.py`) |
| `wilson` (de `_wilson`), `normalize` (de `_normalize`), `score_fidelity`, `extract_signals`, `valor_concluido`, `score_prontuario`, `report`, `ScorerResultado`, `CondicaoFidelidade`, `set_accept_set` | espalhados, genéricos | **ficam** em `bancada/scorer.py`, públicos |
| `report` (1ª definição, morta — sombreada pela 2ª) | linhas 210–216 | **removida** |

Corpos das funções movidas são byte-idênticos, com um único ajuste
sistemático: os 11 `from . import expNNN` (lazy, dentro de cada função)
desaparecem — viram import de módulo no topo de cada `analise_00X.py`
(`from ..experimentos import expNNN`), como pedido na T2. Dois desses 11
imports (dentro de `_coleta_006` e `_classifica_cond_006b`) já eram mortos
no original (pyflakes confirmou antes da edição: `'.exp006' imported but
unused`, `'.exp006b' imported but unused`) — o uso real acontecia nas outras
funções da mesma seção.

**Nota de contagem**: a T0 do reparo falou em "12 call-sites"; o AST (e o
teste novo da T5, rodado contra o código pré-B6) encontrou exatamente 11
linhas de import distintas (308, 432, 484, 510, 626, 681, 773, 840, 878, 897,
1005), cada uma importando 1 nome. Correção factual registrada, sem impacto
no reparo.

**Gaps na especificação da T2, resolvidos e documentados (ver leitura, T1)**:
`CamadaAutoridade` (compartilhada por 004/006/006b) e `CondSeg` (usada só por
007) não estavam na lista de símbolos de nenhum módulo — são os tipos dos
campos de resultado dos dataclasses. `CondSeg` foi para `analise_007.py` sem
ambiguidade (uso exclusivo). `CamadaAutoridade` foi para `analise_004.py` e é
importada por `analise_006.py`/`analise_006b.py` — mesmo padrão que já existe
no repo (`exp006.py`/`exp006b.py` importam `valor_unico`/`valores_na_resposta`
de `exp004.py`; sujeito reaproveitando sujeito, permitido).

## O teste que fecha o ponto cego (T5)

`tests/test_fronteira.py::test_bancada_nao_importa_sujeito_nenhum` (FASE B5)
só barra `NOMES_PROIBIDOS`; imports relativos de nível 1 (`from .X import Y`,
permitidos dentro do próprio pacote `bancada/`) eram pulados com `continue`
sem checar se o alvo existe — foi esse ponto cego que deixou os 11 imports
quebrados passarem no B5.

Novo teste: `test_imports_relativos_de_bancada_apontam_para_arquivo_existente`
— para todo `from .X import ...` ou `from . import X` em `bancada/`, confere
que `bancada/X.py` (ou `bancada/X/__init__.py`) existe em disco.

**Prova de que pega o bug** (reproduzida ao restaurar temporariamente
`bancada/scorer.py` do commit `4f2268e`, antes de qualquer trabalho da B6, e
depois devolvido ao estado corrigido):

```
$ git show 4f2268e:bancada/scorer.py > bancada/scorer.py   # temporario
$ python -m pytest tests/test_fronteira.py::test_imports_relativos_de_bancada_apontam_para_arquivo_existente -q
FAILED — 11 violações, uma por linha (308, 432, 484, 510, 626, 681, 773, 840, 878, 897, 1005),
todas "aponta para 'expNNN', mas nem bancada/expNNN.py nem bancada/expNNN/__init__.py existem"
$ <restaurado o scorer.py corrigido>
$ python -m pytest tests/test_fronteira.py -q
3 passed
```

## Contagem de testes antes/depois

| Momento | `pytest -q` |
|---|---|
| Antes da B6 (baseline, T1) | **13 passed** |
| Depois da T5 (novo teste de fronteira) | **14 passed** |
| Depois da T6 (regressão dos 4 scorers, 8 testes novos) | **22 passed** |
| Final (T7, T8) | **22 passed** |

## Os 8 comandos de `run_once.py` que voltaram a funcionar

Antes: `ImportError: cannot import name 'expNNN' from 'bancada'` em todos.
Depois (rodado ao vivo, prontuário vazio no ambiente de dev — sem exceção,
saída correta de "0/0" e "setup SUSPEITO", que é o comportamento esperado
para prontuário vazio, não um erro):

```
python -m sujeitos.edp.experimentos.run_once --audit-exp 004
python -m sujeitos.edp.experimentos.run_once --audit-exp 006
python -m sujeitos.edp.experimentos.run_once --audit-exp 007
python -m sujeitos.edp.experimentos.run_once --audit-exp 006b
python -m sujeitos.edp.experimentos.run_once --score --score-exp 004
python -m sujeitos.edp.experimentos.run_once --score --score-exp 006
python -m sujeitos.edp.experimentos.run_once --score --score-exp 007
python -m sujeitos.edp.experimentos.run_once --score --score-exp 006b
```

CLI idêntica: mesmas flags (`--help` inalterado), mesma saída de formato.

## Commits (branch `main`, sem push)

1. `73fe522` — T1: leitura obrigatória, `RELATORIO_B6_LEITURA.md`
2. `977d945` — T2: novo pacote `sujeitos/edp/analise/` (move-only)
3. `cb3faa3` — T3: `bancada/scorer.py` só com o genérico, primitivos públicos
4. `9298c9e` — T4: `run_once.py` aponta para `sujeitos.edp.analise`
5. `e305a50` — T5: fecha o ponto cego de `tests/test_fronteira.py`
6. `ebbc19b` — T6: regressão dos 4 scorers (8 testes novos)
7. `89819fe` — T7: `LICENSE` (MIT) + `README` aponta fronteira e licença
8. (este commit) — T8: `RELATORIO_B6.md`

## Fora de escopo (não tocado, por decisão de escopo)

- Renome de `CondicaoFidelidade` → `CondResultado`: a T3 citou este nome mas
  a classe nunca se chamou assim no código (única classe da lista sem um
  "renomear de X" explícito, ao contrário de `wilson`/`normalize`) — ver nota
  detalhada em `RELATORIO_B6_LEITURA.md`. Mantido o nome original;
  troca de baixo risco se a intenção era outra.
- `prompt1.md` na raiz: arquivo pré-existente, não criado nesta sessão, não
  tocado.
- `docs_edp_v5/`, `edp_split`, `edp_v5_main`: material de referência,
  read-only por instrução da T1(d).

---

PARAR.
