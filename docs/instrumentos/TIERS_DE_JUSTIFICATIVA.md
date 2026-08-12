# Instrumento — tiers de justificativa para constantes de ajuste

**Agnóstico de sujeito.** Serve para auditar qualquer base de código que
tenha número mágico decidindo corte, peso ou classificação. Extraído de uma
auditoria do EDP em 2026-08-12 (`docs/sujeito_edp/AUDITORIA_CONSTANTES_NAO_CALIBRADAS.md`),
mas nada aqui depende do EDP.

---

## O problema que ele resolve

A pergunta ingênua — "esta constante é calibrada?" — tem duas respostas e
as duas enganam. "Não" acusa código que tem argumento formal legítimo.
"Sim" absolve código que só tem um comentário simpático.

O erro de fundo é achatar duas coisas diferentes: **ter explicação** e
**ter evidência**. Um comentário longo e convincente ao lado de um número
não é medição.

---

## Os quatro tiers

| tier | critério de admissão | o que se pode afirmar |
|---|---|---|
| **D — Medido** | existe experimento pré-registrado, com dado real e número citável, e a citação está no código ou a um link de distância | o valor foi comparado contra alternativas |
| **C — Argumentado** | derivado de identidade matemática ou princípio declarado, com a derivação escrita — mas nunca confrontado com dado do sistema real | a escolha é principiada; **não** que é a melhor |
| **B — Anedótico** | uma frase de intenção, e a evidência é **um caso** ("corrige o incidente X") ou "empata com Y" | alguém teve um motivo; a amostra é 1 |
| **A — Nu** | literal solto, zero comentário sobre origem | nada |

Tiers C e D não são o alvo. Eles entram na tabela para mostrar que o
projeto **sabe** fazer isso quando quer — o que torna o volume de tier A
significativo, não desculpável.

---

## As três regras que fazem o instrumento funcionar

**1. Cadeia de "empata com X" não sobe de tier.**
Se `a = 1.20` é tier A e alguém define `b = 1.20  # empata com a`, então
`b` também é tier A. Encadear a partir de um número não medido não produz
número medido — produz o mesmo número não medido replicado, com aparência
de consenso. Esta é a regra que mais achado gera na prática, porque a
cadeia parece justificativa.

**2. Comentário que explica o CONCEITO não justifica o VALOR.**
"Memória hiperdominante leva multiplicador, não bloqueio" explica por que
existe um multiplicador. Não explica por que `0.70` e não `0.60`. Ao
classificar, separe as duas perguntas e responda só a segunda.

**3. A palavra "calibrado" no comentário não é evidência.**
Quando o comentário diz "calibrado em <data>", vá ver o que houve naquela
data. Se foi um incidente observado, é tier B — a palavra é mais forte que
o processo por trás dela.

---

## Método de varredura

Duas passadas de grep e uma de leitura:

```bash
# 1. constantes nomeadas
grep -rnE '\b[A-Z_]*(THRESH|WEIGHT|FACTOR|BOOST|BIAS|ALPHA|BETA|GAMMA|DECAY|RATIO|CUTOFF|MARGIN|PENALTY|BONUS|SCALE|COEF|WINDOW|CAP|LIMIT)[A-Z_]*\s*[:=]\s*[0-9]' <dir>

# 2. literais inline (os que escapam da passada 1)
grep -rnE '(^|[^0-9a-zA-Z_])[a-z_]*(thresh|weight|factor|boost|penalty|ratio)[a-z_]*\s*[:=]\s*[0-9]' <dir>
```

A terceira passada não é automatizável: **ler o comentário acima e abaixo
de cada achado** é o que decide o tier. Sem isso a varredura só conta
números.

**Limite declarado do método:** ele acha o que o padrão de nome captura.
Uma constante chamada `X` em vez de `X_THRESHOLD` não aparece. A contagem
resultante é piso, nunca total — relate-a como piso.

---

## Dois achados que a varredura tende a produzir, e que valem procurar

**Constante nomeada e desconectada dos seus call sites.** O projeto define
`PARAM = env("X", "0.65")` num módulo de config, e os lugares que usam o
valor escrevem `0.65` na mão. A variável de ambiente vira mentira parcial:
mexer nela muda parte do sistema, em silêncio. Grep pelo *valor*, não só
pelo nome, para achar isto.

**Mesma constante definida duas vezes, concordando por coincidência.** Dois
módulos declaram `GAP = 4 * 3600` independentemente. Hoje concordam. Nada
force a concordância — recalibrar um e esquecer o outro não dá erro, dá
resultado diferente conforme o caminho de código que rodou.
