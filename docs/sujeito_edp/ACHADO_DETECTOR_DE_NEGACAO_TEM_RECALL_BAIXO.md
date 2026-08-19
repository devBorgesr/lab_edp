# Achado — o detector que decide quarentena tóxica perde ~3 de cada 4 negações

**19/08/2026.** Investigação que começou pequena — *"o `camara_response` armazena
falha sem `answer_class`?"* — e terminou num defeito de produção maior que a
pergunta.

Tier **D (medido)** para as contagens. Tier **C** para a taxa de recall, porque
o denominador vem de um padrão amplo **não validado** (ver §5).

---

## 1. A pergunta original, respondida

No prompt de 01:17 apareciam duas cópias de um `camara_response` cuja resposta
é *"O contexto original que recebi está vazio — não há pergunta explícita à qual
responder"*. Uma **falha** armazenada, recuperada duas vezes, ocupando dois dos
slots entregues.

Hipótese: respostas de falha do caminho `camara_response` não recebem
`answer_class` tóxico, então a exclusão de `store.py:1662` não as pega.

**Confirmada — por duas causas independentes, e a segunda vale mais.**

## 2. Causa 1 — o caminho da câmara nunca carimba

`stamp_and_classify` (`write_provenance.py`) tem **um único chamador**:
`websocket.py:1242`, dentro do handler do turno principal. O caminho que gera
`camara_response` não passa por lá.

Confirmado no store: **0 de 10** entradas `camara_response` têm
`ctx_provenance` ou `answer_class`.

## 3. Causa 2 — o detector não reconhece o texto (a que importa)

Mesmo se fosse chamado, não adiantaria:

```
negacao_textual("O contexto original que recebi está vazio…")  → False
disq_textual(…)                                                 → False
classify(…)                                                     → None
```

E isso **não é específico da câmara**. Medido sobre as 80 respostas do piloto do
exp019 (`claude-haiku-4-5`, turnos reais):

| | detecta |
|---|---|
| candidatas a negação (padrão amplo, exploratório) | **22 / 80** |
| `negacao_textual` + `disq_textual` — **produção** | **6 / 22** |
| `FRASES_NEGACAO` do exp019 — minha lista | **0 / 22** |

**O detector que governa a quarentena tóxica reconhece cerca de 27% das negações
que este modelo de fato produz.**

Exemplos que os dois perderam:

> *"Não tenho contexto anterior nesta conversa"*
> *"Não consigo responder isso com confiança"*
> *"Não tenho registro de uma conversa anterior nesta sessão"*

## 4. A convergência que dá o diagnóstico

São **duas listas independentes**, escritas em momentos diferentes, para
propósitos diferentes — `negacao_textual` (exp012, 07/2026, produção) e
`FRASES_NEGACAO` (exp019, 18/08, minha) — e **as duas são cegas para a mesma
família de frases**.

Isso não é coincidência de autor. É a assinatura do método: lista de frases
escrita por introspecção sobre como *imaginamos* que a negação aparece, nunca
confrontada com o texto que o modelo realmente emite.

A minha teve recall **zero**, escrita dois dias atrás, por alguém que tinha
acabado de ler dezenas dessas respostas.

## 5. O que este achado NÃO estabelece

- **Não há ground truth rotulado.** O denominador (22) vem de um regex amplo que
  eu escrevi olhando as respostas — ele mesmo não foi validado, e pode conter
  falso positivo. A taxa de 27% é aproximada e o intervalo não foi calculado.
- **Não mede o impacto.** Quantas dessas negações viraram entrada armazenada e
  depois recuperada, ninguém contou. O caso das 2 cópias no prompt de 01:17 é
  anedota, não medida.
- **Não é generalizável a outros modelos.** As frases medidas são as do
  `claude-haiku-4-5`. Outro modelo nega com outro vocabulário.

## 6. O que a camada de guarda tóxica NÃO está quebrada

Vale separar, para o achado não virar alarme maior que o devido.

`ctx_provenance` **funciona**: das entradas elegíveis desde 03/08 (quando o
caminho passou a rodar), **2 de 2** têm carimbo. A cobertura de 2/137 no store
inteiro é idade, não falha — o store vai de 31/05 a 18/08 e quase todas as
entradas recentes são `session_summary`, que nunca passam por ali.

O que falha é o **reconhecimento**, não a mecânica.

## 7. Consequência para o desenho de qualquer detector futuro

Uma lista de frases congelada por introspecção não sobrevive ao contato com o
texto real. Se um detector de negação for redesenhado:

- as frases precisam sair de **amostra rotulada e reservada**, não de memória de
  quem escreve;
- o recall precisa ser **medido contra amostra cega**, não assumido;
- e o resultado precisa dizer o recall, porque um detector de 27% usado como se
  fosse de 100% produz exatamente o silêncio que o exp012 existe para eliminar.

## 8. Achado lateral — o terceiro comentário que mente sobre o próprio default

`websocket.py:1237` diz *"exp012 (EDP_WRITE_PROVENANCE, default OFF)"*.
`config.py:87` diz `os.environ.get("EDP_WRITE_PROVENANCE", "1")` — **default
ON**.

É o terceiro caso em dois dias, depois de `EDP_HYBRID_RETRIEVAL` (comentário
dizia desligada, ligada desde 08/07) e do `Desligada (default)` que sobreviveu
dentro da própria errata que corrigia esse tipo de afirmação.

O padrão: comentários que declaram default são escritos uma vez e nunca
revisitados quando a flag é promovida. Não há gate que os confira.
