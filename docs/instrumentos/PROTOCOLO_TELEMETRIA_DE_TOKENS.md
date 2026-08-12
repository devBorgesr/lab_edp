# Instrumento — protocolo de coleta para calibrar chars→tokens

**Agnóstico de sujeito.** Serve para qualquer sistema que monte prompt e
chame uma API de LLM cobrada por token. Extraído da Fase 1 aplicada ao EDP
em 2026-08-12 (`docs/sujeito_edp/AUDITORIA_FASE1_TOKENS.md`), mas nada aqui
depende do EDP.

---

## O problema

Sistemas que montam prompt orçam espaço em **caracteres** e são cobrados em
**tokens**, e fecham a lacuna com uma razão fixa herdada — quase sempre
`4 chars ≈ 1 token`. A razão não é universal: varia por idioma (BPE tem
peças maiores para inglês), por raridade de palavra, e por tipo de conteúdo
(código tokeniza diferente de prosa). Num corpus que não seja inglês
técnico médio, a razão herdada está errada e ninguém sabe em que direção.

O dado para corrigir isso normalmente **já existe e é descartado**: a
resposta da API traz o token real cobrado, e o sistema o usa para calcular
custo e joga fora sem nunca comparar com o tamanho do que enviou.

**Antes de escrever qualquer coisa, procure por isso** — `grep -rn "usage"`
no cliente da API. Se o campo existe, a Fase 1 é instrumentação, não
estimação.

---

## Sete decisões, e o que cada uma evita

**1. Emita no canal de telemetria que já existe.**
Canal paralelo cria segunda fonte de verdade, com rotação e formato
próprios, e invisível para os consumidores que já leem o canal existente.

**2. Grave o objeto `usage` VERBATIM, nunca campos extraídos.**
Se cache de prompt for ligado depois, `usage` ganha campos novos e uma
chamada cacheada tem relação chars→tokens-cobrados completamente diferente
de uma sem cache. Quem gravou só `input_tokens` fica com todas as amostras
posteriores contaminadas e **indistinguíveis** das limpas — o dataset
inteiro vira suspeito retroativamente. Gravar o dict inteiro custa nada e
mantém as duas populações separáveis para sempre.

**3. Amostra incompleta é DESCARTADA, nunca completada com zero.**
Em streaming os contadores chegam em eventos distintos e um pode faltar.
Uma amostra dizendo "4800 chars custaram 0 tokens" envenena a razão de um
jeito que nenhuma análise posterior detecta como erro. Uma amostra a menos
é o custo certo.

**4. Grave DOIS numeradores, não um.**
"Quantos chars foram enviados" tem duas respostas defensáveis: o texto que
a API tokeniza, e os bytes no fio (com o andaime de serialização, que a API
não cobra mas cujo tamanho escala com o número de mensagens). Escolher uma
às cegas produz um número com aparência de medido. Grave as duas mais a
contagem de mensagens, e deixe a análise decidir com dado qual é mais
estável. Custo: dois inteiros por amostra.

*Observado na prática:* os dois divergem muito mais em prompt curto — num
prompt de ~200 chars o andaime quase dobrou a contagem de bytes. Portanto a
análise **não pode** tirar uma razão média sobre tamanhos misturados sem
antes olhar essa dependência.

**5. Meça sobre o payload FINAL, não sobre a requisição de entrada.**
A montagem do payload move campos de lugar, injeta mensagens de preenchimento
e descarta outras. Medir antes conta caracteres que não foram enviados e
deixa de contar os que foram.

**6. Estratifique NA COLETA, e grave os sinais crus.**
Uma razão global é a média de regimes distintos (prosa acentuada, código,
prosa ASCII) e não serve para nenhum. Isso é **irreversível**: a classe não
está no par `(chars, tokens)` — se não for gravada agora, não há como
estratificar depois.

Use classificador determinístico e barato (proporção de não-ASCII, cercas
de código, densidade de símbolos). E grave **os sinais crus junto do
rótulo**: os limiares do classificador são escolha sem medição, e só são
inofensivos porque não entram em decisão nenhuma — eles particionam. Com os
sinais gravados, a análise re-particiona com outros limiares sem recoletar.
O irreversível é não gravar os sinais, não o valor do limiar.

**7. Congele o formato de injeção enquanto a coleta estiver aberta.**
Esta é a que invalida tudo em silêncio. Compactar, podar ou encurtar blocos
no meio da coleta mistura dois regimes no mesmo dataset, e a razão
resultante não descreve nenhum deles — **sem dar erro**, só um número
errado com cara de medido.

Consequência prática: a flag que liga a coleta é também a declaração de
"formato congelado a partir de agora". Trate ligá-la como decisão, não como
default.

---

## Ordem de fases (e por que a ordem não é negociável)

| fase | o que faz |
|---|---|
| 1 | coleta o par `(chars, tokens reais)` — não muda nada |
| 2 | calcula a razão, com hipótese e limiar congelados **antes** de olhar o dado |
| 3 | aplica a razão medida aos orçamentos, e só então otimiza formato |

Toda técnica de **reduzir** consumo (poda de saída, roteamento esparso,
formato compacto, cache de prompt) pertence à Fase 3. Aplicada na Fase 1,
destrói a Fase 1 pela regra 7. São operações opostas na ordem de execução,
não tarefas paralelas.

---

## Custo de implementação, para calibrar expectativa

No caso que originou este protocolo: ~280 linhas de produção em 4 arquivos,
25 testes, e dois testes que valem citar como padrão —

- **flag-off byte-idêntico**: com a coleta desligada, o caminho é um `if` e
  mais nada. Prova-se sabotando a função de medição para lançar exceção e
  verificando que nada acontece — isso prova que o gate vem **antes** da
  medição, não depois.
- **falha de telemetria não propaga**: disco cheio não pode derrubar uma
  resposta ao usuário para gravar telemetria. Prova-se com o destino de
  escrita inacessível.
