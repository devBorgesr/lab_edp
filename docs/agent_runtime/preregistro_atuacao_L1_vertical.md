# PRÉ-REGISTRO PREPARADO — BLOQUEADO
# Vertical slice de atuação L1 (`browser.click`)

## Estado: PREPARADO, não ARMADO

A distinção não é formalidade:

```
PREPARADO   o desenho existe; ha campos em branco; NADA pode ser executado
ARMADO      todos os campos congelados; o primeiro disparo real congela o resto
```

Um pré-registro **armado** não tem campo "a confirmar". Este tem três, e é por
isso que ele está preparado e não armado. Ele passa a ARMADO quando a
assinatura preencher a §6 — e só então o gatilho de congelamento vale.

**Este documento não pode ser executado.** `exige_implementada()` recusa toda
capacidade L1/L2 enquanto `docs/agent_runtime/DECISAO_ATUACAO.md` estiver com
as linhas de assinatura em branco — hoje são 5.

Ele existe pré-registrado para que, **quando** a assinatura acontecer, o
desenho já esteja congelado e não seja escrito depois de já se saber o que se
quer que dê certo. Escrever critério de aceite com o sistema na mão é o modo
mais confortável de não descobrir nada.

**Data de pré-registro: 2026-09-05.**

---

## Pré-condições, todas obrigatórias

```
[ ] preregistro_smoke_browser_inspect.md  PASSOU  (browser.inspect em Chrome real)
[ ] preregistro_juice_shop_inspect.md     PASSOU  (escopo por aba, nos dois sentidos)
[ ] DECISAO_ATUACAO.md ASSINADA, com as 5 linhas preenchidas:
        opcao ......................... A / B / C / D
        canal de volta ................ D1 polling / D2 WebSocket / D3 Native
        alvo permitido ................ ex.: so 127.0.0.1:3000
        primeira capacidade do slice .. ex.: browser.click
        justificativa
[ ] o bloco "O que este modulo NUNCA FAZ" de debugger_capturer.js reescrito
    NO MESMO COMMIT que o rompe — uma promessa de seguranca que sobrevive a
    propria violacao e pior que nao ter promessa
```

---

## 1. Pergunta

**Um `Input.dispatchMouseEvent` disparado pelo `ChromeDebuggerProvider` produz
efeito observável na página-alvo, e apenas nela — com a `Politica` negando a
mesma intenção quando o teto de nível não a autoriza?**

---

## 2. Hipótese

**H1 —** `browser.click` sobre um seletor conhecido do Juice Shop muda o DOM
de forma observável por um `browser.inspect` subsequente, e a mesma intenção
sob `Politica(nivel_maximo=OBSERVAR)` é **negada antes de chegar ao provedor**.

**H0 —** O clique não produz efeito (seletor errado, coordenadas erradas,
evento não confiável para o framework do Juice Shop), ou produz efeito mas a
observação seguinte não o detecta.

**H0 vencer é achado válido:** significa que atuação exige mais que
`Input.dispatchMouseEvent` — provavelmente resolução de seletor via
`DOM.querySelector` + `DOM.getBoxModel` antes do evento. Isso vira desenho de
um pré-registro novo, não um remendo neste.

---

## 3. Condições

| rótulo | papel |
|---|---|
| `click_autorizado` | `Politica(nivel_maximo=ALTERAR)`, alvo Juice Shop |
| `click_negado` | `Politica(nivel_maximo=OBSERVAR)` — **controle** |
| `click_aba_errada` | alvo registrado A, clique pedido em B |
| `antes_depois` | `inspect` → `click` → `inspect`, comparação |

**Controle negativo de validade:** `click_negado`. Se um clique acontecer com
a política em `OBSERVAR`, **a inversão de autoridade não existe** — e esse é o
desenho inteiro do Runtime. Nesse caso nenhum achado é afirmado e o slice
inteiro volta para a mesa.

---

## 4. Critério de decisão

```
PASSA H1 sse:
  click_autorizado   a observacao DEPOIS difere da observacao ANTES,
                     na dimensao esperada pelo seletor escolhido
  click_negado       Politica NEGA; nenhum comando CDP sai; a tarefa
                     registra a negacao em `negadas`
  click_aba_errada   REJEITADO, e nenhum comando vai para a aba B
  reversibilidade    declarada: o clique escolhido NAO e destrutivo
                     (nao apaga, nao compra, nao envia formulario)
  auditoria          o registro persistido diz: qual capacidade, qual alvo,
                     qual politica decidiu, qual foi o efeito
```

---

## 5. O que este slice NÃO faz

```
browser.fill        nao
browser.evaluate    nao — e outra capacidade, com decisao propria: trocar
                    EXPR_PAGINA por string do modelo abre
                    modelo -> JavaScript arbitrario -> pagina, e a
                    classificacao L0 deixa de existir no mesmo instante
browser.navigate    nao — L2
browser.download    nao — L2
browser.network     nao — L2
qualquer aba fora do alvo registrado    nao
qualquer origem nao-loopback            nao
```

Uma capacidade por vez, cada uma pelo Registry, pela Politica e por teste
próprio. O Registry cresce por decisão, não por conveniência.

---

## 6. Constantes — preenchê-las é o que torna este pré-registro ARMADO

| constante | valor | estado |
|---|---|---|
| capacidade | `browser.click` | a confirmar na assinatura |
| nível | `L1 ALTERAR` | fixo |
| alvo permitido | a definir na assinatura | **em branco** |
| seletor do clique | a definir | **em branco** |
| comandos CDP | `DOM.querySelector`, `DOM.getBoxModel`, `Input.dispatchMouseEvent` | provável, a confirmar |

**As linhas em branco acima são a razão de este documento estar bloqueado.**
Preenchê-las é a assinatura, e a assinatura não é minha.
