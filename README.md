# lab_edp

Laboratório experimental do EDP — experimentos, pré-registros e relatórios.

Extraído de edp_v5 (https://github.com/devBorgesr/edp_v5) preservando histórico
via git subtree split -P edp/lab.

## Estrutura

- `bancada/` — núcleo agnóstico de sujeito (prontuário, isolamento, scorer, sampler, repeater, rodízio, formatos); proibido importar `edp.*`
- `sujeitos/edp/` — adaptador que ensina a bancada a falar EDP + `experimentos/` (exp001-010, run_once, calibrações)
- `docs_edp_v5/` — pré-registros, estados e relatórios de fase
- `tests/` — smoke tests e invariante de fronteira bancada/sujeito

## Dependência

O runtime edp é dependência opcional do adaptador. Instalação:

    pip install .            # telescópio puro, sem edp
    pip install ".[edp]"     # com o adaptador EDP

A ref muda para main quando o PR do empacotamento entrar.

## Convenção

Todo experimento tem pré-registro antes da execução. Hipótese, métricas e
critério de decisão são congelados antes de qualquer dado.
