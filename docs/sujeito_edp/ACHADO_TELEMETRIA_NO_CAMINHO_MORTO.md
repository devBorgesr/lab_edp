# Achado — a telemetria de ranking ficou no caminho que a produção não percorre

**2026-08-18.** Defeito meu, de 13/08. Descoberto por telemetria vazia depois
de quatro turnos reais, não por teste.

---

## O defeito

```
store.py:1494   def retrieve(...)                      ← o websocket chama AQUI
store.py:1511       if EDP_HYBRID_RETRIEVAL:
                        return self._retrieve_hybrid(...)   ← produção sai AQUI
store.py:768            emit_ranking_decision(...)          ← eu instrumentei AQUI
config.py:53    EDP_HYBRID_RETRIEVAL default = "1"      ← desde 08/07
```

O `return` da linha 1511 sai antes de chegar perto do código instrumentado.
**Zero eventos não era bug de emissão; era código morto no caminho vivo.**

E o comentário logo acima do despacho diz *"flag DESLIGADA por padrão"* —
falso desde a promoção de 08/07, quando o default virou `"1"`. Eu li esse
comentário e acreditei nele.

---

## O que me fez perceber

Não foi teste, não foi revisão. Foi **um número que não apareceu**.

O pesquisador ligou `EDP_RANKING_TELEMETRY=1`, conversou quatro turnos, e a
verificação devolveu:

```
correlation_id: 6/80   ← a outra correção FUNCIONOU
eventos: {... 'token_usage': 38}   ← ranking_decision AUSENTE
```

O contraste foi o gatilho. Se as duas correções tivessem falhado juntas, a
hipótese natural seria "as flags não pegaram". Uma funcionando e a outra não,
com a mesma flag lida no mesmo import, **elimina a causa comum** — e sobra
"o código não roda", que é qualitativamente diferente de "o código falha".

O log confirmava que o retrieve tinha rodado (`memory | hits=6`, `hits=7`).
Então: retrieve rodou, emissão não. Ou a emissão está condicionada a algo
que não valeu, ou ela não está no caminho.

---

## Como cheguei na causa

Três passos, e o segundo é o que decidiu:

1. **Onde está a emissão?** `grep emit_ranking_decision` → um só call site,
   linha 768.
2. **Quantos caminhos de retrieve existem?** Essa foi a pergunta certa, e ela
   veio de memória de trabalho anterior, não de raciocínio novo: dois dias
   antes, ao instrumentar o `contradiction_flagger`, eu tinha lido **dois**
   call sites de `scan_results` — `store.py:1594` e `:1808` — o segundo
   marcado `# P3: contradiction flagging (paridade)`. Aquela palavra
   *paridade* ficou. Ao ver um só call site do ranking, a assimetria saltou.
3. **Qual roda?** `grep EDP_HYBRID_RETRIEVAL` no config → default `"1"`.
   Fecha.

O passo 2 é o interessante: **a pista estava numa leitura de dois dias antes,
sobre outro subsistema.** Eu tinha visto os dois caminhos, anotado a paridade
no meu próprio relatório, e instrumentado um só. O erro e a evidência do erro
estavam na mesma sessão.

---

## Por que os 12 testes de 13/08 não pegaram

Todos exercitam **a função que eu instrumentei**, ou a fonte dela:

- `test_cascata_completa_e_gravada` — chama o emissor direto
- `test_nf_floor_esta_no_dict_do_ranking` — lê a fonte de `EpisodicMemory.retrieve`
- `test_flag_off_nao_emite` — ordem de leitura da flag na mesma função

Nenhum pergunta **se a produção chega lá**.

E isso é exatamente a **prova de inércia** que apliquei ao `memory_graph` no
mesmo dia — *"alguém importa este módulo?"* — e não apliquei ao meu próprio
código. Verifiquei que estava correto; não verifiquei que roda.

A guarda dos dez fatores foi provada por mutação e é boa. Ela prova que o
dicionário tem os dez. Não prova que alguém o lê.

---

## A correção, e por que o esquema mudou

O híbrido **não tem a mesma cascata**. `ranking_breakdown` ali é
`{method, bm25, vec}` — três campos, não os dez multiplicativos. Não há filtro
de sessão nem `filtro_recusa`; há um `_dedup_ranked` que o cosseno não tem.

Emitir o mesmo esquema com os números repetidos faria a cascata **parecer
completa** e descreveria filtros que não rodaram. Zero pareceria corte total.
Por isso:

- campo `metodo` (`"cosine"` | `"rrf"`) — sem ele, dois formatos de `detalhe`
  ficariam indistinguíveis no mesmo arquivo, e qualquer análise que somasse os
  dois estaria errada
- `None` onde o estágio **não existe**, em vez de repetir o anterior
- `n_apos_dedup`, que só o híbrido tem

## O teste que faltava

`tests/test_ranking_telemetry_caminho_vivo.py` entra por
`MemoryStore.retrieve` — o ponto que o websocket chama — falsificando só o
índice e o embed. O **despacho** roda de verdade.

Provado por mutação: removendo a emissão do híbrido (estado de 13/08),
**5 dos 7 testes falham**. Os 12 antigos continuavam todos verdes.

E um deles trava a lição como mecanismo:
`test_ambos_os_caminhos_tem_emissao_na_fonte` exige exatamente **dois** call
sites — nem um, nem três.

---

## O que isto obriga a reconferir

Os outros dois canais de 13/08 têm a mesma pergunta em aberto:

- **`contradiction_scan`** — instrumentei dentro de `scan_results`, que é
  chamada dos dois caminhos. *Provavelmente* certo.
- **`reflection`** — está em `pipeline.py`, que a produção chama.
  *Provavelmente* certo.

**"Provavelmente" foi exatamente o que me custou este defeito.** Os dois
precisam da mesma verificação: entrar pelo ponto vivo e exigir o evento.
