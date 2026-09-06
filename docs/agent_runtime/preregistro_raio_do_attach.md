# Pré-registro — o raio real de um `chrome.debugger.attach`

## Um `attach` alcança só a aba anexada, ou alcança o perfil do navegador inteiro?

> **Régua da Bancada:** hipótese, condições, métrica e critério fixados **antes**
> de enviar o primeiro comando. Congela ao primeiro disparo real. Se um defeito
> invalidar o desenho, é um pré-registro novo — não uma edição deste.

**Data de pré-registro: 2026-09-06.**
**Depende de:** nada. É pergunta de plataforma, não do Juice Shop.

---

## 1. Por que este documento existe

O `RESULTADO_JUICE_SHOP_INSPECT.md` afirma que o Bloco B exerceu leitura de três
campos enquanto **detinha controle daquela aba**. A frase "daquela aba" foi
escrita por raciocínio, não por medida.

O que se sabe, verificado no código e no manifesto:

```
manifest.json    permissions inclui 'debugger' (estatica)
                 optional_host_permissions = ['http://*/*', 'https://*/*']
controller       chrome.debugger.attach({tabId}, '1.3')
                 chrome.debugger.sendCommand aceita QUALQUER string como metodo
```

O que **não** se sabe: se o Chrome filtra famílias de comandos especificamente
para `chrome.debugger`, e — o que decide a gravidade — se comandos de **escopo
maior que a aba** ficam alcançáveis. O caso que importa é `Network.getAllCookies`,
que na especificação do CDP devolve o pote de cookies do **perfil inteiro**, não
os da página anexada.

Se ele responder, "controle daquela aba" subestima o alcance, e o documento do
Bloco B precisa de errata.

### O que este pré-registro deliberadamente NÃO mede

**Atuação dentro da aba** — `Runtime.evaluate` com expressão arbitrária,
`Input.dispatchMouseEvent`, `Page.navigate`. A resposta já é conhecida pela
especificação do CDP e não está em dúvida; exercitá-la acrescentaria risco sem
acrescentar medida. A pergunta aqui é de **alcance de dado**, não de atuação.

**Este experimento não passa pelo Agent Runtime.** Não adiciona capacidade, não
toca `capacidades.py`, não altera o Registry. É um humano digitando
`chrome.debugger.sendCommand` num console, para caracterizar a plataforma. Um
resultado positivo aqui **não autoriza implementar nada** — ele informa a
`DECISAO_ATUACAO.md`, que continua pendente de assinatura.

---

## 2. Hipótese e predições

**H1 — o alcance é a aba.** Todo comando de escopo maior que o alvo anexado é
recusado pelo `chrome.debugger`, com erro. A frase "controle daquela aba" está
correta e o documento do Bloco B fica como está.

**H0 — o alcance excede a aba.** Pelo menos um comando devolve dado de fora do
alvo anexado: cookies de domínios que não o da aba, enumeração de outros alvos,
ou anexação a outro alvo a partir deste.

**H0 vencer é o resultado provável, e é o que importa saber.** O `chrome.debugger`
expõe o CDP de uma superfície que historicamente foi desenhada para o DevTools,
onde escopo de browser é normal. Se H0 vencer, a consequência não é técnica: é
que a palavra "aba" some da descrição de risco de `browser.inspect` e é
substituída por "perfil", em três documentos.

---

## 3. Condições / desenho

Um comando por condição, agrupados por anel de alcance. O anel é o que dá
significado ao resultado — não a contagem de sucessos.

| anel | comando | o que um sucesso significa |
|---|---|---|
| A — a aba | `DOM.getDocument` | nada novo; **controle positivo do canal** |
| B — dado sensível da aba | `Network.getCookies` | o attach lê cookie da própria página |
| B | `DOMStorage.getDOMStorageItems` | idem, para localStorage |
| **C — além da aba** | `Network.getAllCookies` | **acesso ao pote do perfil inteiro** |
| **C** | `Target.getTargets` | enumeração das outras abas abertas |
| **C** | `Target.attachToTarget` | pivô para outra aba a partir desta |
| C | `Browser.getVersion` | o domínio `Browser` está exposto à extensão |
| D — fora do navegador | `Page.setDownloadBehavior` | o debugger alcança o sistema de arquivos |

**Controle positivo de validade:** o anel A. Se `DOM.getDocument` falhar, o canal
está quebrado e **nenhuma recusa dos outros anéis é evidência de nada** — recusa
por canal morto não é recusa por política. O anel A roda primeiro e roda por
último, e os dois têm de passar.

---

## 4. Ambiente (CONGELADO)

```
perfil ......... DEDICADO E DESCARTAVEL
                 chrome.exe --user-data-dir=C:\tmp\perfil_cdp_probe
alvo ........... http://127.0.0.1:8000/dashboard   (aba anexada)
semente ........ http://127.0.0.1:3000/#/          (segunda origem, NAO anexada)
extensao ....... claude-exporter-v4.2, carregada nesse perfil
```

**O perfil dedicado é o controle de exposição, e não é opcional.** No perfil real
do pesquisador há sessão do claude.ai. Se `Network.getAllCookies` responder, ele
devolveria essa credencial para dentro de um console — medir o vazamento
causando o vazamento. O perfil descartável não tem nada além do que a semente
puser lá.

**Duas origens de propósito.** Com uma só, "cookies do perfil" e "cookies da aba"
dariam o mesmo conjunto, e o resultado não distinguiria as hipóteses — é o mesmo
erro que o Bloco A tinha com uma aba loopback só.

---

## 5. Métricas — e o que NUNCA é registrado

Para cada comando, exatamente três campos:

```
aceito ......... o sendCommand resolveu, ou rejeitou com erro
erro ........... a mensagem, quando rejeitou
alcance ........ SO_DA_ABA | ALEM_DA_ABA | N/A
```

Para `Network.getAllCookies` e `Network.getCookies`, e só para eles, mais dois:

```
n_cookies .............. contagem
dominios_distintos ..... CONTAGEM de dominios distintos, nao a lista
```

**Nenhum `value` de cookie é lido, impresso, copiado ou colado. Nenhum nome de
domínio é transcrito.** O que decide H0 é `dominios_distintos > 1` com o alvo
anexado servindo uma origem só — e isso é um número, não um dado. Um resultado
que exija transcrever o conteúdo para ser convincente está mal desenhado.

---

## 6. Critério de decisão (PASSA / FALHA)

```
PASSA H1 sse TODAS:

  anel A ........... DOM.getDocument aceito, antes e depois     (controle)
  Network.getAllCookies ..... RECUSADO
  Target.getTargets ......... RECUSADO
  Target.attachToTarget ..... RECUSADO
  Page.setDownloadBehavior .. RECUSADO

  (o anel B pode ser aceito sem derrubar H1: cookie e storage DA PROPRIA
   ABA estao dentro do escopo que a frase "controle daquela aba" ja afirma)

FALHA -> H0 se QUALQUER comando do anel C ou D for aceito.
```

**Um caso especial, decidido antes de ver o dado:** se `Network.getAllCookies`
for aceito mas devolver `dominios_distintos == 1` (só o do alvo), isso **não é
H1**. É resultado indeterminado, porque o perfil descartável pode não ter cookie
da segunda origem. Nesse caso a semente falhou, e a condição é refeita — não
reinterpretada.

**O que PASSA autoriza:** manter a redação atual do Bloco B. **O que FALHA
autoriza:** errata em `RESULTADO_JUICE_SHOP_INSPECT.md`, em
`preregistro_smoke_browser_inspect.md` e em `DECISAO_ATUACAO.md`, trocando
"aba" por "perfil" na descrição de raio. **Nenhum dos dois autoriza implementar
capacidade nova.**

---

## 7. Anti-mock e isolamento

```
[ ] perfil dedicado --user-data-dir, JAMAIS o perfil com sessao do claude.ai
[ ] captura de trafego do painel PARADA (licao de #T1)
[ ] nenhum site de terceiro aberto no perfil; so as duas origens locais
[ ] o Agent Runtime NAO participa: nada disto passa por /v1/tarefas
[ ] o perfil e APAGADO ao fim, e o apagamento e registrado
```

O mecanismo é o real: `chrome.debugger.sendCommand` da própria extensão, sem
reimplementação. Não há fake aqui — um `chrome` simulado responderia o que o
simulador decidir, que é exatamente a pergunta em aberto.

---

## 8. Constantes congeladas

| constante | valor |
|---|---|
| perfil | `C:\tmp\perfil_cdp_probe`, criado vazio |
| alvo anexado | `http://127.0.0.1:8000/dashboard` |
| segunda origem | `http://127.0.0.1:3000/#/` |
| versão do protocolo | `1.3` (a mesma do controller) |
| teto por comando | `5000 ms` |
| ordem | anel A, B, C, D, anel A de novo |

Mudou qualquer uma ⇒ é outro pré-registro.

---

## 9. Procedimento

```
1. fechar o Chrome do perfil normal (o attach e por perfil, e a faixa de
   depuracao aparece no perfil errado se isto for pulado)
2. subir o Chrome com --user-data-dir=C:\tmp\perfil_cdp_probe
3. carregar a extensao nesse perfil; conceder host permission para as duas
   origens locais quando o prompt aparecer
4. abrir as DUAS abas: 8000 (sera o alvo) e 3000 (a semente)
5. registrar 8000 como alvo pelo bridge, confirmar alvo.anexado
6. anel A: DOM.getDocument                       -> tem de aceitar
7. aneis B, C, D: um comando por vez, anotando aceito/erro
8. anel A de novo                                -> tem de aceitar
9. apagar C:\tmp\perfil_cdp_probe
10. registrar em RESULTADO_RAIO_DO_ATTACH.md
```

---

## ERRATA 1 — 06/09/2026, antes do primeiro comando

Quatro ajustes de procedimento. **Nenhuma linha da §2, §3, §5 ou §6 muda.**

### a) Attach cru, não pelo bridge — o §9 contradizia o §7

O §9 passo 5 mandava "registrar 8000 como alvo pelo bridge". O §7 exige que o
Agent Runtime não participe. O bridge **faz polling no Runtime** — as duas
instruções não podem valer juntas.

Resolvido em favor do §7, que é o requisito de isolamento:

```js
await chrome.debugger.attach({tabId}, '1.3');
```

O objeto de medida não muda: é exatamente a linha que o controller executa em
`anexar()`. O controller não acrescenta nada ao attach — só chama essa linha,
mais `DOM.enable` e `Page.enable`, que o procedimento repete. Tirar o bridge
remove Runtime, token e CORS do caminho, e com eles três fontes de falha que
não têm relação com a pergunta.

### b) Semente determinística de cookie

O §6 prevê o ramo indeterminado se `dominios_distintos == 1`. Sem semear, esse
ramo é o resultado **provável**, porque um perfil recém-criado pode
simplesmente não ter cookie das duas origens — e aí o experimento não mediu
nada e custou o mesmo.

Antes do attach, no console **de cada aba** (não no do painel):

```js
document.cookie = "probe=1; path=/"
```

É preparação de ambiente feita pelo humano no próprio navegador descartável,
da mesma natureza que navegar até a URL. Não passa por capacidade nenhuma.

### c) "Alcançável de um attach nu" e "alcançável com o domínio ligado" são
respostas diferentes

Alguns comandos CDP exigem `<Dominio>.enable` antes. Uma recusa por domínio
desligado **não é** recusa por política, e tratar as duas como a mesma coisa
inverteria o sentido do resultado.

Por isso cada comando é tentado primeiro **sem** enable. Se o erro disser que o
domínio precisa estar habilitado, o `enable` é tentado e o comando repetido — e
as duas respostas entram na tabela, em colunas diferentes.

### d) `Page.setDownloadBehavior` com `behavior: 'deny'`

Mede se o comando é **aceito** sem escrever nada em disco. O anel D pergunta se
o debugger alcança o sistema de arquivos, e a aceitação já responde.

### e) `Target.attachToTarget` é condicional

Ele exige um `targetId`, que só existe se `Target.getTargets` for aceito. Se
`getTargets` recusar, `attachToTarget` fica `N/A` — e isso **conta como recusa**
para o §6, porque o caminho para ele não existe.

### f) A regra de "nenhum conteúdo" é imposta por código, não por disciplina

A função de resumo do procedimento devolve, para qualquer comando de cookie,
**apenas** `n=<contagem> dominios=<contagem de distintos>`. Nome de domínio e
`value` não são acessíveis ao operador nem por engano. O §5 vira mecanismo em
vez de promessa.

---

## ERRATA 2 — 06/09/2026: a semente de duas portas não discrimina

Encontrado montando o Passo 4, antes de qualquer comando ter sido enviado.

**Cookie não distingue porta.** Para o navegador, `http://127.0.0.1:3000` e
`http://127.0.0.1:8000` são origens diferentes. Para o pote de cookies, são o
**mesmo domínio**: `127.0.0.1`. A §4 apoiava-se na premissa de que duas portas
dariam dois domínios de cookie, e essa premissa é falsa.

**A consequência, se não fosse corrigido:** `dominios_distintos` daria `1` mesmo
que `Network.getAllCookies` devolvesse o pote inteiro. O §6 cairia no ramo
indeterminado, e a leitura errada seria "a semente falhou" — quando o que falhou
foi o desenho da semente. O experimento custaria o mesmo e não mediria nada.

**A correção é aditiva, e nada frozen é removido.** `localhost` e `127.0.0.1`
são domínios de cookie distintos, ainda que resolvam para o mesmo loopback.
Além das duas origens já congeladas, semeia-se uma terceira página:

```
http://127.0.0.1:8000/dashboard    alvo anexado        dominio 127.0.0.1
http://127.0.0.1:3000/#/           segunda origem      dominio 127.0.0.1  (mesmo!)
http://localhost:3000/#/           TERCEIRA, adicionada    dominio localhost
```

Com isso o discriminador fica limpo:

```
dominios_distintos == 1   -> o attach devolveu so o dominio da aba anexada
dominios_distintos >= 2   -> o attach alcancou alem da aba          -> H0
```

**Se `localhost:3000` não responder** — no Windows `localhost` pode resolver
para `::1` antes de `127.0.0.1`, e um servidor preso a IPv4 não atende — tenta-se
`http://localhost:8000/dashboard`. Se nenhum dos dois responder, a condição
**não roda**, e o resultado é registrado como não medido. Inventar uma terceira
origem qualquer para salvar a rodada seria escolher o dado depois de saber o que
ele precisa mostrar.

Hipótese, condições, métrica e critério continuam como congelados. Mudou a
semente, e mudou porque a anterior era incapaz de separar as hipóteses.

---

## 10. Onde o resultado vai

`docs/agent_runtime/RESULTADO_RAIO_DO_ATTACH.md`, com a tabela dos oito
comandos, o veredito H1/H0, e — se H0 — a lista exata dos documentos que
precisam de errata. Enquanto ele não existir, a frase "controle daquela aba" no
Bloco B fica com a marca de **não medida**.
