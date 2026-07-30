# ACHADO — `EDP_WRITE_PROVENANCE` é ponto único de falha das defesas de toxicidade

Data: 29/07/2026. Origem: grep de verificação após o veredito do exp018
(`docs/VEREDITO_EXP018.md`), procurando a "terceira ocorrência" do padrão
guarda-sob-flag. Não é hipótese: os três pontos abaixo foram lidos na fonte,
em `edp_v5 @ 788d7f5` (branch `exp017/fase1-dedup`).

**A leitura inicial estava errada.** Não são "N ocorrências independentes de
um padrão ruim". É **uma flag só** governando o sistema inteiro de defesa
contra conteúdo tóxico, construído ao longo do arco exp012 → exp016.

## Os três pontos (file:line verificado)

**1. Piso `NOT_FOUND_FLOOR` — `edp/memory/store.py:572-573`**
```python
from ..config import EDP_WRITE_PROVENANCE as _WP, NOT_FOUND_FLOOR as _NF, TOXIC_ANSWER_CLASSES as _TAC
nf_floor = _NF if (_WP and e.get("answer_class") in _TAC) else 1.0
```
Com a flag OFF, o multiplicador vira `1.0` — a entry tóxica pontua com peso
cheio no caminho cosine.

**2. Exclusão do índice híbrido — `edp/memory/store.py:1455-1457`**
```python
from ..config import EDP_WRITE_PROVENANCE as _WP12, TOXIC_ANSWER_CLASSES as _TAC12
if _WP12 and e.get("answer_class") in _TAC12:
    continue
```
Com a flag OFF, o tóxico entra no índice BM25+vetorial.

**3. Guarda da consolidação — `edp/consolidation.py:290`**
```python
if EDP_WRITE_PROVENANCE and e.get("answer_class") in TOXIC_ANSWER_CLASSES:
```
Com a flag OFF, promove. **Medido**, não inferido: exp018 condição C4 →
4 de 4 entries tóxicas promovidas a `SemanticMemory`.

A flag é documentada como caminho de rollback em `edp/config.py:84`
("ROLLBACK: EDP_WRITE_PROVENANCE=0").

## Por que o argumento defensivo não se sustenta

A defesa natural do desenho é: "sem carimbo não há `answer_class` para
checar, logo acoplar a leitura à escrita é inócuo".

Falha no caso que importa: **o carimbo é persistido no disco**. Entries
marcadas antes do rollback continuam marcadas. Desligar a flag não apaga
carimbo nenhum — faz as três defesas **ignorarem carimbos que existem**.

## Cenário de falha concreto (é o que está na fila)

1. Backfill de produção roda (pendente — `ESTADO_EXP012.md:92,163-164`).
   N entries tóxicas ficam carimbadas no store real.
2. Algo não relacionado dá errado (latência, bug de escrita, qualquer coisa).
3. Alguém aplica o rollback documentado: `EDP_WRITE_PROVENANCE=0`.
4. As N entries carimbadas voltam a pontuar com peso cheio no cosine,
   entram no índice híbrido, e podem ser promovidas à semântica.

O rollback de uma feature de **escrita** desarma todas as defesas de
**leitura** construídas sobre o que ela escreveu.

## A única defesa que sobrevive ao rollback — e por que não basta

`filtro_recusa` (Dívida #49, `edp/memory/store.py:1459-1463`) NÃO está sob a
flag: roda com `if _recusa is not None:`, independente. É a única proteção
que continua ativa com `EDP_WRITE_PROVENANCE=0`.

E é justamente a **textual** — a Fase 0 do exp012 mediu essa família de
detecção vazando **3 de 6**. A defesa que sobrevive é a menos confiável do
conjunto.

## Desenho do fix — separar escrita de leitura

Duas responsabilidades compartilham uma variável. Separar:

- **`EDP_WRITE_PROVENANCE`** (default ON, mantém o nome e o papel de
  rollback): governa APENAS a escrita do carimbo `answer_class`.
- **`EDP_TOXIC_GUARDS`** (nova, default ON, independente): governa as três
  leituras — piso, exclusão híbrida, guarda de consolidação.

Custo: uma constante nova em `config.py` e a troca do nome nos três pontos
acima. Nenhuma mudança de lógica, nenhuma mudança de comportamento com os
defaults (ambas ON = comportamento atual, byte-idêntico).

Efeito: o rollback do carimbo para de escrever sem desarmar a proteção
sobre o que já foi escrito.

## Critério de aceitação — o exp018 já é o oráculo

Nenhum teste novo precisa ser escrito para validar este fix. Após a
separação, rodar o exp018 exatamente como está:

- **C4** (`consolidate_promote_only` com `EDP_WRITE_PROVENANCE=0`) deve cair
  de **4 → 0**, porque a guarda passa a depender de `EDP_TOXIC_GUARDS`, que
  continua ON.
- **C3** permanece 0 (não regride).
- **C1, C2** permanecem 4 e 4 — este fix NÃO os corrige; eles dependem dos
  itens 1 e 2 do fix triplo (guarda dentro de `consolidate()` e propagação
  de `answer_class` no merge). Se C1/C2 caírem só com esta mudança, algo
  inesperado aconteceu e vale investigar antes de seguir.

## Ordem (a mesma que o exp018 impôs)

Os três pontos são **dormentes** hoje: o store não tem carimbo
(`C:\edp_data_fase0`: 133/133 e 51/51 sem `answer_class`). O backfill de
produção os torna **ativos**.

**Este fix é pré-requisito do backfill**, junto com os três do
`VEREDITO_EXP018.md`. Quatro mudanças, um ciclo, antes de carimbar
produção.