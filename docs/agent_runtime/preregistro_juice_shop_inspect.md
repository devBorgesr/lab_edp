# Pré-registro — `browser.inspect` sobre o OWASP Juice Shop

## O escopo de aba resiste a uma aplicação real, com DOM grande, rotas e formulários — ou ele só funcionava porque o dashboard do EDP é simples?

> **Régua da Bancada:** hipótese, condições e critério fixados **antes** de
> apontar o provedor para o Juice Shop. Congela ao primeiro disparo real.

**Data de pré-registro: 2026-09-05.**
**Depende de:** `preregistro_smoke_browser_inspect.md` ter PASSADO. Rodar este
antes seria testar duas coisas ao mesmo tempo e não saber qual falhou.

---

## 1. Motivação / contexto provado

**Nenhuma capacidade nova é necessária.** `browser.inspect` é `L0 OBSERVAR`,
já implementada e aceita (`capacidades.py`, verificado: `aceita = True`). O que
muda é **apenas o alvo**. Este pré-registro existe porque trocar o alvo é
exatamente o que a restrição de escopo governa, e o dashboard do EDP é um alvo
fácil demais para testá-la: poucas rotas, DOM pequeno, sem login.

**Por que o Juice Shop, e não um site de terceiros:** é uma aplicação
deliberadamente vulnerável mantida pela OWASP **para treinamento e teste de
ferramentas**, rodando local. Não há terceiro para autorizar, não há dado de
ninguém, e o propósito declarado do projeto é ser alvo de teste. Apontar o
provedor para um site real de terceiro seria outra decisão, com outro
consentimento, e não está neste documento.

**Ambiente medido nesta máquina (05/09/2026):**

```
docker ....... AUSENTE     -> instalar do fonte
npm .......... 9.2.0       -> disponivel
```

### ERRATA 05/09/2026 — a nota de ambiente acima estava incompleta

O texto original fica como estava. Ele sugeria que `npm` presente bastava, e
duas coisas faltavam:

```
npm i juice-shop   NAO FUNCIONA. O pacote foi DESPUBLICADO do npm em
                   15/01/2019. A unica via e o fonte:
                   git clone https://github.com/juice-shop/juice-shop.git

node               juice-shop 20.2.0 exige "engines": {"node": "22 - 26"}.
                   Esta maquina tem node v20.19.0 — FORA da faixa.
                   A maquina que roda o smoke (Windows, com Chrome) precisa
                   de Node 22+; conferir com `node --version` ANTES de clonar.

start              `node build/app` — ha etapa de build, nao e so `npm install`
deps               63 diretas; a arvore instalada e grande
```

### ERRATA 2 — 05/09/2026: "a única via é o fonte" também estava errado

A errata acima afirmou que, morto o `npm i`, **a única via é o fonte**. Não é.
A OWASP publica o Juice Shop **empacotado** nas releases do GitHub, por
plataforma e por versão de Node:

```
juice-shop-20.2.0_node22_win32_x64.zip     120 MB, com .md5 publicado ao lado
```

Descoberto depois de a via do fonte falhar nesta máquina: `npm install` morreu
no `postinstall`, no install aninhado do frontend, com
`Cannot read properties of null (reading 'edgesOut')` — bug do arborist do npm
10.9.2.

**E o pacote não é só mais fácil: é metodologicamente melhor.** O repositório
traz `.npmrc` com `package-lock=false`, na raiz e no `frontend`. Sem lockfile,
cada `npm install` resolve a árvore do zero, e duas instalações da mesma tag
podem produzir alvos diferentes. O artefato da release é fixo e verificável por
md5.

**Isto NÃO é troca de alvo.** O §4 nomeia *OWASP Juice Shop em
`http://127.0.0.1:3000`, rota `/#/`* — e continua sendo exatamente isso, na
mesma versão 20.2.0. O que muda é o meio de entrega, e muda para o **oficial**.
A regra que este pré-registro impõe é contra escolher o alvo depois de saber
qual é fácil de instalar; aqui o alvo não mudou, e nenhuma constante da §8 foi
tocada.

**Nada do desenho muda.** Hipótese, condições, controle cruzado nos dois
sentidos e critério de decisão continuam como congelados. O que mudou foi o
custo de armar, e ele agora está escrito em vez de ser descoberto no meio.

**Se Node 22+ não estiver disponível na máquina com Chrome**, isso não
autoriza trocar o alvo por outro servidor local mais leve. O alvo é nomeado no
§4, e trocá-lo é um pré-registro novo — não uma adaptação deste. A razão é a
mesma de sempre: um alvo escolhido depois de saber qual é fácil de instalar
não é o alvo que o desenho previu.

---

## 2. Hipótese e predições

**H1 —** `browser.inspect` produz as mesmas 3 observações sobre o Juice Shop,
com `page.url` da aba do Juice Shop e `dom_nodes` de ordem de grandeza
claramente maior que a do dashboard; **e**, com o Juice Shop registrado como
alvo, um pedido apontando a aba do dashboard é **rejeitado**.

**H0 —** Alguma coisa quebra num DOM real: `DOM.getDocument` com `depth: -1`
estoura tempo ou memória, a contagem recursiva de nós falha, ou a resposta
excede algum limite do canal.

**H0 vencer é achado válido e provável.** `depth: -1` pede a árvore inteira;
num SPA real isso pode ser muito maior do que no dashboard. Se estourar, o
achado é que `browser.inspect` precisa de um teto de profundidade ou de
tamanho — e esse teto vira constante congelada de um pré-registro novo, não um
ajuste silencioso deste.

---

## 3. Condições / desenho

| rótulo | papel |
|---|---|
| `js_positivo` | Juice Shop registrado e `ANEXADO`; espera-se observação |
| `js_cruzado` | Juice Shop registrado, pedido apontando a aba do **dashboard** |
| `dash_cruzado` | dashboard registrado, pedido apontando a aba do **Juice Shop** |

**Controle negativo de validade:** `js_cruzado` **e** `dash_cruzado`, nos dois
sentidos. Os dois são loopback e os dois são "locais" — se qualquer um passar,
o escopo é por "é local", e não por aba. Nesse caso **nenhum achado do
positivo é afirmado**, e a restrição precisa ser reescrita antes de qualquer
outra coisa.

Este é o teste que o Bloco A não consegue fazer: lá só existe uma aba
loopback, então "escopo por aba" e "escopo por ser local" produzem o mesmo
resultado.

---

## 4. Dataset (CONGELADO)

```
alvo A ....... http://127.0.0.1:3000    OWASP Juice Shop (npm, do fonte)
alvo B ....... http://127.0.0.1:8000    dashboard do EDP
rota do JS ... /#/                       pagina inicial, sem login
```

**Sem login, de propósito.** Autenticar no Juice Shop criaria sessão e cookie,
e a observação passaria a poder conter estado de sessão — o que muda a
categoria de risco e sairia do que `CAMPOS_OBS` foi desenhado para carregar.

**Pendência resolvida antes de armar:** o Juice Shop tem de estar servindo e a
página inicial carregada antes do registro. Registrar com a aba ainda em
`about:blank` seria recusa certa pelo motivo errado.

---

## 5. Métricas

As mesmas do smoke, mais uma comparação:

| métrica | fórmula |
|---|---|
| `n_observacoes` | `len(observacoes)` — esperado 3 |
| `url_bate` | `page.url` começa com `http://127.0.0.1:3000` |
| `dom_nodes_js` | `dom.dom_nodes` do Juice Shop |
| `dom_nodes_dash` | `dom.dom_nodes` do dashboard, do Bloco A |
| `razao_dom` | `dom_nodes_js / dom_nodes_dash` |
| `rejeitou_cruzado` | `type == "browser.error"` nos dois sentidos |
| `tempo_inspect` | `duracao_ms` da tarefa |

---

## 6. Critério de decisão (PASSA / FALHA)

```
PASSA H1 sse:
  js_positivo    n_observacoes == 3, kinds == {page,dom,history}
                 url_bate == True
                 dom_nodes_js > 0
                 razao_dom > 2          (o Juice Shop e visivelmente maior;
                                          se nao for, DOM.getDocument nao esta
                                          trazendo a arvore que se pensa)
                 tempo_inspect < 10000 ms   (teto do controller)
  js_cruzado     REJEITADO  -> /não é o alvo/
  dash_cruzado   REJEITADO  -> /não é o alvo/
  campos_extra   vazio
```

**`razao_dom <= 2` não é FALHA automática, é INVESTIGAÇÃO:** pode significar
que o Juice Shop renderiza pouco antes do carregamento completo. Nesse caso o
resultado registra o número e a hipótese, e nenhum achado sobre tamanho é
afirmado — mas as demais linhas continuam valendo.

**Qualquer rejeição cruzada que falhe ⇒ FALHA, e o positivo é descartado
junto.**

---

## 7. Anti-mock e isolamento

Mesmo mecanismo real do smoke. Adicionalmente:

```
[ ] Juice Shop roda LOCAL, em 127.0.0.1:3000 — nunca uma instancia hospedada
[ ] sem login, sem dado inventado, sem exercicio de vulnerabilidade
[ ] a extensao continua com `host_permissions: ["https://claude.ai/*"]`;
    127.0.0.1 vem de optional_host_permissions concedida em runtime
[ ] captura de trafego parada ou com redacao ligada (licao de #T1)
[ ] `--raiz` proprio, separado do smoke do Bloco A
```

**O que este pré-registro NÃO autoriza:** clicar, preencher, navegar, executar
JS, ou exercitar qualquer vulnerabilidade do Juice Shop. Isso é L1, está em
`preregistro_atuacao_L1_vertical.md`, e depende da assinatura de
`DECISAO_ATUACAO.md`.

---

## 8. Constantes congeladas

As mesmas do `preregistro_smoke_browser_inspect.md` §8, mais:

| constante | valor |
|---|---|
| porta do Juice Shop | `3000` |
| rota | `/#/` |
| `razao_dom` mínima | `2` |
| teto de tempo | `10000 ms` (o `TIMEOUT_MS` do controller) |

---

## 9. Procedimento

```
1. instalar e subir o Juice Shop (docker ausente aqui -> do fonte)
2. abrir http://127.0.0.1:3000/#/ e esperar a pagina carregar
3. no console do painel: registrar a aba do Juice Shop como alvo
4. GET /v1/browser/alvo -> operacional:true, com a origin do Juice Shop
5. tarefa com capacidades ["browser.inspect"] -> js_positivo
6. pedido manual apontando a aba do dashboard -> js_cruzado
7. registrar de volta a aba do dashboard; pedido apontando o Juice Shop
   -> dash_cruzado
8. registrar tudo em RESULTADO_JUICE_SHOP_INSPECT.md
```

---

## 10. Onde o resultado vai

`docs/agent_runtime/RESULTADO_JUICE_SHOP_INSPECT.md`, com cada linha da §6
verdadeira ou falsa, os dois `dom_nodes`, a razão, e o veredito H1/H0.
