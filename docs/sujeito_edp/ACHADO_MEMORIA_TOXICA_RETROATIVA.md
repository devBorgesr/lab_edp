# Achado — a defesa contra memória tóxica é cega para trás

**2026-08-18.** Observado in vivo pelo pesquisador, verificado no store real.

---

## O sintoma

Pergunta vaga de continuação — *"onde estamos na nossa última conversa?"* — e o
EDP responde **"não tenho registro de uma última conversa anterior a esta"**,
tendo 158 entradas episódicas, incluindo a conversa de cinco dias antes.

O log do turno mostra por quê. Das cinco memórias recuperadas, **quatro eram
`session_summary`**, e duas delas dizem literalmente:

```
[há 2 meses, session_summary] "Nada. Esta é a primeira mensagem da conversa...
                               Não tenho memória entre conversas."
```

**O modelo leu isso e repetiu.** A resposta "não tenho memória" veio da própria
memória.

Na pergunta seguinte, **específica** (*"e sobre adão e eva?"*), o retrieval
acertou e trouxe a conversa de 5 dias inteira. Reproduz exatamente o padrão de
`DIAGNOSTICO_SESSION_SUMMARY.md §2`: query específica → cosseno vence; query
vaga de continuação → summary domina.

## O que foi medido

Sobre `edp_data/sessions/default_cognitive/episodic.json`:

| | |
|---|---|
| `session_summary` no store | **32 de 137** (23%) |
| com `answer_class` (carimbo do exp012) | **0** |
| a que diz "não tenho memória" | `answer_class=None`, **`acessos=20`** |

## O defeito, e ele é estrutural

O `exp012`/`exp016` criaram exatamente a defesa para isto: `answer_class ∈
{not_found, disqualification}` dispara `NOT_FOUND_FLOOR = 0.05` e derruba o
score em 20×. A tese é correta — *uma resposta que diz "não encontrei" não pode
virar memória bem ranqueada*.

**Mas o carimbo nasceu depois do veneno.** Nenhuma das 32 `session_summary`
tem `answer_class`, porque foram escritas antes de `EDP_WRITE_PROVENANCE`
existir. A defesa protege o futuro e é cega para o passado — e as memórias
mais tóxicas para perguntas de continuação são justamente as antigas.

Mais fundo: o sistema guarda **os próprios relatos de fracasso com o mesmo
status do conhecimento**. Um resumo de "não achei" fica no mesmo store, com os
mesmos dez fatores de ranking, que um resumo de "chegamos a esta conclusão".
Nada os distingue estruturalmente além de um carimbo que estas não têm.

## E piora com o uso

O retrieve incrementa `acessos` (`memory/store.py`), que alimenta
`access_boost = 1 + 0,05·ln(1+n)` (`temporal.py:42`). Cada recuperação sobe o
rank da próxima vez.

**É um desvio de rota que se fortalece com o uso.** Quanto mais se pergunta
"você lembra?", mais alto sobe a memória que responde "não". A entrada em
questão chegou a `acessos=20` sendo escolhida repetidamente.

## Analogia, e onde ela quebra

Registrada porque foi ela que expôs o mecanismo: *"é igual a uma pessoa com
dislexia"* — capacidade intacta, relato falso sobre ela, e sistemático.

Acerta nisso. Quebra no mecanismo: na dislexia o problema é **decodificar**.
Aqui a recuperação funcionou perfeitamente — leu a página errada, e a página
errada é um bilhete dizendo "este livro está vazio".

E quebra numa direção pior: dislexia não piora a cada leitura. Isto piora.

## Dois caminhos, nenhum tomado aqui

- **exp009** foi pré-registrado em julho para exatamente isto — remover os
  privilégios de nascença das `session_summary`. Estava dado como bloqueado
  por corpus numa medição feita contra o store errado; no store real são 50
  domínios e ele **roda**.
- **Backfill do carimbo** nas 32 antigas, com dry-run antes de aplicar —
  o `exp016` já tem precedente exato desse procedimento.

Achado, não correção.

---

## ERRATA — 18/08/2026, algumas horas depois

**Duas afirmações acima descrevem o caminho COSSENO, e a produção roda o
HÍBRIDO desde 08/07.** Medido em `store.py`, dentro de `_retrieve_hybrid`:

```
access_boost   0 ocorrências      nf_floor       0
prioridade     0                  session_boost  0
epi_mult       0                  src_weight     0
dom_penalty    0                  anchor_boost   0
acessos        6  ← só para INCREMENTAR, nunca para pontuar
```

O `HybridRetriever` pontua com **BM25 + vetor + RRF**. Nada mais.

### O que CAI

**"Piora com o uso" está errado em produção.** Escrevi que cada recuperação
incrementa `acessos` → alimenta `access_boost` → sobe o rank da próxima vez.
O `acessos` é incrementado, sim — e **nunca lido pelo ranking híbrido**. O
laço auto-reforçado que descrevi **não existe no caminho vivo**. Ele existe no
cosseno, que não roda desde 08/07.

**E o "piso de 20×" também não.** `NOT_FOUND_FLOOR` tem zero ocorrências no
híbrido.

### O que SOBREVIVE, e com mecanismo diferente

A governança **existe** no híbrido, mas como **exclusão no índice**, não como
rebaixamento no ranking (`store.py:1645-1662`):

```python
if e.get("epistemic_status") in ("contradicted", "quarantined"):  continue
if _WP12 and e.get("answer_class") in _TAC12:                     continue
if _recusa(e["text"]).get("confianca") == "alta":                 continue
```

É **binário**: dentro ou fora. Não há meio-termo graduado.

E o achado central continua de pé, com a causa correta: as 32
`session_summary` têm `answer_class = None`, então **passam pela exclusão** e
competem em pé de igualdade. A defesa é retroativamente cega — só que o que
ela deixa passar não é "rebaixado 20×", é **plenamente competitivo**.

### E a dominância vem de onde, então

De **similaridade pura**. Aqueles resumos são longos, genéricos e
semanticamente centrais — exatamente o que vence tanto no BM25 quanto no
vetor quando a query é vaga. Não precisam de boost nenhum.

Isso é pior que o diagnóstico original, não melhor: **não há um privilégio
para remover.** Eles ganham no mérito da métrica.

### Consequência que quase me fez recomendar a coisa errada

Eu ia sugerir o **exp009** como o passo seguinte — ele foi pré-registrado em
julho para "remover os privilégios de nascença das `session_summary`
(prioridade alta + verified)". Mas `prioridade` e `epistemic_status`
**não entram no ranking híbrido**. O exp009 mediria a remoção de privilégios
que a produção não concede.

A H1 dele pode estar vazia hoje — não por refutação, por mudança de
substrato. Isso precisa ser verificado antes de qualquer disparo.
