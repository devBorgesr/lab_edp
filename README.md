# lab_edp

Laboratório experimental do EDP — experimentos, pré-registros e relatórios.

Extraído de edp_v5 (https://github.com/devBorgesr/edp_v5) preservando histórico
via git subtree split -P edp/lab.

## Estrutura

- `bancada/` — núcleo agnóstico de sujeito (prontuário, isolamento, scorer, sampler, repeater, rodízio, formatos); proibido importar `edp.*`
- `sujeitos/edp/` — adaptador que ensina a bancada a falar EDP + `experimentos/` (exp001-010, run_once, calibrações) + `analise/` (análises pós-coleta específicas por experimento)
- `docs_edp_v5/` — **herdado**: pré-registros, estados, relatórios de fase e documentos fundadores importados do edp_v5 (cópias de referência, não editar)
- `docs/` — **nativo** deste repo: template de pré-registro, acervo de experimentos, proveniência
- `tests/` — smoke tests e invariante de fronteira bancada/sujeito

## Dependência

O runtime edp é dependência opcional do adaptador. Instalação:

    pip install .            # telescópio puro, sem edp
    pip install ".[edp]"     # com o adaptador EDP

A ref muda para main quando o PR do empacotamento entrar.

## Convenção

Todo experimento tem pré-registro antes da execução. Hipótese, métricas e
critério de decisão são congelados antes de qualquer dado.

## Metodologia

Novo pré-registro? Comece por [docs/TEMPLATE_PREREGISTRO.md](docs/TEMPLATE_PREREGISTRO.md)
— estrutura derivada dos 4 pré-registros existentes (008/009/010/017), com
checklist para colar. [docs/ACERVO_EXPERIMENTOS.md](docs/ACERVO_EXPERIMENTOS.md)
mostra qual experimento tem pré-registro em arquivo e qual não tem (a
disciplina começou no 008 — os anteriores não são reconstruídos
retroativamente). [docs_edp_v5/edp_metodologia.md](docs_edp_v5/edp_metodologia.md)
é a metodologia fundadora **herdada** do edp_v5 (princípios, checklist de
commit, padrão de testes) — referência de método, não deste repo.
[docs/PROVENIENCIA_LAB.md](docs/PROVENIENCIA_LAB.md) resolve qual das duas
cópias (`lab_edp` vs `edp/lab/` no edp_v5) é a canônica. Em suma: `docs/` é
nativo daqui; `docs_edp_v5/` é herdado, cópia de referência.

## License

MIT — see [LICENSE](LICENSE). The `bancada/` ↔ `sujeitos/` boundary (bancada
never imports `edp.*` or `sujeitos.*`) is enforced by `tests/test_fronteira.py`.
