# Auditoria — REL-001

`e01a62f36d04` · 2026-08-31T21:21:14+00:00 · **BLOCKED**

## O sistema foi auditável?

**Não sob este protocolo.** A execução foi interrompida antes de qualquer cálculo, por pré-condição de validade não satisfeita.

## O que foi encontrado

- **cardinalidade do ranking**: 37 documentos por query (N = 50)
- **duplicacao intra query por id**: 0,26 fracao dos slots (N = 50)
- **duplicacao por texto**: 0 fracao dos documentos distintos (N = 50)
- **sobreposicao cross query**: 0,283 Jaccard entre pares de queries (N = 1225)
- **razao score topo cauda**: 1,814 razao adimensional (N = 50)

- 50 de 50 queries nao alcancam 50 documentos distintos (min=30, mediana=37.0, max=41). Os slots estao cheios; os documentos, nao.

## O que NÃO foi possível concluir

Nenhuma métrica de protocolo foi calculada — sem Recall@K, sem índice de acordo, sem *ground truth*.

Etapas não executadas: `estratos`, `amostragem`, `julgadores`, `estatistica`.

As medições acima descrevem o material recuperado. Elas **não** autorizam afirmação sobre a qualidade das respostas do sistema.

## Qual decisão precisa ser tomada

Entre **alterar o objeto auditado** e **alterar o protocolo**. As duas mudam o que está sendo medido; nenhuma pode ser adotada em silêncio, e a escolha não é do serviço.

---

Evidência detalhada em `relatorio_tecnico.md`. Manifesto `89686215aafcc8b5…` em `manifesto.json`.