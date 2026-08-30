# Achado — a consolidação não remove da episódica, e o índice conta o mesmo documento duas vezes

**30/08/2026.** Encontrado ao verificar itens do ranking que eu **não** tinha
checado no REL-001A — o auditor externo listou "IDs únicos?" e eu só tinha
verificado o tamanho do ranking.

Tier **D (medido)**.

---

## 1. O número

Ranking de 50 posições, 50 queries reais, retriever de produção:

```
ids duplicados no ranking ......... 637 em 2.500 slots  (25,5%)
textos duplicados ................. 692
documentos com texto vazio ........   0
média por query ................... 12,7 ids repetidos de 50
```

**O mesmo documento, com o mesmo `id`, aparece várias vezes no top-50 de uma
única query.** Isso não é duplicata de conteúdo — é a mesma entrada devolvida
mais de uma vez.

## 2. A causa

```
ids em episodic ........ 137
ids em semantic .........  61
ids nos DOIS ............  61   ← 100% da semântica
documentos distintos .... 137
entradas no índice ...... 198
```

**Todos os 61 ids da camada semântica também estão na episódica.** A
consolidação promove a entrada para `semantic` e **não a remove** de `episodic`.

E `_hybrid_index` (`store.py:1649`) varre as duas camadas sem deduplicar por id:

```python
for layer, pool in (("episodic", epi), ("semantic", sem)):
    for e in pool:
        ...
        entries_kept.append(e)
```

Resultado: **31% das entradas do índice são o mesmo documento contado duas
vezes**, e cada uma pode ganhar seu próprio lugar no ranking.

## 3. Isto CORRIGE uma atribuição minha

O `ACHADO_DUPLICATA_EXPLICA_DOMINANCIA.md` (19/08) explicou a duplicação inteira
por uma causa só: `session_summary` geradas a cada `WebSocketDisconnect`,
produzindo **texto igual com ids diferentes**.

Aquilo está certo e continua valendo. Mas é **uma** das causas, não a causa.

| | mecanismo | assinatura |
|---|---|---|
| **causa 1** (19/08) | resumo regravado a cada disconnect | texto igual, **ids diferentes** |
| **causa 2** (hoje) | consolidação não remove da episódica | **id igual**, indexado 2× |

E o instrumento já separava as duas o tempo todo. O `dup_rate` do exp017 emite
`id=` e `hash=` **em campos distintos**:

```
00:48  id=0/5 hash=4/5     ← causa 1 pura
00:51  id=2/5 hash=2/5     ← causa 2
01:17  id=1/3 hash=1/3     ← causa 2
```

Eu li `hash=4/5` como o fenômeno e tratei `id=` como ruído. Os dois campos
existem exatamente porque o exp017 já sabia que eram fenômenos diferentes — o
`_dedup_pass_exp017` faz **duas passadas**, uma por id e outra por hash, e o
docstring dele diz *"colapsa fenômeno D"* e *"fenômeno A-no-resultado"*.

**A informação estava no instrumento e no nome das variáveis. Eu não li.**

## 4. Consequência para o REL-001

`monta_pool` fatia `ranking[:5]` como `topo` e `ranking[19:50]` como `cauda`. Com
ids repetidos:

- o `topo` pode ter menos de 5 documentos distintos;
- o **mesmo documento** pode cair em `topo` e em `cauda` — e o julgador o
  avaliaria duas vezes, com o par entrando duas vezes no κ;
- a prevalência do estrato do gate fica distorcida por peso indevido.

Medido: **1 caso** de texto do topo reaparecendo na cauda nas 50 queries. Baixo,
mas não zero, e o efeito no κ não é desprezível quando o estrato tem 250 pares.

Correção no harness: deduplicar o ranking por id **antes** de fatiar. Isso não
altera o protocolo — o `§3.2` diz "top-5 do retriever", e cinco slots com quatro
documentos distintos nunca foram cinco.

## 5. Consequência para produção — declarada, não consertada aqui

**Não** estou tocando em `_hybrid_index`. Remover a duplicação do índice muda o
conjunto recuperado em todo turno, e isso é `FORMAT_STATE_FLAGS`: precisa de
flag, de pré-registro e de medição antes/depois. Este documento registra o
achado; o conserto é ciclo próprio.

Vale notar que o `_dedup_pass_exp017` **já colapsaria** isso na primeira passada
(por id) — e continua desligado (`_mode = "off"`).

## 6. O que este achado NÃO estabelece

- **Não** mede o efeito na qualidade da resposta. Mede que 25,5% dos slots do
  ranking são repetição de id.
- **Não** diz que a consolidação está errada em promover — diz que promover sem
  remover, combinado com um índice que varre as duas camadas, conta duplo.
- **Não** cobre o store vivo de hoje: o snapshot é de 18/08 12:14.
