# Diagnóstico de Retrieval — piloto zero

**Uma página. Se algo aqui não bater com o que você recebeu, é defeito nosso.**

## O que é

Uma medição técnica reproduzível do material que o seu retriever devolve.

**Não é auditoria de qualidade, não é certificação, e não calcula Recall@K.**

## Você fornece

- **acesso ao retrieval** — um adaptador de ~40 linhas com quatro métodos;
- **corpus/snapshot** — o diretório dos seus documentos;
- **perguntas reais** do seu domínio.

## Nós entregamos

| | |
|---|---|
| `reports/executive.md` | uma página: status, o que foi medido, o que **não** foi |
| `reports/technical.md` | a evidência completa |
| `manifest.json` | fonte de verdade, com `sha256` de tudo |
| `artifacts/checks.json` | cada verificação e o defeito que ela detecta |

## O que medimos

| medição | o que é |
|---|---|
| cardinalidade do ranking | documentos **distintos** por pergunta |
| duplicação por id | fração dos slots ocupados por id repetido |
| duplicação por texto | documentos com id diferente e texto idêntico |
| Jaccard entre perguntas | quanto do material se repete entre perguntas |
| razão de score topo/cauda | quão discriminativo é o ranking |

Cada número vem com `N`, unidade e intervalo de confiança.

## O que NÃO medimos

- qualidade das respostas;
- Recall@K, precisão, ou comparação com conjunto de referência;
- relevância — **nenhum julgamento** é feito;
- conformidade ou certificação.

E **não dizemos se um valor é alto ou baixo**: não há linha de base. Com poucos
sistemas medidos, chamar um valor de anômalo seria opinião com aparência de
medida.

Descrevemos **o que foi recuperado**, não **se o que foi recuperado era o certo**.

## Tempo

| | |
|---|---|
| `check` (validação) | **milissegundos** |
| `run` (diagnóstico) | segundos — medido: ~2 s para 220 documentos e 40 perguntas |
| chamadas a modelo de linguagem | **zero** |

## `COMPLETE` e `BLOCKED`

**`COMPLETE`** — executou; você recebe as medições.

**`BLOCKED`** — *aquela régua* não pôde ser executada sobre *aquele sistema*.
Não é erro nosso, e **não diz que o seu sistema é ruim**: outra régua pode se
aplicar. O relatório diz qual pré-condição falhou.

Você ainda recebe as medições descritivas sob `BLOCKED`, desde que o ranking
tenha procedência provada.

O único caso sem medição nenhuma é ranking sem procedência — medir sobre
ranking não verificado não mede nada.

**`READY` no `check` não garante `COMPLETE` no `run`**: o dry-run confere
procedência, e a cardinalidade só é medida com todas as perguntas.

## Privacidade

Query e documento **nunca** aparecem em claro por caminho automático — o que
aparece é hash. Credencial é removida sempre. O seu snapshot é **copiado**
antes de qualquer consulta: auditar não altera o auditado.

Retenção: material bruto 7 dias, relatórios 90, manifesto 365. **A expiração é
um comando que o operador agenda** — se ninguém agendar, nada expira. Está
dito assim de propósito.

## Suporte

Escreva para quem lhe enviou este pacote. Se algo não bater com o
`SERVICE_CONTRACT.md`, é defeito nosso, e queremos saber.

---

*Este é um piloto. O serviço nunca rodou com material de um cliente externo
antes do seu.*
