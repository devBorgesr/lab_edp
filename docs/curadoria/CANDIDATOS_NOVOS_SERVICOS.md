# Candidatos a serviço novo

Só serviços com **capacidade concreta identificada**. Nada proposto por
combinação de nomes de módulo.

---

## SERVIÇO A — Diagnóstico de perda de contexto (funil)

```
nome ...................... "onde o seu contexto se perde"
problema .................. o cliente sabe quantos documentos chegaram;
                            não sabe quantos foram avaliados e por que os
                            outros saíram
engenharia existente ...... emit_ranking_decision (cascata completa),
                            pareto_store (JSONL), 2 testes
quanto do núcleo existe ... a MEDIÇÃO existe inteira; falta o consumidor
o que falta ............... um check no auditor, um método opcional no
                            contrato, e um relatório que apresente a cascata
evidência ................. store.py:765 emite os 5 estágios + fatores por
                            posição; testado em 2 arquivos
risco ..................... só o EDP emite isso hoje. Um cliente com outro
                            RAG precisa expor telemetria equivalente — e o
                            caso B do piloto (retrieval atrás de API sem
                            score) sugere que muitos não expõem
relação com MVP ........... EXTENSÃO, não substituição. Mesma régua,
                            observação nova.
```

**É o mais próximo de pronto.** Mas depende de o cliente ter instrumentação.

---

## SERVIÇO B — Bateria de perturbação de contexto

```
nome ...................... "seu RAG resiste a quê?"
problema .................. o cliente monta uma janela de contexto e não sabe
                            se a resposta depende da POSIÇÃO, do RUÍDO ou de
                            uma âncora específica
engenharia existente ...... window_formats.py (316 L): fmt_ablacao,
                            fmt_lost_in_middle, fmt_ruido_dominante,
                            fmt_ancora_envenenada, fmt_historico_cortado,
                            fmt_fato_em_camada — transformações PURAS
                          + sampler.py (240 L): N amostras por condição,
                            porque LLM não é determinístico
                          + rodizio.py (147 L): roda um PLANO de condições
                          + scorer.py (1.025 L): análise pós-coleta
quanto do núcleo existe ... a mecânica inteira: perturbar, amostrar, rodar
                            plano, pontuar
o que falta ............... TESTE (a Bancada tem 2 arquivos para 3.000 linhas),
                            e um desfecho definido — hoje o scorer computa
                            "fidelidade", e o que isso significa para um
                            cliente é NAO_VERIFICADO
evidência ................. os 7 formatos existem e são puros; o sampler
                            existe porque o não-determinismo foi medido
risco ..................... ALTO. Isto CONSOME MODELO (N amostras × M
                            condições), ao contrário do DIAGNOSTICO v1 que
                            faz zero chamadas. A economia é outra.
                            E mede QUALIDADE DE RESPOSTA — NÍVEL 3, que o
                            CLAIMS.md hoje proíbe emitir.
relação com MVP ........... SERVIÇO SEPARADO, com régua própria e
                            pré-registro próprio. Não é extensão.
```

**Este é o candidato mais interessante e o mais perigoso.** Ele responderia a
pergunta que o `REL-001` está bloqueado tentando responder — mas por outro
caminho: em vez de rotular relevância, **perturbar e medir o efeito**.

Isso é experimento comparativo, que é exatamente o que falta para sair do
NÍVEL 1. Mas exige pré-registro, desfecho congelado, e a Bancada testada.

---

## SERVIÇO C — Observação de RAG atrás de API

```
nome ...................... "auditar o que você não consegue instrumentar"
problema .................. o CASO B do pré-registro do piloto: o retrieval
                            está atrás de uma API, sem score exposto. Hoje o
                            MVP responde BLOCKED e entrega zero medições.
engenharia existente ...... sf_exportador/copilot/:
                              debugger_capturer.js (541 L) — chrome.debugger
                              har_analyzer.js (276 L)     — análise de HAR
quanto do núcleo existe ... a CAPTURA existe, para tráfego de navegador
o que falta ............... tudo o resto. O EDP captura conversa do claude.ai;
                            um RAG de cliente não roda no navegador dele.
                            A técnica é transferível; o código, NAO_VERIFICADO.
evidência ................. os dois arquivos existem e somam 817 linhas.
                            Fechado na Fase 3 (item 1.6): não há
                            package.json, nem jest/vitest/mocha, nem
                            __tests__, nem *.test.js/*.spec.js em lugar
                            nenhum do sf_exportador. ZERO infraestrutura de
                            teste no repositório inteiro (6.255 linhas JS).
risco ..................... MUITO ALTO, e agora com uma camada a mais: a
                            base técnica não tem NENHUM teste automatizado
                            em 6.255 linhas. Interceptar tráfego de sistema
                            de terceiro é questão jurídica e de
                            consentimento, não só técnica. E um score
                            reconstruído de tráfego não é o score do
                            retriever — seria inferência apresentada como
                            medida, que é exatamente o que o CLAIMS.md
                            proíbe.
relação com MVP ........... NÃO recomendo. Registro porque o caso B é real e
                            porque a engenharia existe — não porque o caminho
                            seja bom.
```

---

## O que NÃO propus, e por quê

**Serviço de série temporal** (`prontuario`): a capacidade existe, mas
"diagnóstico ao longo do tempo" sem um único cliente que tenha pedido é
imaginação, não demanda.

**Serviço de linhagem** (`lineage.py`, 340 L): rastreia origem de conteúdo. É
capacidade real, mas não sei que pergunta de cliente ela responde — e propor
serviço a partir de capacidade, sem problema identificado, é o erro que este
documento deveria evitar.

**Dashboard**: existe (`edp/dashboard/` com static e templates), a decisão de
adiar já foi tomada duas vezes, e o inventário não muda o argumento.
