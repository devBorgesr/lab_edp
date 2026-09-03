# Agent Runtime — a fronteira, não a fusão

**01/09/2026.** Une o kernel EDP e o Exportador **por contrato**, não por
merge de repositório. Nenhum dos dois foi alterado.

## A inversão que define o desenho

```
Copiloto  →  declara Tarefa
Kernel    →  governa (política, orçamento, memória, procedência)
Router    →  escolhe modelo
Modelo    →  propõe Intenção
Política  →  autoriza ou nega          ← a autoridade mora aqui
Provedor  →  executa, devolve Observação
```

**O modelo não tem autoridade. Tem capacidade de propor.** Concretamente: o
modelo nunca chama `provedor.executa`. Ele devolve uma `Intencao`, e só o
`Executor` executa — depois da política. Se essa camada sumisse, o resto
continuaria funcionando, e seria exatamente o agente-com-ferramentas que este
desenho existe para não ser. Há teste que falha nesse dia.

## O ponto de união que já existia

O `debugger_capturer.js` grava **HAR 1.2** em `/traffic/<data>/<sessão>.har`,
no sandbox da extensão, já redigido. `ProvedorHAR` lê esse arquivo.

Não fala com `chrome.debugger`, não abre aba, não pede permissão nova. **A
superfície de integração é um arquivo** — por isso a união pôde acontecer hoje
sem romper nada.

## Os três níveis

```
L0  OBSERVAR       lê o ambiente, não altera        IMPLEMENTADO
L1  ALTERAR        muda a página do usuário          declarado, recusado
L2  PRIVILEGIADO   navega, baixa, toca credencial    declarado, recusado
```

L1 e L2 levantam `CapacidadeNaoImplementada` apontando para
`DECISAO_ATUACAO.md`. **Não degradam em silêncio para "não fez nada"** — a
diferença entre "recusei" e "tentei e não consegui" é a única coisa que o
operador tem para decidir.

### Por que estão recusados

`debugger_capturer.js` tem um bloco **"O que este módulo NUNCA FAZ"**: nunca
`Input.*`, `Page.navigate`, `Page.reload`, nada que **altere** a aba. Verificado
no código — os únicos comandos CDP presentes são `Network.enable`,
`Network.getResponseBody` e `Runtime.enable`.

Não é lacuna de engenharia. É fronteira de segurança escrita de propósito, no
módulo que fala com o `chrome.debugger`, no navegador **autenticado** do
usuário. Rompê-la é decisão do pesquisador.

## Garantias com teste

| garantia | como |
|---|---|
| capacidade não declarada na tarefa é negada | política, e o loop continua |
| L1 sem aprovador não admite a tarefa | `BLOQUEADA`, não `FALHA` |
| política criada por acidente só observa | default `Nivel.OBSERVAR` |
| loop sem teto não existe | `Orcamento` obrigatório, teto duro de 100 |
| toda parada tem motivo | 4 estados terminais, `motivo_parada` sempre |
| observação é imutável | `frozen=True` + hash por conteúdo |
| segredo não passa | redação **de novo**, mesmo se a origem já redigiu |
| "nada encontrado" é observação | não silêncio, não lista vazia ambígua |
| tarefa filha não herda capacidade | senão L0 vira L2 em três saltos |

47 testes. **Nenhum gasta API** — o modelo é `ClienteFake` com respostas
roteirizadas; testar o loop com modelo real mediria o modelo, não o loop.

## O ciclo, fechado em L0 (03/09)

O `propositor` deixou de ser um callback abstrato: agora há Router real e
modelo produzindo `Intencao`.

```
Requisição (arquivo JSON)  →  Tarefa
Roteador                   →  escolhe modelo por complexidade
Cliente de modelo          →  devolve JSON
Parse estrito              →  Intencao ou None
Política                   →  autoriza ou nega
ProvedorHAR                →  Observação
                           →  próxima iteração
```

**`RoteadorEDP` adapta `edp/model_router.py::route_model`** — não
reimplementa. Verificado contra o kernel real: `"continue"` → `haiku` (tier 1),
pergunta técnica longa → `sonnet` (tier 2), com motivo e custo estimado.

Nota: `model_router` tem 3 importadores e **zero testes** no kernel (curadoria,
01/09). Por isso o adaptador **confere se o arquivo existe no caminho** antes
de confiar no import — `edp` em `sys.modules` fazia qualquer caminho "funcionar".

### O modelo é recurso substituível

A troca de modelo no meio da tarefa é testada: a **tarefa continua a mesma**,
porque o estado vive na `Tarefa` e nas `Observacao`, não no modelo. A trilha
guarda modelo, tier e custo por iteração — sem isso, uma tarefa que trocou de
modelo fica impossível de reconstruir.

### Parse estrito, pelo mesmo motivo do `juiz_llm`

Saída ilegível devolve `None`, **nunca `concluir=True`**. Se ilegível virasse
"concluir", um modelo com problema de formatação encerraria a tarefa dizendo
que atingiu o objetivo. Três ilegíveis seguidas terminam em `BLOQUEADA` com
motivo — nunca em `CONCLUIDA` por desistência.

## O transporte do Copiloto: o que falta, e por quê

**Não existe caminho do Copiloto para o runtime hoje.** Medido em 01/09:

```
sandbox do Copiloto   IndexedDB de chrome-extension://<id>  → Python não lê
host_permissions      ["https://claude.ai/*"]               → sem localhost
chrome.downloads      só em popup.js, não no Copiloto
```

Criar um custa:

| caminho | custo |
|---|---|
| HTTP local | adicionar `host_permission` ao manifest — **mexe no Exportador** |
| download | botão novo no painel do Copiloto — **mexe no Exportador** |
| arquivo manual | operador salva o JSON e aponta o runtime — **zero mudança** |

`requisicao.py` implementa o terceiro e deixa os outros dois possíveis: o
contrato é um **arquivo JSON** (`TarefaRequest v1`). Quem o escrever — botão
novo, servidor HTTP, ou uma pessoa — não muda nada no runtime.

**Não escolhi o transporte. Registrei que a escolha existe**, e que as duas
opções automáticas exigem tocar no Exportador, o que a própria análise que
originou este trabalho pediu para não fazer ainda.

## Dois defeitos achados ao ligar o ciclo

**Capacidade alucinada derrubava o loop.** Um modelo propondo
`observe.telepatia` levantava de dentro da política e matava a tarefa —
modelos alucinam nomes, e uma tarefa de 20 iterações morreria na primeira
palavra inventada. Agora é **negada**, e o modelo propõe outra coisa na
iteração seguinte. A distinção preservada: *declarar* capacidade inexistente
na `Tarefa` continua levantando (erro de contrato do cliente); *propor* no
meio do loop é alucinação e é negada.

**`RoteadorEDP` mentia sobre disponibilidade.** Depois do primeiro import,
`edp` fica em `sys.modules` e qualquer caminho passava a "funcionar" —
`disponivel` dizia `True` apontando para lugar nenhum. Agora confere o arquivo
no caminho antes.

## O que isto NÃO é

**Não faz parte do MVP de Diagnóstico de Retrieval.** `auditor/` não importa
`agent_runtime/`. O piloto externo continua sendo a prioridade declarada; esta
é linha de produto separada, e a decisão de atuação não bloqueia aquele piloto
nem o contrário.

**Não é um agente autônomo.** É o esqueleto de governança que tornaria um
agente autônomo decidível — construído antes da autonomia, de propósito, porque
a ordem inversa não tem volta.
