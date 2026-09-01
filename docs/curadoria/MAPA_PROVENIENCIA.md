# Mapa de proveniência — engenharia construída duas vezes

**Nenhuma unificação foi feita.** Este documento só mostra onde os dois lados
resolveram o mesmo problema com vocabulários diferentes.

## A matriz

| conceito | EDP (`edp_v5`) | MVP (`auditor/`) | compatível? | duplicação | unificação possível |
|---|---|---|---|---|---|
| **id de execução** | `correlation_id` (`pareto_store.py`, 8 arquivos) | `audit_id` (`jobs.py`, `manifest.py`) | conceitualmente sim | **SIM** | `audit_id` poderia SER um `correlation_id` |
| **hash do estado** | `hash_format_state()` — hash do formato da janela | `sha256_manifesto` — hash do manifesto inteiro | escopos diferentes | parcial | não; medem coisas distintas |
| **hash do corpus** | `sha256` em `store.py`, `cache.py`, `config.py` — uso NAO_VERIFICADO | `sha256_episodic` / `sha256_semantic` no snapshot | NAO_VERIFICADO | NAO_VERIFICADO | requer inspeção do uso no kernel |
| **linhagem** | `runtime/lineage.py` (340 L): `SourceEntry`, `LineageRecord`, `LineageTracker` | `checks[].evidencia` + `etapas[]` | **não** — lineage rastreia origem de conteúdo, o MVP rastreia verificações | não | complementares, não duplicados |
| **carimbo de escrita** | `write_provenance.py` (212 L): `stamp_and_classify` | `procedencia` no artefato congelado | mesmo conceito, camadas diferentes | parcial | NAO_VERIFICADO |
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

## O que NÃO foi verificado

- **como o kernel usa `sha256`** nos 10 arquivos onde aparece — não abri cada
  uso; pode ser cache, pode ser integridade, pode ser id;
- **se `LineageTracker` está ativo** — `is_lineage_enabled()` existe, mas não
  medi o default nem quem chama;
- **se `write_provenance.stamp_and_classify` roda hoje** — a flag
  `EDP_WRITE_PROVENANCE` está LIGADA por default, mas não medi a cobertura de
  chamada;
- **volume do `events.jsonl` em produção** — a rotação a 10 MB sugere que já
  foi pensado, mas não medi arquivo real.

## Recomendação, que não é decisão

Não unificar. **Traduzir.**

Um adaptador que leia `events.jsonl` e o exponha como evidência do auditor daria
acesso à telemetria inteira sem tocar em nenhum dos dois vocabulários — e sem
o risco de uma unificação que quebraria os dois lados de uma vez.
