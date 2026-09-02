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

23 testes.

## O que isto NÃO é

**Não faz parte do MVP de Diagnóstico de Retrieval.** `auditor/` não importa
`agent_runtime/`. O piloto externo continua sendo a prioridade declarada; esta
é linha de produto separada, e a decisão de atuação não bloqueia aquele piloto
nem o contrário.

**Não é um agente autônomo.** É o esqueleto de governança que tornaria um
agente autônomo decidível — construído antes da autonomia, de propósito, porque
a ordem inversa não tem volta.
