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

from .canal import CanalMesa, MesaDeSolicitacoes
from .capacidades import Nivel
from .contrato import Observacao, ProvedorDeCapacidade
from .executor import Intencao
from .politica import Politica
from .provedores.browser import ChromeDebuggerProvider, RegistroDeAlvos
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
    p.add_argument("--raiz", default=None,
                   help="onde as tarefas sao persistidas (default: temporario)")
    p.add_argument("--origem-extensao", default=None, metavar="chrome-extension://ID",
                   help="abre CORS para UMA origem exata — o painel do "
                        "Copiloto. Sem isto nao ha CORS nenhum e so a pagina "
                        "servida pelo proprio Runtime fala com ele. Curinga "
                        "nao e aceito.")
    p.add_argument("--browser", action="store_true",
                   help="liga browser.inspect via chrome.debugger. Exige que o "
                        "painel do Copiloto registre a aba-alvo e anexe antes "
                        "de qualquer tarefa — ver docs/agent_runtime/"
                        "SMOKE_BROWSER_INSPECT.md")
    a = p.parse_args(argv)

    if a.propositor == "llm":
        print("--propositor llm ainda nao esta ligado: exige cliente de modelo "
              "configurado (PropositorLLM + RoteadorEDP). Nao ha default "
              "silencioso — ver docs/agent_runtime/DECISAO_TRANSPORTE.md.",
              file=sys.stderr)
        return 2

    propositor = PropositorEco()
    provedores = []
    if a.har:
        from .provedores.har import ProvedorHAR
        provedores.append(ProvedorHAR(a.har))

    # Mesa e registro de alvos sao COMPARTILHADOS entre o provedor (que le) e
    # os endpoints (que escrevem). Construi-los aqui e passar aos dois e o que
    # faz o alvo registrado por POST /v1/browser/alvo chegar a tarefa.
    mesa = MesaDeSolicitacoes()
    alvos = RegistroDeAlvos()
    if a.browser:
        provedores.append(ChromeDebuggerProvider(
            canal_de=lambda cid: CanalMesa(mesa, cid), alvos=alvos))

    if not provedores:
        provedores.append(ProvedorVazio())

    try:
        app = cria_app(Politica(nivel_maximo=Nivel.OBSERVAR), provedores,
                       propositor, nome_propositor=propositor.nome,
                       raiz=a.raiz, mesa=mesa, alvos=alvos,
                       origem_extensao=a.origem_extensao)
        print(f"[transporte] propositor={propositor.nome} "
              f"provedores={[p.nome for p in provedores]} "
              f"raiz={a.raiz or '(temporario)'} "
              f"http://{a.host}:{a.porta}/", file=sys.stderr)
        if a.origem_extensao:
            print(f"[transporte] CORS aberto para UMA origem: "
                  f"{a.origem_extensao}", file=sys.stderr)
        else:
            print("[transporte] sem CORS — so a pagina servida por este "
                  "Runtime (GET /) fala com ele", file=sys.stderr)
        if a.browser:
            print("[transporte] browser.inspect LIGADO — nenhuma tarefa de "
                  "navegador roda ate o painel registrar a aba e anexar "
                  "(estado ANEXADO em GET /v1/browser/alvo)", file=sys.stderr)
        roda(app, host=a.host, porta=a.porta)
    except TransporteMalConfigurado as e:
        print(f"[transporte] recusa de subir: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
