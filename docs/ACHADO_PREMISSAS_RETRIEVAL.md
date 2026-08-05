# ACHADO — premissas herdadas sobre retrieval e implantação não bateram com o checkout

Data: 05/08/2026. Origem: verificação de Passo 0 do plano E8
(`docs/plano_experimento_e8.md`), interrompida antes da execução por
conflito de escopo com `NORTE.md`. Três achados sobrevivem à interrupção e
ficam registrados aqui — nenhum exige medição para valer, todos são
leitura de código/documentação ou busca por evidência de processo, não
execução do retrieval em si (que segue congelada, é tarefa 0.1 da Fase 0).

## (a) Não há instância implantada rodando neste ambiente

Busca por evidência de um "Chat Cognitivo" em execução — o sistema cujo
diagnóstico (retrieval quase aleatório, consolidação episódica ausente)
motivou a investigação original:

```
ps aux | grep -iE "edp|uvicorn|gunicorn|chat.?cognitivo|node|npm"
  → nenhum processo do EDP; só VSCode e ferramentas de IDE

ss -tlnp
  → só :22 (ssh) e portas locais do VSCode; nenhum servidor de aplicação

systemctl list-units --type=service --all | grep -i edp
  → vazio

docker ps -a
  → "no docker" (comando ausente/sem containers)

find <edp_v5> -iname "*deploy*" -o -iname "Procfile" -o -iname "*.service"
  → nenhum resultado
```

**Consequência:** o "Chat Cognitivo" é histórico, não corrente, neste
ambiente de verificação. Qualquer experimento futuro que meça o EDP
"como ele roda de verdade" precisa **estabelecer** onde e como esse
sistema está implantado antes de pinar um SHA — não presumir que a
branch mais avançada localmente (`fix/toxic-guards`) ou a mais estável
(`main`) é o que está no ar. Isto bloqueou a escolha de SHA do plano E8
(§3 do plano) e continua bloqueado.

## (b) Contradição parcialmente resolvida sobre o caminho de retrieval vivo

Afirmação herdada a verificar: *"o retrieval que o EDP roda hoje é
`cosine_similarity` força-bruta do sklearn; a flag de HNSW é decorativa;
FAISS não é usado."*

Resolvido por leitura direta (sem instrumentar nem executar) —
`edp/config.py:40-53`:

```python
# ── Retrieval híbrido (exp010, 07/2026) ────────────────────────────────
# DESLIGADO por padrão: com "0", MemoryStore.retrieve é EXATAMENTE o atual
# (cosine puro). Com EDP_HYBRID_RETRIEVAL=1, o retrieve usa o HybridRetriever
# (BM25+vetorial+RRF, SEM MMR — o exp010 mostrou MMR piorando neste tamanho de
# store). Evidência (exp010, H1 confirmada sobre dados reais): Recall@5
# 25%→87.5%, Redis 3/3 no top-5, session_summary 40%→10% do top-5 em queries
# vagas, guarda (pedidos de resumo) intacta.
# PROMOVIDO A DEFAULT ON (Fase 1, 08/07/2026) apos suite de regressao 3/3
# (R1 CP3 presente, R2 Recall 2/3, R3 SS 13.3%). Para DESLIGAR (reverter ao
# cosine antigo): EDP_HYBRID_RETRIEVAL=0 — a env var e a rede de seguranca.
EDP_HYBRID_RETRIEVAL = os.environ.get("EDP_HYBRID_RETRIEVAL", "1") == "1"
```

E `requirements.txt:16-17`:

```
faiss-cpu>=1.7        # ANN retrieval acelerado (10-100x mais rápido)
# hnswlib>=0.7        # alternativa ao FAISS para HNSW
```

**Refutado, pela metade:** com os defaults de `config.py`, o caminho vivo
é o `HybridRetriever` (BM25 + vetorial + RRF), promovido a default ON em
08/07/2026 — não cosine puro força-bruta. `faiss-cpu` está declarado como
dependência real (não comentada), `hnswlib` é que está comentado. A
afirmação herdada estava invertida neste ponto.

**Não resolvido, e propositalmente não perseguido agora:** qual
implementação a perna vetorial do `HybridRetriever` de fato usa — FAISS
real ou produto interno força-bruta chamado por trás de uma interface
com nome de FAISS. Resolver isso exige instrumentar uma chamada real
(log ou breakpoint), que é exatamente a tarefa 0.1 da Fase 0 do plano E8,
e está congelada junto com o resto do experimento. **Fica registrado como
a primeira coisa a fazer quando E8 for descongelado**, não como
pendência esquecida.

## (c) Linhagem de afirmações não verificadas — regra para prompts futuros

As afirmações de (b), mais outras três já confirmadas erradas em
`docs/VEREDITO_fix_corrupcao_json.md` ("Premissas do Passo 0 — refutadas,
registradas, não escondidas"):

- branch/SHA assumido (`main @ 67f2f5b`) — real era `fix/toxic-guards @ cf91c96`;
- 5 call sites assumidos — reais eram 7 (`edp/ingest/session_index.py` e
  `edp/profiles/registry.py` ficaram de fora da contagem original);
- `tests/test_health_check.py` "falhando na coleta" — passa limpo, 5/5
  (reconfirmado agora: `python3 -m pytest tests/test_health_check.py -q`
  → `5 passed`);

e um quase-erro adicional desta própria rodada: o prompt que originou o
plano E8 pedia para criar artefatos sob o nome `exp018`, sem verificar que
esse número já estava ocupado por um experimento fechado e sem relação
(`docs/VEREDITO_EXP018.md`, promoção tóxica) — pego antes de escrever
qualquer arquivo, não depois.

**A regra que sai disso:** afirmações desta linhagem — números de call
site, estado de branch, resultado de teste, próximo ID de experimento
livre, o que está ou não implantado — entram em qualquer prompt futuro
como **premissa a verificar**, nunca como **base de decisão**. Todo
prompt que as use precisa de um Passo 0 que as confirme na fonte (leitura
de código + execução real, não busca textual sozinha) antes de gastar
esforço no que vem depois. Isto não é desconfiança do autor do prompt —
é a mesma disciplina que este laboratório já aplica ao próprio dado
experimental, estendida à camada anterior: a descrição do sistema que o
experimento vai medir.

## (d) Hipótese "retrieval quase aleatório = artefato de escala do RRF" — REFUTADO

**Correção (05/08/2026), depois do registro original abaixo.** O veredito
inicial desta seção era INDETERMINADO, por não localizar a citação da
queixa em nenhum dos 5 candidatos do repositório. Estava certo sobre o
repositório — e errado em parar aí. O pesquisador localizou a origem: uma
conversa de 22/06/2026 (fora deste repo, fora de qualquer um dos dois
git), onde métricas operacionais reais do Chat Cognitivo foram
compartilhadas — retrieval score médio **0,475**, compressão 0,0%, 5,0
memory hits, zero erros em 37 requisições. **Tentei buscar essa conversa
(`WebFetch` na URL fornecida) para conferir por mim mesmo antes de aceitar
— retornou 403 (URL privada, não recuperável por ferramenta não
autenticada), então o que segue depende do relato do pesquisador, não de
verificação direta minha do texto original.** O que pude conferir de
forma independente, na fonte, corrobora a lógica:

- `edp/config.py` (já citado em §(b)): híbrido promovido a default ON em
  **08/07/2026** — 22/06 é anterior. **Falsificador 1 dispara.**
- RRF produz ~0,016 (`edp/retrieval_hybrid.py:236-246`, confirmado em §(d)
  original abaixo); **0,475 é escala cosseno**, não RRF. **Falsificador 2
  dispara.** Dois falsificadores bastam; um já derrubaria a hipótese.
- exp010 (Recall@5 25%→87,5%) é a correção que a promoção de 08/07
  documenta — motivo independente, já citado em §(b), de que o
  diagnóstico de 22/06 tinha alvo real e foi endereçado.
- `promote_threshold=3` (`edp/consolidation.py:173,250,344`, confirmado
  agora por leitura direta) explica a metade "consolidação episódica
  ausente" sem precisar de patologia: 37 requisições dificilmente
  acessam a mesma entry 3× para disparar promoção.

**Veredito: REFUTADO**, não indeterminado. "Quase aleatório" foi
avaliação interpretativa de um LLM assistente numa conversa — nunca foi
medição, nunca foi artefato verificável, e o próprio número que a
sustentava (0,475 em embeddings normalizados) já é bem acima do que um
par aleatório produziria. A investigação por leitura abaixo (o §(d)
original) permanece útil como registro do que EXISTE no repositório — só
o veredito final muda, de "não achei citação, fico indeterminado" para
"a citação existe, é de fora do repo, e refuta".

---

### Registro original (05/08/2026, antes da correção acima)

Verificação por leitura, sem instrumentar retrieval. Checado
nos 5 candidatos apontados: `RELATORIO_DOGFOOD.md` (untracked, mtime
22/07 — gerado pelo script do commit `7ca4ef2`), `FASE0_DIAGNOSTICO_HARDENING.md`
(16/07), `benchmark_report.json` (único commit, 20/05 — **anterior** à
promoção do híbrido em 08/07), `AVALIACAO_ENGENHARIA_EDP.md` (22/07), e o
próprio script de `7ca4ef2` (`audit/retrieval_audit.py` + `RELATORIO_AUDIT_V1.md`).

**Nenhum dos cinco contém a queixa "retrieval quase aleatório" como
diagnóstico de patologia.** `RELATORIO_DOGFOOD.md` e o script que o gera
usam "aleatória"/"aleatoriedade" só como referência estatística neutra
(baseline sob permutação, mesmo espírito do controle `shuffled` do E7) —
o texto explicitamente enquadra repetição alta como possivelmente normal,
não como falha. `FASE0_DIAGNOSTICO_HARDENING.md` não menciona o termo.
`AVALIACAO_ENGENHARIA_EDP.md` faz uma queixa **diferente**: "força-bruta
sem índice real" / `RETRIEVAL_BACKEND` "decorativa" — sobre o backend
vetorial não ser ANN-indexado, não sobre a magnitude do score pós-fusão
RRF (é a mesma pergunta ainda aberta em §(b) acima, não esta). Sem a
citação verbatim da queixa original, os falsificadores de confirmação
(§ "CONFIRMA") não podem ser satisfeitos, e os falsificadores 1/2/3/4 de
refutação também não — nenhum lado tem citação. **Registro como
indeterminado, não forçado para nenhum lado**, como a régua deste
documento manda.

**Falsificador 5 checado e não disparado:** `edp/retrieval_hybrid.py:236-246`
confirma RRF padrão rank-based (`score(d) = Σ 1/(k+rank(d))`, k=60,
comentário "padrão da literatura") — não preserva magnitude, a premissa
de compressão por construção se sustenta tecnicamente.

**Pergunta 5 (limiar fixo vs. escala) resolvida, e tranquilizadora:**
`min_score=0.20` e `CURRENT_SESSION_TRUST_THRESHOLD=0.30`
(`edp/memory/store.py:492,617,660`) comparam contra `rank_score`
calculado **antes** da fusão (cosine puro por camada, dentro do
`retrieve()` de `EpisodicMemory`/`SemanticMemory`) — nunca contra o score
pós-RRF. O caminho pós-fusão usa uma constante própria,
`HYBRID_MIN_SCORE` (`edp/config.py:126`, default `0.0` via
`EDP_HYBRID_MIN_SCORE`), com comentário explícito do autor original:
"O RETRIEVAL_MIN_SIM (0.20, escala cosine) zeraria TUDO — escala
própria" (`config.py:125`) e "min_score do chamador (escala cosine) NÃO
se aplica ao RRF" (`store.py:1464`). Nenhum gate sempre-rejeitando
encontrado. Achado lateral descartado: `ANALISE_SATELITES_V32.md:519`
sugere um corte `ranking_score >= 0.88` para detecção de loop, mas é
código **proposto, nunca implementado** (`grep` em `.py` não encontra
`sat_count` nem esse `0.88` fora desta análise) — não é bug vivo.

**Achado colateral, não confirmatório mas relevante para investigação
futura:** `edp/dashboard/static/dashboard.js:141-142` exibe
`sm.retrieval_score.mean` truncado a 3 casas num painel operacional
("r-score"), alimentado diretamente pelo `ranking_score` bruto via
`M.retrieval_score()` (`edp/memory/store.py:1519,1737` →
`edp/metrics.py:42-43`) — se o híbrido estiver ON, esse painel mostra a
escala RRF (~0,016), exatamente o tipo de número que pareceria "quase
aleatório" a um operador olhando o dashboard. O próprio autor do fix já
havia avisado disso em `config.py:51`: "dashboards/telemetria
Gauss/retrieval_score veem a escala nova." Isto é candidato plausível a
mecanismo, **não confirmação** de que foi isto que o diagnóstico
observou — a origem textual do diagnóstico não foi localizada nestes 5
arquivos. Se o diagnóstico original for encontrado em outra fonte, checar
primeiro se ele cita este painel.

## (e) §(c) um nível mais fundo — premissa sem documento nenhum por trás

§(c) trata de linhagem de auditoria **documentada e errada** (branch/SHA,
contagem de call sites, resultado de teste — algo foi escrito, e o
escrito não batia com o checkout). O caso de §(d) é mais raso ainda: **não
havia documento nenhum para verificar.** "Retrieval quase aleatório" era
uma avaliação interpretativa feita por um assistente LLM dentro de uma
conversa, a partir de um número real (0,475) que não a sustentava sozinho
— um cosseno médio de 0,475 em embeddings normalizados fica bem acima do
que um par aleatório produz. Essa avaliação foi comprimida num resumo de
memória, endurecida em premissa ao ser recuperada numa sessão posterior,
e reciclada como base de decisão nesta própria investigação (a motivação
original do plano E8, a hipótese do RRF) — sem nunca ter existido como
artefato revisável, versionado ou datado.

**A diferença importa para a regra:** um Passo 0 que só audita "documento
existe e bate com a fonte" não pega este caso, porque não há documento.
A verificação tem que se perguntar, antes disso, **se a premissa tem
qualquer artefato por trás — ou se é só coisa que alguém (humano ou
modelo) lembra de ter concluído.** Avaliação interpretativa de LLM sobre
um número real, se vai virar premissa de trabalho futuro, precisa ser
citada com o número junto (aqui: "0,475, avaliado como baixo") — nunca só
o rótulo ("quase aleatório") sobrevivendo sozinho, descolado da medição
que (não) o sustentava. O rótulo generoso é o sintoma: ele fez o trabalho
que o número, sozinho, não fazia.
