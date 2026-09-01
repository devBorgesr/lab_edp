# MVP-1F — gate de pré-produção

**01/09/2026.** Checklist do item 26, conferido por medição.

## Estado do gate

| item | estado |
|---|---|
| máquina de estados auditada | ✅ enum, `TRANSICOES` e doc conferidos por teste |
| invariantes do job | ✅ estado impossível não chega ao disco |
| crash recovery | ✅ job sobrevive; fila devolve tarefa órfã |
| concorrência | ✅ 10 auditorias simultâneas × 3 rodadas |
| idempotência entre processos | ✅ subprocessos distintos |
| isolamento | ✅ **vulnerabilidade real corrigida** — ver abaixo |
| path traversal / symlink | ✅ |
| segredos | ✅ 7 tipos, em query e documento |
| limites | ✅ `INVALID` com o número, sem truncar |
| repetibilidade | ✅ mesmos hashes e medições |
| adaptador externo | ✅ escrito só com o contrato público, em subprocesso |
| `check` dry-run | ✅ **corrigido** — era falso |
| `BLOCKED`/`INVALID`/`ERROR` distintos | ✅ |
| instalação limpa | ⚠️ `pip --target`, **sem `venv`** (sem `ensurepip` aqui) |
| Docker | 🔴 **`DOCKER_TEST = NAO_EXECUTADO`** |
| onboarding com pessoa | 🔴 `NAO_EXECUTADO` |

**Não marco `READY_FOR_EXTERNAL_PILOT`.** Três linhas acima não estão
verdes, e duas delas dependem de coisas que não tenho aqui.

---

## A vulnerabilidade

`Registro._arq` montava `<raiz>/<audit_id>/job.json` **sem validar o
`audit_id`**. Com `audit_id="../globex/segredo123"`, o registro do cliente
`acme` lia o job do cliente `globex`. Reproduzido:

```
acme lendo job do globex -> VAZOU: globex
caminho montado: .../data/acme/../globex/segredo123/job.json
```

O HTTP não vazava — **mas por acidente**: o roteador do Starlette não casa
barra dentro de parâmetro de caminho. Proteção incidental de biblioteca não é
defesa, e o CLI (`status`, `report`) não tinha nem isso.

Eu validava `client_id` desde o início e **nunca validei `audit_id`** — os dois
compõem o caminho, e o isolamento deste serviço é por caminho. Corrigido em
`Registro`, `Workspace` e por consequência na API; id hostil devolve `None`,
indistinguível de inexistente.

## O `check` prometia o que não fazia

A documentação entregue dizia *"responde em segundos, **sem processar nada**"*.
Medido: **1,81 s no `check` contra 1,74 s no `run`** — o mesmo trabalho. Ele
copiava o corpus, montava o índice, rodava todas as consultas e calculava as
cinco medições; só não gravava os dois relatórios.

Reescrito como dry-run de verdade: valida schema e limites, confere o snapshot,
pede **uma** consulta e verifica a procedência. **0,009 s — 214× mais rápido.**

E declara o que **não** verificou. Consequência honesta: **`READY` no `check`
não garante `COMPLETE` no `run`** — a cardinalidade só é medida com todas as
perguntas. Está no `QUICKSTART` e há teste que exige o aviso na saída.

## A retenção era promessa sem mecanismo

`PRIVACY.md` prometia 7/30/90/365 dias. **Nada no serviço chamava
`Workspace.expira`.** Uma garantia de retenção sem mecanismo é uma garantia que
não existe.

Agora há `auditor expirar`, que **lista por padrão** e só apaga com
`--executar`. Continua não rodando sozinho — apagar material de cliente dentro
de um processo que atende requisição é pior que não apagar — e a doc passou a
dizer que os prazos são **política, não automatismo**.

## O que não foi testado, e por quê

**Docker**: não há Docker nesta máquina. O `Dockerfile` está escrito e
revisado; **não foi construído nem executado**. `DOCKER_TEST = NAO_EXECUTADO`.

**`venv`**: sem `ensurepip` aqui. A instalação limpa usou `pip install
--target` a partir de um diretório neutro — prova que o pacote instala, importa
e roda sem os caminhos do laboratório (varredura por AST: **zero** literais com
`/home/`, `/media/sf_`, `edp_data_todo`), e que ele inicia com `fixtures/` e
`examples/` removidos. Mas não isola dependências como um `venv` isolaria.

**Onboarding com pessoa**: exige alguém da equipe que não escreveu o engine.
`NAO_EXECUTADO`.

## Continua `NAO_MEDIDO`

```
cliente real · valor percebido · disposição de pagar · tempo humano real
```

`PILOTO_ZERO/` está pronto: README de uma página, contrato, schema,
privacidade, claims e as oito perguntas — com o registro de integração para
preencher **durante**, não depois.
