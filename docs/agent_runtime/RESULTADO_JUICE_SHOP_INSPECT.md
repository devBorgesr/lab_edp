# Resultado — `browser.inspect` sobre o OWASP Juice Shop (Bloco B)

**06/09/2026.** Pré-registro: [`preregistro_juice_shop_inspect.md`](preregistro_juice_shop_inspect.md).
Procedimento: [`SMOKE_JUICE_SHOP.md`](SMOKE_JUICE_SHOP.md).

## Veredito: **H1**

As três condições da §3 rodaram contra Chrome real. O positivo produziu as três
observações com DOM 3,34× maior que o do dashboard, e **os dois controles
cruzados recusaram**. Como as duas abas são loopback, isso separa o que o Bloco
A não conseguia separar: **o escopo é por aba registrada, não por "é local"**.

---

## Ambiente

```
Chrome ............. 152.0.0.0        (Windows NT 10.0; Win64; x64)
Node ............... v22.14.0         exigido pelo juice-shop: "22 - 26"
Juice Shop ......... 20.2.0           pacote OFICIAL, nao build local
  artefato ......... juice-shop-20.2.0_node22_win32_x64.zip   120,4 MB
  md5 .............. 1191bb6ed1ab696507bb0b50b27bb7a5
                     conferido das duas pontas contra o publicado pela OWASP
extensao ........... claude-exporter-v4.2
  id ............... nfcegkcnhaggcfgbngmifkndbabgkacn
Runtime ............ --propositor eco --porta 8010 --browser
                     --origem-extensao chrome-extension://nfcegkcn...
                     --raiz .\tarefas_juice
  teto_nivel ....... 0     (o Runtime nao consegue executar L1)
alvo A ............. http://127.0.0.1:3000/#/    tab 1824678014
alvo B ............. http://127.0.0.1:8000/dashboard   tab 1824678011
```

**O alvo é um artefato verificado, não um build local.** A errata 2 do
pré-registro explica: o repositório do Juice Shop traz `.npmrc` com
`package-lock=false` na raiz e no `frontend`, então dois `npm install` da mesma
tag podem produzir árvores diferentes. O pacote da release é fixo e tem md5
publicado. O §4 continua atendido — mesmo alvo, mesma versão, mesma porta,
mesma rota.

**A página não foi tocada.** Nenhum clique, nenhum banner fechado, nenhum
scroll entre o carregamento e a medição. Os 1091 nós são do estado inicial de
`/#/` como a aplicação o entrega.

---

## Cronologia — UMA sessão, com uma tentativa inválida no meio

Registrada explicitamente porque no Bloco A um auditor lendo cortes do
transcrito concluiu que havia duas execuções independentes. Aqui os horários
são todos do relógio do navegador (UTC).

```
11:21:59   alvo.registrado + alvo.anexado    tab 1824678014, S-sgz2oc35
           ---- intervalo de ~18 min entre a anexacao e a submissao ----
~11:3x     T-6ecdbba9  FALHA  CanalIndisponivel        <- NAO CONTA, ver abaixo
11:39:57   alvo.registrado + alvo.anexado    tab 1824678014, mesma sessao
11:40:45   T-0ca9e427  CONCLUIDA  661,63 ms            <- js_positivo
11:46:24   R-cruz-1    browser.error                   <- js_cruzado
11:50:48   alvo trocado para tab 1824678011 (dashboard)
11:51:23   R-cruz-2    browser.error                   <- dash_cruzado
```

---

## A tentativa que não conta, e por quê

```
T-6ecdbba9
  status ......... FALHA
  iteracoes ...... 0
  motivo_parada .. CanalIndisponivel: painel recusou:
                   o debugger nao esta anexado ao alvo
  erro ........... null
```

O alvo estava `ANEXADO / operacional: True` quando conferido, e deixou de estar
antes da submissão. `iteracoes: 0` — a tarefa não chegou a rodar; o canal
recusou antes.

**Isto não é H0.** H0 seria a captura quebrar num DOM real: `depth: -1`
estourando tempo, memória ou limite de canal. Aqui nada foi medido. É a mesma
classe das duas tentativas inválidas do Bloco A: a pré-condição do teste — alvo
válido e operacional **no momento do disparo** — não existia. Dado inválido não
vira evidência, nem contra nem a favor.

**Causa não determinada.** A hipótese mais provável é o service worker MV3 ter
sido encerrado por ociosidade no intervalo de ~18 min, levando junto a sessão de
`chrome.debugger`. Não foi observado nenhum evento `[bridge]` de desanexo que
confirmasse — o handler estava instalado e teria logado. Fica como hipótese, não
como achado.

**A mitigação que fez a rodada válida funcionar**, e que está no procedimento:
manter o DevTools do service worker aberto (o Chrome não encerra um SW em
depuração) e emitir a conferência do alvo e a submissão **no mesmo bloco**, sem
janela entre uma e outra.

---

## `js_positivo` — `T-0ca9e427`

```json
{
  "task_id": "T-0ca9e427",
  "status": "CONCLUIDA",
  "iteracoes": 1,
  "motivo_parada": "eco: todas as capacidades declaradas observadas",
  "negadas": [],
  "duracao_ms": 661.63,
  "erro": null,
  "observacoes": [
    { "kind": "page",    "url": "http://127.0.0.1:3000/#/",
      "title": "Loja de sucos OWASP",   "hash": "e2e33331f3d3b06c" },
    { "kind": "dom",     "dom_nodes": 1091,     "hash": "201c71b2c4c2cb58" },
    { "kind": "history", "history_len": 4,      "hash": "74f1d8188c431b7c" }
  ],
  "fonte": "chrome.debugger tab=1824678014"
}
```

O `title` veio `"Loja de sucos OWASP"` — a aplicação Angular renderizada de
fato, com i18n aplicado, não um shell vazio. É o que descarta a leitura de que
`dom_nodes` alto poderia vir de um documento ainda não hidratado.

### §6, linha por linha

| linha | exigido | medido | |
|---|---|---|---|
| `status` | CONCLUIDA | CONCLUIDA | OK |
| `n_observacoes` | 3 | 3 | OK |
| `kinds` | page, dom, history | page, dom, history | OK |
| `url_bate` | começa com `http://127.0.0.1:3000` | `http://127.0.0.1:3000/#/` | OK |
| `dom_nodes_js` | > 0 | 1091 | OK |
| `razao_dom` | > 2 | 1091 / 327 = **3,34** | OK |
| `tempo_inspect` | < 10000 ms | 661,63 ms | OK |
| `campos_extra` | vazio | nada fora de `{kind,url,title,dom_nodes,history_len,erro}` | OK |
| persistido | existe | `tarefas_juice\T-0ca9e427\tarefa.json` = True | OK |

`dom_nodes_dash = 327` vem do Bloco A (`T-612fc612`, mesma capacidade, mesmo
controller).

**O ramo de investigação da §6 não foi acionado.** `razao_dom <= 2` obrigaria a
registrar o número sem afirmar nada sobre tamanho; com 3,34 a margem é
confortável e a linha vale como está.

---

## Os dois controles cruzados

```
js_cruzado      R-cruz-1   11:46:24.999
  alvo registrado ...... 1824678014  (Juice Shop)
  pedido apontando ..... 1824678011  (dashboard)
  resposta ............. browser.error
                         "tab_id 1824678011 nao e o alvo (1824678014)"    REJEITADO

dash_cruzado    R-cruz-2   11:51:23.532
  alvo registrado ...... 1824678011  (dashboard)
  pedido apontando ..... 1824678014  (Juice Shop)
  resposta ............. browser.error
                         "tab_id 1824678014 nao e o alvo (1824678011)"    REJEITADO
```

**É aqui que o Bloco B paga o que prometia.** No Bloco A havia uma aba loopback
só, então "escopo por aba" e "escopo por ser local" produziam o mesmo resultado
e o desenho não conseguia distinguir os dois. Aqui as duas abas são loopback, as
duas são "locais", e mesmo assim cada uma recusa a outra — nos dois sentidos. A
restrição é por **aba registrada**.

---

## Achado secundário: a correção do Bloco A resistiu a uma troca real

A troca de alvo em 11:50:48 — Juice Shop para dashboard — aconteceu **sem**
`Another debugger is already attached`. Esse foi o defeito real encontrado no
Bloco A: `limparAlvo()` era chamado sem `chrome.debugger.detach()`, e os testes
com `chrome` falso não o reproduziam. A correção (`invalidaAlvo()`) já tinha
três testes; agora está exercitada numa troca de alvo em Chrome real, que é
onde ela falhava antes.

Não estava no desenho e não altera o veredito. Fica registrado porque é
evidência que apareceu de graça.

---

## O que o H1 afirma, e o que não

**Afirma:** `browser.inspect` produz as três observações sobre uma aplicação
real com DOM grande, rotas e formulários; o DOM medido é 3,34× o do dashboard; e
a restrição de escopo é por aba registrada, verificada nos dois sentidos entre
duas origens loopback.

**A palavra "aba" está marcada como NÃO MEDIDA.** Este documento descreve o
raio do `chrome.debugger.attach` como sendo a aba anexada. Isso foi escrito por
raciocínio sobre o CDP, não por medida. Se `Network.getAllCookies`,
`Target.getTargets` ou `Target.attachToTarget` forem alcançáveis a partir de um
attach, o raio é o **perfil**, não a aba — e esta seção precisa de errata.
Pré-registro aberto para medir: [`preregistro_raio_do_attach.md`](preregistro_raio_do_attach.md).
O veredito H1 do Bloco B não depende disso: o que foi exercido continua sendo
três campos de leitura, e os dois controles cruzados continuam recusando.

**Não afirma nada sobre atuação.** Nenhum clique, preenchimento, navegação ou
execução de JS aconteceu. Nenhuma vulnerabilidade do Juice Shop foi exercitada.
Não houve login — de propósito, pelo §4: autenticar criaria sessão e cookie, e a
observação passaria a poder carregar estado de sessão.

**Não expande o Registry.** `browser.click` e o resto de L1 continuam recusados
por `exige_implementada()` e dependem da assinatura de `DECISAO_ATUACAO.md`. O
Runtime desta execução subiu com `teto_nivel: 0`.

`browser.inspect` continua L0 pela razão de sempre: a expressão enviada a
`Runtime.evaluate` é fixa no provider (`EXPR_PAGINA`, constante em
`debugger_controller.js`). No dia em que ela virar string vinda do modelo, a
classificação muda no mesmo commit.

---

## O que esta execução produziu de procedimento

Cinco defeitos encontrados armando, todos já corrigidos em
`SMOKE_JUICE_SHOP.md`:

```
--browser faltava na linha PowerShell do Bloco A (so a versao bash tinha)
--origem-extensao virou obrigatoria, e inverte a ordem extensao/Runtime
`npm install` do fonte quebra: edgesOut do arborist + package-lock=false
`tar` NAO existe nesta maquina; Expand-Archive trava; ZipFile .NET resolve
TLS 1.0/1.1 default do PS 5.1 faz o GitHub recusar o download
```

E um defeito de verificação, que é o mais grave dos seis porque estava do lado
de quem mede: o bloco que conferia o md5 fazia `if ($a -eq $b)`, e com os dois
downloads falhados `$null -eq $null` deu verdadeiro — **imprimiu `MD5 OK` sem
ter medido nada**. Gate degenerado, corrigido com `Test-Path` e teste de
não-vazio nos dois hashes.
