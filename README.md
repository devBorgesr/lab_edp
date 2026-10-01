# EDP Research Lab — Retrieval Diagnostics

Research repository for reproducible retrieval diagnostics, audit instrumentation, sanitization, and bounded technical claims.

> **Repository boundary**
>
> This is a research/engineering laboratory, not the public client-delivery repository. Client audit deliverables belong in **[edp-audits](https://github.com/devBorgesr/edp-audits)**. Private client queries, proprietary corpora, credentials, raw exports, and other non-public client material should not be committed here.

The diagnostic tooling is designed to measure what a retrieval system is actually returning, with explicit evidence, hashes, and limitations.

**This repository does not by itself certify end-to-end RAG quality.** See [`O que não fazemos`](docs/auditor/produto/O_QUE_NAO_FAZEMOS.md).

## Install

```bash
pip install -e .            # engine + CLI, no external dependency
pip install -e ".[http]"    # + HTTP API
auditor --version
```

## Use

```bash
auditor check --input <corpus> --queries <perguntas.json> \
              --protocol DIAGNOSTICO --adaptador cliente
auditor run   ... --output ./auditorias
auditor status --output ./auditorias
auditor report <audit_id> --output ./auditorias
```

`check` is a dry run: it returns `READY` or `BLOCKED` before processing.

## Research outputs

Depending on the protocol, the tooling can produce a manifest with hashes, technical/executive reports, and deterministic verification records.

Those artifacts are research/runtime outputs. **The public delivery contract for an external audit is defined separately in [edp-audits](https://github.com/devBorgesr/edp-audits).**

## Data hygiene

The repository treats conversational exports and client-like raw material as a restricted class rather than normal source code. Public experiments should prefer synthetic fixtures, public datasets, hashes, or sanitized evidence.

Local paths and environment-specific identifiers that appear in historical research notes describe the test environment; they are not part of the client-facing audit contract.

## Documentation

| | |
|---|---|
| [Como funciona](docs/auditor/produto/COMO_FUNCIONA.md) | diagnostic flow |
| [O que você recebe](docs/auditor/produto/O_QUE_VOCE_RECEBE.md) | research artifacts |
| [O que não fazemos](docs/auditor/produto/O_QUE_NAO_FAZEMOS.md) | boundaries |
| [Quickstart](docs/auditor/onboarding/QUICKSTART.md) | local integration |
| [Contrato](docs/auditor/SERVICE_CONTRACT.md) | diagnostic contract |
| [Claims](docs/auditor/CLAIMS.md) | supported claims |
| [API](docs/api/README.md) | HTTP |

## Current research status

`DIAGNOSTICO v1` measures retrieved material. It does not by itself measure answer quality, exhaustive Recall@K, or legal/domain correctness.

Experimental relevance protocols in this repository should be treated according to their own pre-registration and validation status, not as a blanket certification of a client system.

For published external audit cases, start at **[EDP Audits](https://github.com/devBorgesr/edp-audits)**.
