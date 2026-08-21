# Pré-registro — EDI-001
## Existe sinal preditivo entre histórico decisório e desfecho, no próprio corpus do EDP?

**Congelado em 21/08/2026, ANTES de qualquer modelagem.**

Destino: `edp_engineering/docs/preregistrations/` quando o repositório existir.
Mora aqui enquanto isso porque **certificação experimental é função do lab** —
o repositório do agente não certifica a si mesmo (ver §7.3).

---

## §1. Motivação — o gargalo é corpus, e este corpus existe

A auditoria de 20/08/2026 concluiu que a capacidade de medição do EDP cresceu
mais rápido que a fonte de dados: experimentos pedindo N=40 com 6 disponíveis,
Fase 2 pedindo ~300 com 83, guarda de escrita pedindo 20–30 com 6.

O pivô proposto ataca isso usando **histórico decisório de produto** como corpus.
Este experimento testa a premissa **no próprio EDP**, antes de qualquer conversa
com empresa, porque aqui existem as duas metades que raramente coexistem:

| metade | onde | volume medido |
|---|---|---|
| **o quê** (decisão + desfecho) | `git log` | 278 commits kernel |
| **o porquê** (raciocínio) | sessões `.jsonl` | 6.056 mensagens elegíveis |

## §2. Hipótese (declarada antes do dado)

- **H1:** Um modelo com acesso a Git **e** conversas prevê o desfecho de uma
  decisão melhor que baselines que usam só uma das metades ou só heurística de
  churn.
- **H0:** Não prevê melhor. O sinal, se existir, é capturado por heurística
  trivial — e a integração decisão-raciocínio não agrega.

**H0 vencer é publicável e acionável**: mata o pivô cedo, por 233 exemplos, em
vez de depois de construir conectores e vender a tese.

## §3. Corpus e corte temporal (medidos, não estimados)

**Cutoff: `2026-08-11`**, imposto pela Regra 2 de `docs/AVISO_INSTANCIA_LIMPA.md`
(sessões a partir dessa data são desqualificadas por exposição a gabarito).

**O corte é por MENSAGEM, não por arquivo.** Medido: a maior sessão tem 10.555
linhas e atravessa 06/08 → 21/08 — 63% do corpus local. Filtrar por arquivo
descartaria essa fração inteira ou a contaminaria inteira.

```
mensagens totais (todas as linhas) ....... 16.737
  sem timestamp (metadados: ai-title,
  mode, snapshots — não são conversa) .....  3.305
conversa (user+assistant) com timestamp ..  9.785
  ELEGÍVEL   (< 2026-08-11) ..............  6.056   (61,9%)
  EXCLUÍDA   (>= 2026-08-11) .............  3.729   (38,1%)

commits: contexto (< cutoff) ............     233
         janela de desfecho (>= cutoff) ..      45
janela de observação ....... 2026-08-11 → 2026-08-20
```

### §3.1 Uma interpretação que precisa de confirmação, não de suposição

A Regra 2 exclui **sessões** do corpus. Este desenho usa **commits posteriores
ao cutoff como rótulo de desfecho** — não como features. A leitura adotada é que
commits não são sessões e não carregam exposição a gabarito.

**Isto é interpretação, não fato.** Se o pesquisador entender que a Regra 2
alcança qualquer artefato posterior a 11/08, a janela de desfecho desaparece e
este experimento não roda. A decisão fica registrada aqui em vez de embutida no
código.

## §4. Rótulos hierárquicos — e três não têm classe

Desfecho observado APÓS cada commit do contexto, olhando só o futuro dele.
Distribuição **medida**, não prevista:

| rótulo | n | % | armado? |
|---|---|---|---|
| `untouched` | 84 | 36,1% | — (negativo) |
| **`revised_soon`** (≤3 commits) | **83** | 35,6% | **sim — EDI-001A** |
| **`revised_later`** (>3 commits) | **62** | 26,6% | **sim — EDI-001B** |
| `reverted` | **0** | 0,0% | **NÃO — classe vazia** |
| `incident` | **0** | 0,0% | **NÃO — não há dado de incidente** |
| `errata` explícita | **4** | 1,7% | **NÃO — sem poder (§6.2)** |

**`revised_soon` é rótulo abundante com significado fraco.** Tocar o mesmo
arquivo em até 3 commits é majoritariamente iteração normal, não decisão ruim.
Isso está declarado aqui para que um resultado positivo em EDI-001A **não** seja
lido como "o EDP prevê decisões erradas". Ele prevê **revisitação**.

`revised_later` tem significado menos diluído — arquivo retomado bem depois tem
chance maior de ser revisão real — ao custo de N menor.

## §5. Baselines — quatro pernas, e a terceira é a que decide o produto

| | dados | o que isola |
|---|---|---|
| **B0** | prevalência / aleatório | piso |
| **B1** | só Git — churn, nº de arquivos, idade, frequência | o sinal é trivial? |
| **B2** | só conversas | o valor está no raciocínio? |
| **B3** | Git + conversas + EDP (retrieval, lineage, proveniência) | a **integração** vale? |

**B2 é obrigatório e é o mais informativo dos quatro.** Se B2 empatar com B3, o
valor não está na ligação decisão↔desfecho — está no rastro de raciocínio, e o
produto a construir é outro. Sem essa perna, um B3 vitorioso seria
inconclusivo quanto à própria tese.

## §6. Métricas e critério (poder MEDIDO antes da coleta)

Primária: **AUC** (`revised_soon` e `revised_later` separadamente).
Secundárias: PR-AUC, precision@10, calibração. Não entram no critério.

**H1 confirmada** se, em EDI-001A **ou** EDI-001B, o IC 95% do AUC de **B3**
exclui 0,50 **E** exclui o AUC pontual do melhor entre B1 e B2.

IC por bootstrap estratificado, 20.000 réplicas, `SEED = 20260821`.

### §6.1 Poder simulado (4.000 réplicas por célula)

| rótulo | P/N | AUC 0,60 | AUC 0,65 | AUC 0,70 |
|---|---|---|---|---|
| `revised_soon` | 83/150 | [0,53 ; 0,67] ✔ | [0,57 ; 0,72] ✔ | [0,63 ; 0,77] ✔ |
| `revised_later` | 62/171 | [0,52 ; 0,68] ✔ | [0,57 ; 0,73] ✔ | [0,62 ; 0,77] ✔ |
| `errata` | 4/229 | [0,31 ; 0,87] ✘ | [0,37 ; 0,89] ✘ | [0,43 ; 0,93] ✘ |

`MDE_DECLARADA = 0.60` — as duas pernas armadas detectam efeito fraco.

### §6.2 Declarado, não escondido (NORTE §4.3)

**A perna `errata` NÃO roda.** Com split temporal honesto, as 13 erratas do
repositório colapsam para **4** — nove delas se referem a commits posteriores ao
cutoff e portanto não são previsíveis a partir do contexto elegível.

Com 4 positivos, o IC do AUC não exclui 0,50 nem para efeito forte. Rodar
produziria "inconclusivo" garantido, e um inconclusivo garantido não é
resultado — é gasto.

`reverted` e `incident` têm **classe vazia**: zero reverts no repositório, e não
existe fonte de incidente. Não são "não medidos"; são **inexistentes neste
corpus**.

## §7. Anti-mock, vazamento e isolamento

**§7.1 — Vazamento temporal é a ameaça principal.** Nenhuma feature pode derivar
de informação posterior ao commit avaliado. Concretamente: proibido usar
contagem futura de modificações, mensagem de commit posterior, ou qualquer
mensagem de sessão com `timestamp` maior que o do commit.

O harness **falha** se qualquer feature tiver dependência de índice futuro. Não
é aviso em comentário — é asserção.

**§7.2 — O rótulo não entra nas features.** As mensagens de commit que contêm
`errata`/`revert` são o rótulo; o texto delas fica fora do conjunto de features
dos commits que elas corrigem.

**§7.3 — O agente não pode certificar a si mesmo.** Este pré-registro mora no
`lab_edp` e não no `edp_engineering` por isso. Quando o terceiro repositório
existir, cada commit feito pelo agente entra no histórico que o agente analisa —
e essa é a razão arquitetural de separar os repositórios, não organização.

## §8. Constantes congeladas (espelhadas em `edi_001.py`)

| constante | valor |
|---|---|
| `EXPERIMENTO` | `"EDI-001"` |
| `CUTOFF` | `"2026-08-11"` |
| `N_CONTEXTO` | `233` |
| `N_CONVERSA_ELEGIVEL` | `6056` |
| `LIMIAR_REVISED_SOON` | `3` |
| `ALPHA` | `0.05` |
| `MDE_DECLARADA` | `0.60` |
| `N_BOOTSTRAP` | `20000` |
| `SEED` | `20260821` |
| pernas armadas | `revised_soon`, `revised_later` |

**CONGELADO ao primeiro disparo real. Mudou a régua → é o EDI-002.**

## §9. O que este experimento NÃO responde

**Não generaliza para equipes humanas.** O raciocínio deste corpus foi produzido
por **um agente**, e os rótulos de errata foram escritos pelo **mesmo agente**.
Um resultado positivo demonstra que existe sinal previsível entre rastro de
raciocínio e desfecho — **não** que equipes humanas deixem rastro equivalente.
Equipe humana produz commit lacônico e conversa fragmentada, não transcrição
verbosa.

Esta é a distinção mais importante do documento, e vale o §4.12: **o resultado
vale para o corpus registrado e para nenhum outro.** Vender EDI-001 positivo
como evidência de generalização corporativa seria a única desonestidade
disponível neste projeto.

**Não prevê "decisão errada".** Prevê revisitação. A escada até `errata` fica
para quando houver N.

**Não mede utilidade.** Prever que um arquivo será revisitado não estabelece que
avisar disso melhora a decisão. Isso é EDI-004 ou posterior.

**Não é o produto.** É o teste da premissa do produto, feito com o corpus mais
barato disponível e com escopo declarado.
