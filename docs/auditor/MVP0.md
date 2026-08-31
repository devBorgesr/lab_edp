# MVP-0 do serviço de auditoria

**31/08/2026.** Pipeline que recebe um sistema e produz **um de dois**
resultados: uma auditoria, ou um bloqueio com motivo verificável. Nunca uma
métrica quando uma pré-condição de validade está quebrada.

O caso de teste é o próprio REL-001, que está bloqueado.

## A propriedade que distingue isto de uma ferramenta de avaliação

Quando uma pré-condição bloqueante falha, o pipeline **interrompe**. As etapas
seguintes ficam `PENDING` e não rodam.

Não é que o número deixe de ser impresso — ele **não chega a ser calculado**.

Há três trancas independentes, porque uma só depende de quem escreveu o
chamador:

1. `Auditoria.roda()` para na etapa que barrou;
2. `Manifesto.publica_resultado()` levanta `AuditoriaBloqueada` se houver
   barreira — pega quem montar as etapas na mão;
3. `Manifesto.resultado` levanta na leitura — pega quem gerar relatório sozinho.

## Estados

| estado | significado | autoriza métrica? |
|---|---|---|
| `PASS` | rodou e passou | sim |
| `FAIL` | rodou e o sistema auditado reprovou | **sim — isto é resultado do cliente** |
| `BLOCKED` | não pôde rodar; pré-condição quebrada | não |
| `INVALID` | o insumo não é auditável | não |
| `PENDING` | não executou | não |

A distinção que importa comercialmente é `FAIL` × `BLOCKED`. Um serviço que as
confunde entrega *"seu RAG tem Recall@5 = 0,41"* quando não mediu nada.

## Verificações, e o que cada uma detecta

Todo check é obrigado a declarar **qual defeito seu número moveria**
(`NORTE §4.15`) — é campo obrigatório, e `Resultado` recusa construção sem ele.

| check | detecta |
|---|---|
| `ranking.veio_do_retriever` | ranking fabricado (ordem de arquivo, alfabética) |
| `ranking.cardinalidade` | duplicação consumindo a janela top-k |
| `ranking.duplicacao_medida` | *(diagnóstico, não barra)* duplicação por id e por texto |
| `estratos.sem_sobreposicao` | mesmo documento julgado duas vezes |
| `estratos.controle_fora_do_ranking` | controle negativo contaminado |
| `estratos.tamanhos` | pool incompleto alterando a prevalência |
| `procedencia.artefato_e_auditavel` | artefato invalidado reaproveitado; dado órfão de corpus |
| `procedencia.snapshot_tem_hash` | corpus trocado sob o mesmo caminho |
| `estatistica.unidades_suficientes` | IC estreito por contar itens como independentes |
| `estatistica.prevalencia_permite_acordo` | acordo produzido pelo desbalanceamento |

Nenhum é hipotético: cada um é um defeito que **já passou** neste projeto.

## Cenários provados

| caso | defeito | resultado |
|---|---|---|
| A | nenhum | `COMPLETE` |
| B | mesmo id em duas camadas | `BLOCKED` — cardinalidade |
| C | corpus pequeno | `BLOCKED` — cardinalidade |
| D | controle presente no ranking | `BLOCKED` — controle contaminado |
| E | **ordem de arquivo como ranking** | `BLOCKED` — procedência |
| F | score constante | `BLOCKED` — procedência |
| G | ranking fora de ordem | `BLOCKED` — procedência |
| H | snapshot sem hash | `BLOCKED` — procedência |
| — | poucos clusters | `BLOCKED` — estatística |
| — | prevalência 97% | `BLOCKED` — estatística |

O caso E é exatamente a invalidação 01. **Agora falha na primeira etapa de
ranking, antes de qualquer chamada de API.**

## Rodada real contra o EDP

```
python -m auditor run --input <store> --protocol REL-001 \
  --amostra amostra_congelada.json --dominios dominio_congelado_v2.json \
  --output auditorias/edp_2026-08-31
```

Saída: `BLOCKED`, exit code 2.

> 50 de 50 queries não alcançam 50 documentos distintos (min=30, mediana=37,
> max=41). Os slots estão cheios; os documentos, não.

Artefatos em `auditorias/edp_2026-08-31/`: `relatorio.md` e `manifesto.json`
com `sha256`.

**Nota de leitura:** o diagnóstico de cardinalidade reporta 29/36/40 e o auditor
reporta 30/37/41. A diferença é de +1 e tem causa conhecida: o diagnóstico
remove da contagem o turno da própria query, o auditor não. Nenhum dos dois
alcança 50; a diferença não muda veredito, mas está registrada porque dois
números diferentes para a mesma coisa sem explicação é como começa uma errata.

## Critérios de conclusão (item 13) — conferidos

| critério | estado |
|---|---|
| entrada válida → executa | ✅ caso A |
| entrada inválida → bloqueia | ✅ B–H |
| problema de ranking → diagnóstico correto | ✅ com evidência numérica |
| problema de procedência → bloqueia | ✅ |
| problema estatístico → bloqueia | ✅ prevalência e clusters |
| artefato inválido → não entra | ✅ `INVALID` |
| resultados com manifest + hashes + status | ✅ sha256 do manifesto inteiro |

**MVP-0 concluído.** 192 testes passando.

## O que NÃO foi construído, de propósito

- **API HTTP** — CLI primeiro (item 10);
- **execução de juiz dentro do pipeline** — a etapa registra configuração; a
  coleta continua no harness do REL-001;
- **Question Mining / Reddit** — módulo futuro, alimenta o dataset de queries e
  não substitui o mecanismo de auditoria (item 11);
- **isolamento entre clientes, limites de uso, retenção** — o MVP-0 roda local;
- **correção do `_hybrid_index`** — permanece defeito de produção declarado e
  não consertado (item 5).

## Auditar não altera o auditado

`MemoryStore.retrieve` incrementa `acessos`/`ultimo_acesso` e salva. O adaptador
do EDP **copia o store** antes de consultar, e há teste garantindo que o arquivo
de origem não muda. Um serviço que altera o sistema do cliente ao medi-lo não
está medindo o sistema do cliente.

## Matriz de decisão do REL-001 (item 12) — agora informada por medição

| opção | preserva o sujeito atual? | altera protocolo? | altera produção? |
|---|---|---|---|
| corrigir `_hybrid_index` | **não** | não no texto, sim na prática | **sim** |
| deduplicar só na auditoria | **não** | sim na prática | não |
| reduzir a cauda (20–35) | parcialmente | **sim** | não |
| novo protocolo | novo experimento | **sim** | não |
| expandir corpus externo | — | — | — |

**A última linha está resolvida por medição e sai da matriz.** Consultando o
ranking inteiro, cada query tem 112–132 ids distintos e 98–118 textos distintos;
50 de 50 passam dos 50. O corpus não é o gargalo — a duplicação consome a janela.

**O que a matriz não mostra:** deduplicar **renumera as posições**. A posição 30
do ranking deduplicado é ~45 no de produção. `"posições 20–50 do mesmo
retriever"` passa a apontar outro conjunto sem que uma linha do pré-registro
mude. A escolha não é só quanto material existe — é **de qual ranking o §3.2
fala**.

Nada disso é escolha do agente. Decisão pendente.
