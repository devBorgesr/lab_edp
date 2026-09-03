"""
Ponto de entrada do transporte HTTP (opcao `A`, assinada em 03/09/2026).

    export AGENT_RUNTIME_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
    python3 -m agent_runtime --propositor eco
    python3 -m agent_runtime --propositor eco --har /caminho/sessao.har

`--propositor` NAO tem default. Escolher por conta propria qual coisa propoe
as intencoes seria o transporte decidindo o que a assinatura mandou o operador
decidir — e a resposta HTTP sairia identica nos dois casos, sem que ninguem
soubesse qual modelo (ou nao-modelo) produziu aquilo. Por isso `/health`
tambem devolve o nome do propositor em uso.
"""
import argparse
import sys

from .capacidades import Nivel
from .contrato import Observacao, ProvedorDeCapacidade
from .executor import Intencao
from .politica import Politica
from .transporte import TransporteMalConfigurado, cria_app, roda


class PropositorEco:
    """
    Deterministico, sem modelo: uma observacao por capacidade declarada, e
    conclui. Existe para provar o TRANSPORTE sem misturar a duvida de estar
    testando o transporte com a duvida de estar testando um modelo.

    Nao e um modelo degradado. E a ausencia de modelo, com nome proprio.
    """
    nome = "eco"

    def __call__(self, tarefa, obs: list[Observacao]) -> Intencao:
        feitas = {o.capacidade for o in obs}
        for c in tarefa.capacidades:
            if c not in feitas:
                return Intencao(capacidade=c, parametros={},
                                porque=f"eco: observando '{c}' uma vez")
        return Intencao(capacidade="", concluir=True,
                        porque="eco: todas as capacidades declaradas observadas")


class ProvedorVazio(ProvedorDeCapacidade):
    """
    Responde as capacidades L0 com observacao vazia e `fonte='vazio'`.

    Uma observacao vazia NAO e falha — o contrato de `ProvedorDeCapacidade` diz
    isso explicitamente. O que ela nao pode e se passar por dado: por isso a
    fonte diz o que e, e aparece na resposta HTTP.
    """
    nome = "vazio"

    def capacidades(self):
        return {"observe.network", "observe.console", "analyze.json",
                "memory.read", "memory.write"}

    def executa(self, capacidade, parametros, tarefa_id, iteracao):
        return [Observacao(capacidade=capacidade, tarefa_id=tarefa_id,
                           iteracao=iteracao,
                           dados={"vazio": True,
                                  "aviso": "sem provedor real ligado a esta "
                                           "capacidade; use --har"},
                           fonte="vazio")]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agent_runtime", description=__doc__)
    p.add_argument("--propositor", required=True, choices=["eco", "llm"],
                   help="quem propoe as intencoes. Sem default de proposito.")
    p.add_argument("--porta", type=int, default=8010)
    p.add_argument("--host", default="127.0.0.1",
                   help="so loopback; qualquer outro valor e recusado")
    p.add_argument("--har", default=None,
                   help="HAR real para observe.network/analyze.json")
    a = p.parse_args(argv)

    if a.propositor == "llm":
        print("--propositor llm ainda nao esta ligado: exige cliente de modelo "
              "configurado (PropositorLLM + RoteadorEDP). Nao ha default "
              "silencioso — ver docs/agent_runtime/DECISAO_TRANSPORTE.md.",
              file=sys.stderr)
        return 2

    propositor = PropositorEco()
    if a.har:
        from .provedores.har import ProvedorHAR
        provedores = [ProvedorHAR(a.har)]
    else:
        provedores = [ProvedorVazio()]

    try:
        app = cria_app(Politica(nivel_maximo=Nivel.OBSERVAR), provedores,
                       propositor, nome_propositor=propositor.nome)
        print(f"[transporte] propositor={propositor.nome} "
              f"provedor={provedores[0].nome} "
              f"http://{a.host}:{a.porta}/", file=sys.stderr)
        roda(app, host=a.host, porta=a.porta)
    except TransporteMalConfigurado as e:
        print(f"[transporte] recusa de subir: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
