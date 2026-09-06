# Resultado — o raio real de um `chrome.debugger.attach`

**06/09/2026.** Pré-registro: [`preregistro_raio_do_attach.md`](preregistro_raio_do_attach.md).

## Veredito: **H0** — o raio é o perfil, não a aba

`Network.getAllCookies` foi **aceito** a partir de uma sessão anexada a uma
única aba, e devolveu **3 domínios de cookie distintos** enquanto a mesma
sessão via **1 domínio** pela via com escopo de aba (`Network.getCookies`).

A frase "controle daquela aba" no `RESULTADO_JUICE_SHOP_INSPECT.md` **subestima
o alcance** e recebe errata.

---

## A tabela

```
anel  metodo                          nu         nota / erro
----  ------------------------------  ---------  ------------------------------
A     DOM.getDocument                 ACEITO     root=#document      (controle)
B     Network.getCookies              ACEITO     n=1 dominios=1
B     DOMStorage.getDOMStorageItems   RECUSADO   -32601 "wasn't found"
C     Network.getAllCookies           ACEITO     n=4 dominios=3      <-- DECIDE
C     Target.getTargets               RECUSADO   -32000 "Not allowed"
C     Browser.getVersion              RECUSADO   -32601 "wasn't found"
D     Page.setDownloadBehavior        RECUSADO   -32000 "Cannot not access
                                                 browser-level commands"
A     DOM.getDocument                 ACEITO     root=#document      (controle)
```

`Target.attachToTarget` ficou **N/A** e conta como recusa pelo §6-e: ele exige
um `targetId`, e `Target.getTargets` recusou — o caminho para ele não existe.

**O controle do §3 passou nas duas pontas.** `DOM.getDocument` aceito antes e
depois, então o canal estava vivo o tempo todo e as recusas são recusas de
política, não de canal morto. Sem isso, nenhuma linha desta tabela valeria.

---

## O achado que vale mais que o veredito: há duas recusas diferentes

Os códigos de erro separam dois mecanismos que seriam invisíveis se só
contássemos aceitos e recusados.

```
-32601  "'X' wasn't found"
        O metodo NAO EXISTE nesta sessao. O dominio inteiro nao e exposto a
        uma sessao com escopo de aba.
        -> DOMStorage.getDOMStorageItems, Browser.getVersion

-32000  "Not allowed" / "Cannot not access browser-level commands"
        O metodo EXISTE e foi BLOQUEADO. Ha um filtro explicito, e ele nomeia
        a propria categoria: comandos de nivel de navegador.
        -> Target.getTargets, Page.setDownloadBehavior
```

*(o duplo negativo em "Cannot not access" é do próprio Chrome, transcrito como veio)*

**Ou seja: o Chrome FILTRA, e o filtro é real.** Enumerar outras abas, pivotar
para elas e mexer no comportamento de download estão bloqueados por decisão
explícita, com mensagem que nomeia a categoria.

**E `Network.getAllCookies` passa por esse filtro.** Ele devolve dado de escopo
de perfil e **não é classificado como comando de nível de navegador**. Não é
que não haja contenção — é que a contenção tem um buraco de categoria: o
`Network` é tratado como domínio de aba, e um de seus métodos não é.

Essa é a frase precisa do achado, e é diferente de "extensão com debugger vê
tudo".

---

## O que muda, e o que não muda

**Muda:** a descrição de raio. Onde os documentos dizem que um attach alcança a
aba, passa a valer:

```
alcanca         DOM, execucao de JS e cookies DA ABA
alcanca TAMBEM  o pote de cookies do PERFIL INTEIRO, via Network.getAllCookies
nao alcanca     enumeracao de outras abas, pivo para elas, comportamento de
                download, e o dominio Browser
```

**Não muda a classificação de `browser.inspect`.** A capacidade continua L0
porque ela **não envia** `Network.getAllCookies` — os três comandos que ela
envia estão escritos em `inspecionar()`, e a expressão de `Runtime.evaluate` é
a constante `EXPR_PAGINA`. O que este resultado altera é a **consequência de
uma mudança nesse código**, não o comportamento atual.

O que fica mais grave em uma linha: se `EXPR_PAGINA` virar string vinda do
modelo, ou se alguém acrescentar um comando ao mapa, o que está do outro lado
não é o DOM de uma aba — é o pote de cookies do perfil. Isso eleva o custo de
errar na `DECISAO_ATUACAO.md`, e é exatamente o tipo de fato que uma assinatura
precisa ter na mesa antes de ser dada.

---

## Ambiente

```
Chrome ......... 152.0.7977.77 (oficial, 64 bits)
SO ............. Windows 10 Version 1607 (Build 14393.5921)
perfil ......... C:\tmp\perfil_cdp_probe        DESCARTAVEL, apagado ao fim
extensao ....... Claude Exporter 4.10.0 (pasta claude-exporter-v4.2)
  id ........... nfcegkcnhaggcfgbngmifkndbabgkacn (igual ao do perfil real —
                 ID de extensao descompactada vem do caminho, nao do perfil)
  origins ...... http://127.0.0.1:3000/*, http://127.0.0.1:8000/*,
                 https://claude.ai/*
alvo anexado ... http://127.0.0.1:8000/dashboard   tab 777254524
sementes ....... 127.0.0.1:8000 e localhost:3000, `probe=1`
attach ......... chrome.debugger.attach({tabId}, '1.3') CRU
                 sem bridge, sem token, sem Agent Runtime
```

**Nenhum valor de cookie e nenhum nome de domínio foi lido, impresso ou
transcrito.** A função de resumo do instrumento devolve apenas contagens — o
§5 foi imposto por código, não por disciplina do operador. Sabemos que são 3
domínios; não sabemos quais, e não precisamos saber para decidir.

---

## Duas erratas foram necessárias antes de rodar

Ambas achadas relendo, não executando.

**Errata 1 — o §9 contradizia o §7.** O procedimento mandava registrar o alvo
"pelo bridge", mas o bridge faz polling no Agent Runtime, que o §7 proíbe de
participar. Resolvido com attach cru.

**Errata 2 — a semente de duas portas não discriminava.** Cookie é escopado por
domínio, não por porta: `127.0.0.1:3000` e `127.0.0.1:8000` são o mesmo balde.
Sem a terceira semente em `localhost`, `dominios_distintos` daria 1 mesmo com o
pote inteiro na mão, e a leitura teria sido "indeterminado, a semente falhou" —
quando o que falhou era o desenho da semente.

**A errata 2 é a que salvou o experimento.** Sem ela, esta rodada teria
produzido um não-resultado com aparência de resultado, e o `getAllCookies`
aceito teria sido lido como inconclusivo.

---

## Detalhes de procedimento para a próxima vez

```
perfil novo pede "allow pasting" em CADA instancia de DevTools
optional_host_permissions exige gesto do usuario: request() no console falha.
  Solucao: criar um botao na pagina do painel e clicar nele.
quatro contextos de console, e tres deles NAO servem:
  chrome://extensions ................ sem API de extensao
  aba de 127.0.0.1 / localhost ....... sem API de extensao (so a semente)
  DevTools do service worker ......... tem chrome.*, nao tem CopilotController
  copilot/panel.html ................. o unico que serve
DevTools aberto na aba alvo impede o attach
```

---

## O que este resultado NÃO autoriza

Implementar nada. Ele não adiciona capacidade, não passou pelo Agent Runtime e
não tocou `capacidades.py`. `browser.click` e o resto de L1 continuam recusados
por `exige_implementada()`, pendentes da assinatura de `DECISAO_ATUACAO.md`.

O resultado é insumo para essa assinatura, não substituto dela.
