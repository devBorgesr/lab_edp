# Mapa de proveniência — engenharia construída duas vezes

**Nenhuma unificação foi feita.** Este documento só mostra onde os dois lados
resolveram o mesmo problema com vocabulários diferentes.

## A matriz

| conceito | EDP (`edp_v5`) | MVP (`auditor/`) | compatível? | duplicação | unificação possível |
|---|---|---|---|---|---|
| **id de execução** | `correlation_id` (`pareto_store.py`, 8 arquivos) | `audit_id` (`jobs.py`, `manifest.py`) | conceitualmente sim | **SIM** | `audit_id` poderia SER um `correlation_id` |
| **hash do estado** | `hash_format_state()` — hash do formato da janela | `sha256_manifesto` — hash do manifesto inteiro | escopos diferentes | parcial | não; medem coisas distintas |
| **hash do corpus** | `sha256` no kernel: 3 usos reais, nenhum é hash de corpus (ver fechamento abaixo) | `sha256_episodic` / `sha256_semantic` no snapshot | **não** | **não** | vocabulário exclusivo do MVP |
| **linhagem** | `runtime/lineage.py` (340 L), **vivo em produção** — `EDP_LINEAGE` default `true`, chamado em `websocket.py:1326` a cada turno com LLM | `checks[].evidencia` + `etapas[]` | **não** — lineage rastreia origem de conteúdo, o MVP rastreia verificações | não | complementares, não duplicados |
| **carimbo de escrita** | `write_provenance.py` (212 L): `stamp_and_classify`, 1 de 3 caminhos de escrita cobertos (código admite) | `procedencia` no artefato congelado | mesmo conceito, cobertura parcial em ambos | não — os dois são parciais por razões diferentes | não recomendado antes de fechar a cobertura de qualquer um dos lados |
| **store de eventos** | `FileParetoStore` → JSONL append-only, rotação 10 MB | `Workspace` → arquivos por auditoria | **sim, formatos compatíveis** | não | o auditor poderia LER o JSONL |
| **snapshot** | 15 arquivos citam; `exp009`, `exp010`, `adaptive_controller`, `llm_adapter` | `snapshot_dir` + hash, copiado antes de consultar | NAO_VERIFICADO se o kernel hasheia | NAO_VERIFICADO | — |
| **manifest** | **0 arquivos** | `manifest.json`, contrato `AuditResult v1` | — | **não existe no kernel** | vocabulário exclusivo do MVP |

## O que a matriz mostra

**Uma duplicação real, e ela é pequena.** `correlation_id` e `audit_id` são o
mesmo conceito: um identificador que amarra tudo que aconteceu numa execução.
Foram construídos separadamente porque os dois lados nasceram separados.

**Uma compatibilidade que não estava óbvia.** O `FileParetoStore` grava JSONL
append-only. O auditor consome artefatos de arquivo. **Um adaptador que leia
`events.jsonl` não precisaria de nada novo dos dois lados** — só de um
tradutor. Isso é candidato de acoplamento, não de unificação.

**Duas coisas que pareciam duplicadas e não são.** `lineage` rastreia a
**origem do conteúdo** (de onde veio este fato); o MVP rastreia **verificações**
(o que foi conferido e o que detecta). São eixos diferentes do mesmo problema —
e, juntos, cobrem mais do que qualquer um sozinho.

E `hash_format_state` mede o **formato da janela**; `sha256_manifesto` mede o
**relatório inteiro**. Nomes parecidos, escopos que não se sobrepõem.

## Fechado na Fase 3 (01/09/2026)

**Uso real de `sha256` no kernel — 3 ocorrências, não 10 "arquivos".** A
contagem original de "10 arquivos" incluía scripts de experimento (`exp009`,
`exp010`) que citam a palavra "snapshot", não `sha256` — outra confusão de
população. Os três usos reais:

```
store.py:1586,1764   seed de RNG p/ EDP_SHUFFLE_SEED (reprodutibilidade,
                      NÃO identidade de conteúdo)
pareto_store.py:186   hash_format_state() — IDENTIDADE do regime de formato
cache.py:46            chave de cache de embedding, versionada por
                      EMBED_MODEL_VERSION — CACHE
```

**Nenhum é hash de corpus/documento.** A linha "hash do corpus" da matriz sai
de `NAO_VERIFICADO` para **não há equivalente no kernel** — é vocabulário
exclusivo do MVP.

**`LineageTracker` está ativo.** `EDP_LINEAGE` default `"true"`, chamador único
`websocket.py:1326`, no caminho real de resposta. Vivo em produção, não
"execução desconhecida".

**Cobertura de `stamp_and_classify`: 1 de 3 caminhos de escrita**, e o próprio
código do kernel já documenta a lacuna (comentário em `websocket.py:1256`:
"0 de 10 dessas entradas no store têm carimbo" para o caminho da câmara de
eco).

**Volume de `events.jsonl` — medido, com uma distinção importante.** O store
vivo do kernel (`edp_data/pareto/events.jsonl`) tem **395 eventos reais**,
18/08/2026 a data mais recente. Mas a distribuição por tipo mostra algo que
muda o candidato de acoplamento nº 2: **268 `memory_accessed`, 110
`memory_added`, 8 `camara_outcome`, 7 `mode_switched`, 1 `task_started`, 1
`task_completed` — zero de `ranking_decision`, `reflection`,
`contradiction_scan`, `token_usage` ou `summary_write`.** Os 5 emissores
atrás de flag nunca dispararam fora de teste, porque as flags estão
desligadas. O formato JSONL está exercitado e funciona; os dados específicos
da telemetria de interesse, não. Ver `CANDIDATOS_ACOPLAMENTO_MVP.md`.

## Recomendação, que não é decisão

Não unificar. **Traduzir.**

Um adaptador que leia `events.jsonl` e o exponha como evidência do auditor daria
acesso à telemetria inteira sem tocar em nenhum dos dois vocabulários — e sem
o risco de uma unificação que quebraria os dois lados de uma vez.
