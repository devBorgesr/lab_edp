# REL-001 — smoke de infraestrutura

**31/08/2026.** Item 3 das instruções de coleta. **Nenhum resultado aqui entra no
experimento.**

## O que rodou

3 pares — 1 por query, nas três primeiras do conjunto congelado.
Modelo `claude-haiku-4-5`, T=0, `sha256_system = c9b34b61…`.

| query (sha) | estrato | latência | formato |
|---|---|---|---|
| `030980c0e6f3` | topo | 11,38 s | ok |
| `0ad19bd7a8d7` | topo | 7,16 s | ok |
| `10308b8a0399` | cauda | 2,11 s | ok |

```
inclassificáveis .... 0 de 3     limite do §11: 10%
veredito ............ dentro do limite
```

**Conectividade, formato e parsing verificados.** Nenhum campo `relevant` foi
gravado — o arquivo do smoke não tem caminho para isso.

## O que este smoke NÃO diz

Não diz que o juiz é bom, nem que concorda com alguém. Diz que a chamada
completa — pool, embaralhamento, prompt, chamada, parse, classificação de falha
— funciona ponta a ponta e devolve o formato congelado.

Três pares são insuficientes para qualquer análise, **e isso é o desenho**.

## Projeção para a coleta, para a decisão de prosseguir

A latência cai de 11,4 s para 2,1 s entre a primeira e a terceira chamada —
aquecimento de conexão, não do modelo.

| | tempo do caminho B (500 pares) |
|---|---|
| a 7,2 s/par (sem aquecimento) | ~60 min |
| a 2,1 s/par (regime estável) | ~18 min |

Custo em ordem de grandeza: ~300k tokens de entrada, ~5k de saída. Em Haiku,
centavos de dólar. **O caminho A (humano) é o caro** — 500 julgamentos manuais.

## Estado

**PARADO.** A coleta principal não começa sem confirmação explícita (item 5).

Se ela for autorizada, a ordem do item 12 é: controle → topo → cauda → κ → IC
por bootstrap de query → AC1 → prevalência → veredito. E o controle roda
**primeiro**: se não atingir `ACORDO_ESPERADO_CONTROLE = 0.98`, a rodada é
inválida e nada depois dele é interpretado.
