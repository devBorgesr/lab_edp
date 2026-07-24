# lab_edp

Laboratório experimental do EDP — experimentos, pré-registros e relatórios.

Extraído de edp_v5 (https://github.com/devBorgesr/edp_v5) preservando histórico
via git subtree split -P edp/lab.

## Estrutura

- raiz — bancada: expNNN.py, repeater, rodizio, scorer, sampler, isolation, prontuario, window_formats
- experimentos/ — scripts de calibração, backfill e medição
- relatorios/ — pré-registros, estados e relatórios de fase

## Dependência

O runtime edp é dependência externa. Instalação:

    pip install "git+https://github.com/devBorgesr/edp_v5@exp017/fase1-dedup"

A ref muda para main quando o PR do empacotamento entrar.

## Convenção

Todo experimento tem pré-registro antes da execução. Hipótese, métricas e
critério de decisão são congelados antes de qualquer dado.
