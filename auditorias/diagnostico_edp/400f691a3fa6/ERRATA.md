# Errata — auditoria `400f691a3fa6`

**07/09/2026.** Os artefatos originais desta auditoria **não foram alterados**.
Esta errata fica ao lado deles.

## O que não é recuperável desta execução

**Sob qual configuração o sujeito foi medido.** Verificado em todos os
artefatos persistidos:

```
manifest.json ....... `configuracao` e do AUDITOR
                      (modo, min_unidades, exemplos_em_claro)
                      `retriever` tem top_k, origem, adaptador, telemetria
                      NENHUMA mencao a flag do sujeito
artifacts/checks.json ... nao
input/audit_input.json .. nao
reports/*.md ............ nao
```

**Qual código foi medido.** O manifesto registra `adaptador: EDPAuditavel` e
`versao_adaptador: edp-1` — a versão do *adaptador*, não a do sujeito.
Medido em 07/09/2026: a partir deste repositório, `import edp` resolve para
`/home/kali/.local/lib/python3.11/site-packages/edp/`, uma **cópia instalada**,
não `/media/sf_edp_v5_main/edp/`. Ela é mais antiga: tem `EDP_RETRIEVE_DEDUP`
e **não tem** `FORMAT_STATE_FLAGS`.

## Por que isso importa para os números publicados

`duplicacao_intra_query_por_id = 0,26`, IC [0,24; 0,26], sobre 50 queries.

`EDP_RETRIEVE_DEDUP` está em `edp.config.FORMAT_STATE_FLAGS` com o comentário
*"muda o conjunto recuperado"*, e seu default é `"0"` — desligada.

**Portanto a duplicação medida é indistinguível entre duas causas:**

```
defeito do retriever (dedup ausente apos merge hibrido / RRF)
flag de dedup simplesmente desligada, que e o default
```

Nenhum artefato desta execução separa as duas. **Qualquer afirmação causal
sobre a duplicação por ID, a partir desta auditoria, é infundada** — inclusive
a hipótese de "bug de junção", que foi levantada e não pode ser sustentada
aqui.

O número em si continua válido: 26% dos slots foram ocupados por IDs já
presentes no ranking. É a *explicação* que não está disponível.

## O que foi corrigido, e a partir de quando

`retriever.configuracao_sujeito` passa a ser escrito em **toda** execução, com
a identidade do módulo medido e a fotografia de `FORMAT_STATE_FLAGS`. Sempre
presente: a ausência da chave passa a significar "manifesto anterior a esta
correção", e `disponivel: false` significa "o adaptador não sabe reportar".

Auditorias anteriores a esta data **não ganham a informação
retroativamente** — ela não existe. Para comparar com esta execução, é preciso
rodar de novo.

## Consequência para uso comercial

Este relatório **não deve ser usado como amostra** sem esta errata anexada. A
primeira pergunta de um leitor técnico é "medido sob qual configuração?", e a
resposta honesta hoje é "não registrado". Uma amostra que não responde isso
mostra o oposto do rigor que ela existe para demonstrar.
