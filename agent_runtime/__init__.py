"""
Agent Runtime — fronteira entre o kernel EDP e um ambiente observavel.

    Copiloto  ->  declara Tarefa
    Kernel    ->  governa (politica, orcamento, memoria, proveniencia)
    Router    ->  escolhe modelo
    Modelo    ->  propoe Intencao
    Politica  ->  autoriza ou nega
    Provedor  ->  executa e devolve Observacao

O modelo NAO tem autoridade. Ele tem capacidade de propor.

NAO faz parte do MVP de Diagnostico de Retrieval (`auditor/`), e nao toca
nele. Linha de produto separada, com decisao propria em
`docs/agent_runtime/DECISAO_ATUACAO.md`.
"""
from .capacidades import CATALOGO, Nivel, busca                    # noqa: F401
from .contrato import Artefato, Observacao, ProvedorDeCapacidade   # noqa: F401
from .executor import Executor, Intencao, Resultado                # noqa: F401
from .politica import Decisao, Politica, Veredito                  # noqa: F401
from .tarefa import EstadoTarefa, Orcamento, Tarefa, deriva        # noqa: F401
