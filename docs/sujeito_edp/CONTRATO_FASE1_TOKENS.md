# Contrato da Fase 1 — o que é uma amostra

**2026-08-12.** Documento curto e de referência única: define a **população
experimental** da coleta de tokens do EDP. Existe porque a Fase 2 vai carregar
um arquivo JSONL e precisa saber, sem interpretar, quais linhas são observação
e quais não são.

Spec e nota de execução: [`AUDITORIA_FASE1_TOKENS.md`](AUDITORIA_FASE1_TOKENS.md).
Protocolo agnóstico de sujeito: [`../instrumentos/PROTOCOLO_TELEMETRIA_DE_TOKENS.md`](../instrumentos/PROTOCOLO_TELEMETRIA_DE_TOKENS.md).

---

## 1. O que é uma amostra válida

Um evento `token_usage` que satisfaz **todas** as condições abaixo. A
autoridade não é este texto — é `edp.runtime.pareto_store.amostra_valida_fase2`,
e o harness da Fase 2 **importa a função** em vez de re-derivar o filtro:

```
event == "token_usage"
  AND format_state is not None      # veio de um turno, com regime conhecido
  AND provider == "anthropic"       # único instrumentado
  AND usage.input_tokens is not None
  AND usage.output_tokens is not None
```

O predicado existe em código, e não só aqui, porque a regra em prosa tem um
modo de falha conhecido e barato: alguém escreve `carrega_tudo()`, esquece o
filtro, e a contaminação volta pela porta que o `format_state` foi criado para
fechar.

## 2-3. Três classes de chamada, e por que só uma é observação

| classe | caminho | emite? | `format_state` | destino |
|---|---|---|---|---|
| **A — observação** | turno principal (`chat` / `stream_chat`) | sim | regime | **entra** |
| **B — auxiliar** | Echo Chamber (`_llm_call_for_chamber`), `cognitive_decisions` (background) | sim | `None` | fica gravada, fora do estrato |
| **C — operacional** | `AnthropicProvider.validate()` | **não** (`telemetria=False`) | — | não existe |
| — | provider Ollama | não instrumentado | — | fora do dataset |

**Por que B grava em vez de descartar:** são chamadas legítimas ao mesmo
provider, com token real, mas de composição própria — system de refutação na
câmara, prompt de extração congelado no `cognitive_decisions`. Não são
inválidas; são **outra população**. Descartar na emissão perderia dado que
pode servir a outra pergunta; misturar responderia a pergunta errada.

**Por que C não grava:** `validate()` manda o prompt `"1"` com `max_tokens=1`
para testar credencial. Não é turno, e em prompt minúsculo o andaime JSON
domina (medido: 379 bytes de fio para 194 chars de texto), então a amostra
puxaria a razão do estrato inteiro.

**A câmara é o caso que exigiu correção ativa**, não omissão: roda dentro do
turno, na **mesma thread**, e por isso herdaria o `format_state` por acidente.
Metadado falso é pior que metadado ausente — carimbar o prompt da câmara com o
regime do prompt principal afirmaria algo que não é verdade sobre a amostra.
`_llm_call_for_chamber` limpa o regime antes da chamada e restaura no
`finally`.

## 4. Campos do `format_state`

| campo | conteúdo |
|---|---|
| `schema_version` | `1` |
| `mode` | `cognitive` \| `sprint` |
| `caps` | caps efetivos da janela imediata, de `CAPS_POR_MODO` |
| `flags` | 10 booleanos: as 9 de `config.FORMAT_STATE_FLAGS` + `EDP_USE_CTX_MGR` |

`caps` grava o **estado efetivo**, não a configuração que o implica: `mode`
sozinho obrigaria quem analisa a reconstruir "logo, o cap era 12000".

`EDP_USE_CTX_MGR` está na lista explicitamente porque é lida de `os.environ`
direto no `llm_adapter`, não do `config.py` — o teste de completude varre o
`config.py` e **não a pegaria**. É a única flag fora do módulo e a mais
disruptiva do conjunto: troca `_build_enriched_context` pelo fallback.

## 5. Como o hash é calculado

`sha256(json.dumps(format_state, sort_keys=True, separators=(",",":")))[:16]`.

`sort_keys=True` não é cosmético: sem ele, dois dicts com o mesmo conteúdo e
ordem de inserção diferente dariam hashes diferentes, e a Fase 2 veria dois
regimes onde só há um. O hash não carrega informação nova — é derivável dos
campos — e é isso que o torna barato. O que ele muda é a natureza da garantia:
de "confie que a configuração era a mesma" para "prove qual regime produziu
esta amostra", agrupando por igualdade de string em vez de comparação de dicts
aninhados.

## 6. O que MUDA o hash

Modo operacional (`/mode sprint`), qualquer uma das 10 flags, os caps.

## 7. O que NÃO muda o hash

Qualquer alteração de **código**: `JANELA_IMEDIATA_N` (local a
`_retrieve_context`), `BLOCO_CAP_CHARS`, o texto dos templates de prompt, a
lógica de montagem de contexto.

## 8. Limite runtime vs. código — declarado, não resolvido

**Duas amostras de builds diferentes podem ter `format_hash` idêntico.** O
snapshot captura o regime de *runtime*, não o de *código*.

Consequência operacional: **coleta que atravesse um deploy que mexa em
composição de prompt precisa ser cortada na data do deploy, à mão.** Nada no
mecanismo detecta isso.

Decisão explícita de **não fechar agora**: carimbar o commit mudaria a pergunta
que o hash responde, de *"qual regime operacional estava ativo?"* para *"qual
implementação exata produziu isto?"*. São dois eixos, e misturá-los num só
hash impediria analisar `mesmo runtime × build A vs build B` como cruzamento de
dois fatores. Se for fechado, o desenho é `runtime_regime_hash` **+**
`code_revision`, lado a lado — não fundidos.

## 8-bis. O que o snapshot afirma — e o que não afirma

**Afirmação errada, que este documento não faz:** "o `format_state` prova o
estado com que o prompt foi montado."

**Afirmação correta:** o `format_state` registra o estado de runtime observado
**no início do turno**. O prompt é montado depois, dentro do mesmo turno.

Entre os dois pontos existe uma janela. `_operational_mode` é atributo de
instância do runtime por sessão, e os dois pontos de mutação —
`api/routes/mode.py:50` e `api/routes/websocket.py:379`, ambos chamando
`set_operational_mode` (`llm_adapter.py:1016`) — rodam em requisições, logo em
threads, diferentes de um turno em voo. Um `/mode sprint` que caia nessa janela
faz a amostra afirmar `caps=[4000,…]` enquanto o prompt foi montado com
`[12000,…]`.

É a mesma classe do defeito da câmara — **metadado falso, não ausente** — só
que por corrida em vez de por herança. Janela estreita, sistema single-user;
na prática, rara.

**Não foi corrigida de propósito.** O conserto mexeria no caminho vivo
(re-snapshot na montagem do prompt, ou o turno passar a ler o modo do próprio
snapshot), e não é pré-requisito para coletar. É decisão da Fase 2 ou de
depois, não buraco pendente da Fase 1.

**Vira condição de suspeição analítica, não descarte.** `emit_mode_switched`
já grava `ts` a cada troca, de graça. A Fase 2 marca como suspeita qualquer
amostra cujo turno se sobreponha a um `mode_switched` — e **reporta o número**,
em vez de apagar as amostras em silêncio (ver §10).

## 9. Provider coberto

Só Anthropic. Ollama não emite. Isso não enviesa a razão — ela é propriedade
do tokenizador e do conteúdo, e o tokenizador é o da Anthropic de qualquer
forma — mas restringe a população, e o campo `provider` vai gravado em cada
amostra para que a restrição seja **checável** e não presumida. Hoje
`"anthropic"` é redundante; no dia em que o Ollama for instrumentado, amostra
antiga sem o campo viraria ambígua retroativamente, sem como desambiguar.

## 10. Regra de filtragem da Fase 2

```python
from edp.runtime.pareto_store import amostra_valida_fase2

amostras = [e for e in store.query(event_type="token_usage")
            if amostra_valida_fase2(e)]
estratos = collections.defaultdict(list)
for a in amostras:
    estratos[(a["format_hash"], a["classe"])].append(a)
```

**Toda redução de N tem de ser explicável.** A Fase 2 reporta a cascata, não
só o número final — porque agora existem amostras **estruturalmente bem
formadas e epistemicamente suspeitas** (§8-bis), e um `n=500` solto esconde a
diferença:

```
coleta bruta                        N
├── provider == anthropic           N
├── format_state presente           N
├── tokens completos                N
├── população Fase 2                N   ← amostra_valida_fase2()
├── sobrepostas a mode_switched     N   ← suspeitas, contadas
├── excluídas                       N
└── analisadas                      N
```

Estratificar por `format_hash` **e** por `classe` de conteúdo
(`acentuado`/`codigo`/`ascii`): são dois eixos independentes — regime de
formato e regime de tokenização. Os sinais crus (`sinais`) vão gravados junto
do rótulo, então a Fase 2 pode re-particionar com outros limiares sem
recoletar.

---

## Pendências declaradas

- **Custo do snapshot no caminho vivo não foi medido.** Com a flag OFF é um
  `if`. Com ON: leitura de 10 atributos + `json.dumps` + sha256 por turno, mais
  uma passada no prompt. Provavelmente desprezível ao lado da latência de
  inferência — mas isso é uma expectativa, não uma medição, e não vai declarada
  como "sem impacto".
- **O pré-registro da Fase 2 não existe.** Este contrato define a *população*;
  não define hipótese, limiar, regra de parada nem n mínimo por estrato. Sem
  isso a coleta pode começar, mas a análise não.
