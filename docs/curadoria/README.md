# Curadoria do ecossistema EDP

| documento | o que traz |
|---|---|
| [INVENTARIO_ECOSSISTEMA.md](INVENTARIO_ECOSSISTEMA.md) | **Fase 1** — inventário estrutural: repos, módulos, LOC, mortos |
| [MAPA_CAPACIDADES.md](MAPA_CAPACIDADES.md) | **Fase 2** — 21 capacidades com ficha e maturidade |
| [MAPA_FLAGS.md](MAPA_FLAGS.md) | as 12 flags desligadas, uma a uma |
| [MAPA_PROVENIENCIA.md](MAPA_PROVENIENCIA.md) | matriz EDP × MVP, duplicação e unificação |
| [CANDIDATOS_ACOPLAMENTO_MVP.md](CANDIDATOS_ACOPLAMENTO_MVP.md) | o que acopla, quando, e se muda a régua |
| [CANDIDATOS_NOVOS_SERVICOS.md](CANDIDATOS_NOVOS_SERVICOS.md) | 3 serviços com capacidade concreta |
| [LACUNAS_E_NAO_VERIFICADO.md](LACUNAS_E_NAO_VERIFICADO.md) | 7 itens não apurados, e o que mudaria |

## Resumo executivo

```
CAPACIDADES ENCONTRADAS ........ 21
ACOPLÁVEIS AGORA ...............  3
ACOPLÁVEIS DEPOIS DO PILOTO ....  4
PRECISAM DE TESTE ..............  6
PRECISAM DE EXPERIMENTO ........  2
NOVOS SERVIÇOS CANDIDATOS ......  3
NÃO VERIFICADAS ................  7
```

## A regra que estrutura tudo

```
EXISTE < EXECUTADO < TESTADO < VALIDADO < REUTILIZÁVEL < PRONTO P/ PRODUÇÃO
```

Não são sinônimas, e a curadoria não converte:

```
módulo existe   ≠  feature pronta
flag existe     ≠  feature funcionando
teste existe    ≠  produção pronta
código grande   ≠  software maduro
```

**Nenhuma capacidade do kernel está em `VALIDADA`.** O máximo alcançado é
`TESTADO` — que é mais do que a maioria dos códigos, e menos do que pronto.

## As três coisas que a Fase 2 achou e a Fase 1 não

1. **Os 12 emissores de evento do `pareto_store`** formam uma camada de
   observabilidade coerente, com JSONL append-only e `correlation_id` — não
   são flags soltas.
2. **`window_formats` é uma bateria de perturbação de contexto** (ablação,
   lost-in-middle, âncora envenenada). Nada equivalente existe no MVP, e é a
   base do único serviço candidato que mediria NÍVEL 3.
3. **`isolation.verify_no_leak` resolve o mesmo problema que o MVP resolve por
   cópia + hash.** Duas soluções para "não contaminar o auditado", construídas
   separadamente — e a do kernel não tem teste.
