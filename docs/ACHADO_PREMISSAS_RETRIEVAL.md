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
