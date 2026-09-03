"""
Transporte HTTP — opcao `A` de `docs/agent_runtime/DECISAO_TRANSPORTE.md`,
assinada em 03/09/2026 (porta 8010, servidor em `lab_edp_novo`, cliente v1 =
pagina separada).

    GET  /                            pagina de teste (MESMA ORIGEM — ver CORS)
    GET  /health
    GET  /v1/capacidades              o que este runtime aceita
    POST /v1/tarefas                  TarefaRequest v1 -> 202 + task_id
    GET  /v1/tarefas/{id}             estado
    GET  /v1/tarefas/{id}/resultado   resultado (409 enquanto nao terminal)
    POST /v1/tarefas/{id}/cancelar    cancelamento

TRANSPORTA. Nao decide nada sobre a tarefa: quem valida e `requisicao.valida`,
quem recusa por nivel e `para_tarefa`, quem autoriza por chamada e `Politica`,
quem executa e `Executor`. Se este arquivo tomasse alguma dessas decisoes,
haveria duas fontes de verdade para a mesma regra.

O QUE ESTE MODULO NUNCA FAZ
---------------------------
Na linha do `"O que este modulo NUNCA FAZ"` de `debugger_capturer.js` no
Exportador — a fronteira escrita vale mais que a fronteira lembrada.

  * **Nunca faz bind fora de loopback.** `roda()` recusa qualquer host que nao
    seja `127.0.0.1`/`localhost`/`::1`. Um runtime que propoe capacidade e
    escuta em `0.0.0.0` e um runtime que qualquer maquina da rede dirige.
  * **Nunca emite `Access-Control-Allow-Origin`.** Ver CORS.
  * **Nunca sobe o teto de nivel.** `para_tarefa(..., Nivel.OBSERVAR)`, sempre.
  * **Nunca abre conexao persistente, streaming ou push.** Isso e a opcao `B`,
    e o gatilho para reabrir a escolha e progresso incremental existir.
  * **Nunca fala com o `/stream` do EDP.** A unidirecionalidade de
    `edp/ingest/websocket_receiver.py` continua intacta (opcao `C`, nao
    recomendada).

CORS: A AUSENCIA E A DECISAO
----------------------------
Qualquer pagina aberta no navegador pode **enviar** um POST para
`127.0.0.1:8010`. O que ela nao pode e **ler a resposta** sem
`Access-Control-Allow-Origin`, e nao pode nem enviar com `Authorization` +
`Content-Type: application/json` sem passar por preflight.

Este servidor nao responde preflight e nao emite header de CORS nenhum. Por
isso a pagina de teste e servida **por ele mesmo**, em `GET /`: mesma origem
nao precisa de CORS. O resultado e que **nenhuma outra origem consegue falar
com este runtime**, e isso e propriedade, nao esquecimento.

Quando o painel do Copiloto virar cliente (etapa seguinte, ainda nao
autorizada), a origem passa a ser `chrome-extension://<id>` — e ai emitir CORS
para essa origem especifica vira uma decisao consciente, com nome e escopo,
em vez de um `*` herdado de agora.

AUTENTICACAO
------------
`Authorization: Bearer <token>`, comparado com `hmac.compare_digest`. O token
vem de `AGENT_RUNTIME_TOKEN`; **sem ele o servidor recusa subir**. Falhar
fechado importa aqui: um servidor local sem token e alcancavel por qualquer
processo da maquina.

A pagina de teste NAO recebe o token embutido — ela tem um campo onde o
operador cola, `type="password"`, nao persistido. Mesma disciplina do campo de
API key do dashboard do EDP.

ASSINCRONO — ERRATA DA PRIMEIRA VERSAO
--------------------------------------
A primeira versao rodava a tarefa DENTRO da requisicao e devolvia o resultado
na mesma resposta. Isso veio de ler "primeiro faca request/response confiavel"
como "execucao sincrona", e nao e a mesma coisa: `request/response` descreve o
formato do transporte, nao onde a tarefa executa.

O brief pedia `submit_task -> task_id`, depois `get_task` / `get_result` /
`cancel_task` — assincrono por construcao. Sem tarefa guardada nao havia o que
consultar, e sete itens ficaram impossiveis de uma vez.

Agora `POST /v1/tarefas` devolve **202 + task_id**, `servico.TaskService`
persiste e executa fora da requisicao, e as tres consultas existem.

IDENTIFICACAO DO CLIENTE
------------------------
`AGENT_RUNTIME_TOKENS` mapeia `client_id:token`, separados por virgula. Sem
ela, `AGENT_RUNTIME_TOKEN` continua valendo como o cliente `default`.

O `client_id` autenticado filtra TODA leitura: `task_id` nao e segredo — e
devolvido a quem submeteu — entao sem o filtro um cliente com o id de outro
leria a tarefa alheia.

CORRELATION ID FICA EM HEADER, NAO NO CORPO
-------------------------------------------
`X-Request-Id` (idempotencia) e `X-Correlation-Id` (rastreio) sao concerns do
TRANSPORTE. Poe-los no corpo exigiria acrescenta-los a `TarefaRequest v1`, que
recusa campo desconhecido de proposito — e o brief manda manter v1 como
contrato logico. Header transporta; contrato nao muda.
"""
# SEM `from __future__ import annotations` DE PROPOSITO.
#
# Com ele, `def submete(request: Request, ...)` vira a string "Request", e o
# FastAPI tenta resolve-la no namespace do MODULO — onde `Request` nao existe,
# porque `fastapi` so e importado dentro de `cria_app` (regra da casa: o nucleo
# roda sem fastapi). O resultado era silencioso e errado: o parametro virava
# query param obrigatorio e o endpoint devolvia 422 de schema para quem nem
# tinha se autenticado. Achado ao escrever `test_endpoints_protegidos_recusam_401`.
import hmac
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from .capacidades import CATALOGO, Nivel
from .contrato import Observacao, ProvedorDeCapacidade
from .executor import Intencao
from .politica import Politica
from .requisicao import SCHEMA, RequisicaoInvalida
from .servico import TaskService
from .tarefa import Tarefa

#: Mesmo formato de id do `servico._ID`: compoe caminho, entao e entrada nao
#: confiavel.
_ID_CLIENTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

SCHEMA_RESPOSTA = "TarefaResponse v1"

#: Teto de corpo. Uma `TarefaRequest` tem centenas de bytes; 64 KiB e folga de
#: duas ordens de grandeza e ainda impede que o transporte vire canal de upload.
TETO_BYTES = 64 * 1024

#: Teto de tempo POR TAREFA. Na primeira versao era o limite do que cabia numa
#: requisicao sincrona; agora a tarefa roda fora da requisicao, entao ele deixa
#: de proteger a conexao e passa a proteger o pool: uma tarefa sem teto segura
#: um worker para sempre. Continua recusado NA ENTRADA — aceitar e cortar no
#: meio devolveria resultado parcial com cara de resultado completo.
TETO_SEGUNDOS = 300.0

LOOPBACK = {"127.0.0.1", "localhost", "::1"}

#: Rotas que exigem token. `/` e `/health` ficam abertas de proposito: a pagina
#: nao carrega segredo nenhum, e `/health` precisa responder a quem ainda nao
#: tem token para dizer que o servidor esta de pe.
#: Prefixos protegidos. `/health` e `/` ficam abertas de proposito: a pagina
#: nao carrega segredo, e `/health` precisa responder a quem ainda nao tem
#: token para dizer que o servidor esta de pe.
PROTEGIDOS = ("/v1/",)

Propositor = Callable[[Tarefa, list[Observacao]], Intencao]


class TransporteMalConfigurado(RuntimeError):
    """Recusa de subir. Nunca e um aviso: o servidor nao existe assim."""


def _token_configurado() -> str:
    tok = os.environ.get("AGENT_RUNTIME_TOKEN", "")
    if not tok or len(tok) < 16:
        raise TransporteMalConfigurado(
            "AGENT_RUNTIME_TOKEN ausente ou com menos de 16 caracteres.\n"
            "Este servidor nao sobe sem token: um runtime local sem "
            "autenticacao e alcancavel por qualquer processo da maquina.\n"
            "  export AGENT_RUNTIME_TOKEN=\"$(python3 -c "
            "'import secrets;print(secrets.token_urlsafe(32))')\"")
    return tok


def catalogo_publico(teto: Nivel = Nivel.OBSERVAR) -> list[dict[str, Any]]:
    """
    O catalogo inteiro, com `aceita` dizendo o que o teto deixa passar.

    L1/L2 aparecem de proposito: o cliente precisa saber que a capacidade
    EXISTE e esta recusada, senao pede de novo achando que errou o nome. A
    razao da recusa esta em `DECISAO_ATUACAO.md`, e o campo aponta pra la.
    """
    return [{"nome": c.nome, "nivel": int(c.nivel), "o_que_faz": c.o_que_faz,
             "implementada": c.implementada,
             "aceita": bool(c.nivel <= teto and c.implementada),
             "motivo": ("" if c.nivel <= teto and c.implementada else
                        f"L{int(c.nivel)} acima do teto deste runtime"
                        if c.nivel > teto else
                        "declarada, nao implementada")}
            for c in CATALOGO.values()]


def _clientes_configurados() -> dict[str, str]:
    """
    `client_id -> token`. Falha FECHADO: sem nenhum token o servidor nao sobe.

    `AGENT_RUNTIME_TOKENS` = "acme:tok1,globex:tok2". Sem ela, o
    `AGENT_RUNTIME_TOKEN` de sempre vale como o cliente `default` — quem so
    tem um cliente nao precisa aprender formato novo.
    """
    multi = os.environ.get("AGENT_RUNTIME_TOKENS", "").strip()
    if multi:
        out: dict[str, str] = {}
        for par in multi.split(","):
            cid, _, tok = par.strip().partition(":")
            cid, tok = cid.strip(), tok.strip()
            if not cid or not tok:
                raise TransporteMalConfigurado(
                    f"AGENT_RUNTIME_TOKENS mal formado em {par!r}; "
                    f"esperado 'client_id:token'")
            if len(tok) < 16:
                raise TransporteMalConfigurado(
                    f"token do cliente {cid!r} tem menos de 16 caracteres")
            if not _ID_CLIENTE.match(cid):
                raise TransporteMalConfigurado(f"client_id invalido: {cid!r}")
            out[cid] = tok
        return out
    return {"default": _token_configurado()}


def cria_app(politica: Politica,
             provedores: list[ProvedorDeCapacidade],
             propositor: Propositor,
             teto_nivel: Nivel = Nivel.OBSERVAR,
             pagina: Path | str | None = None,
             nome_propositor: str = "?",
             raiz: Path | str | None = None,
             servico: "TaskService | None" = None):
    """
    `propositor` e OBRIGATORIO e injetado, como no `Executor`.

    Nao existe default: um propositor silencioso escolhido pelo transporte
    faria o servidor devolver resultado de um modelo que ninguem escolheu. Quem
    monta o servidor decide qual modelo propoe — trocar Claude por Ollama nao
    pode passar por aqui.

    `fastapi` so e importado dentro desta funcao; o nucleo do runtime roda sem
    ele, como no `auditor/api.py`.
    """
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse

    clientes = _clientes_configurados()
    html = Path(pagina) if pagina else Path(__file__).parent / "pagina_teste.html"
    svc = servico or TaskService(
        raiz or Path(tempfile.mkdtemp(prefix="agent_runtime_")),
        politica, provedores, propositor, teto_nivel)

    app = FastAPI(title="Agent Runtime — transporte", docs_url=None, redoc_url=None)
    app.state.servico = svc

    def _cliente(authorization) -> str | None:
        """Devolve o `client_id` autenticado, ou `None`."""
        prefixo = "Bearer "
        dado = authorization[len(prefixo):] if (
            authorization or "").startswith(prefixo) else ""
        achado = None
        # Percorre TODOS os clientes, sempre, e sempre com compare_digest.
        # Sair no primeiro acerto faria o tempo de resposta contar quantos
        # clientes existem antes do que acertou.
        for cid, tok in clientes.items():
            if hmac.compare_digest(dado, tok):
                achado = cid
        return achado

    @app.middleware("http")
    async def autentica(request, chamada):
        """
        Autenticacao em MIDDLEWARE, nao no handler.

        No handler ela roda depois da validacao de parametros do FastAPI —
        entao um cliente sem token recebia 422 com detalhe de schema em vez de
        401. Dar retorno sobre o formato do corpo a quem nao se autenticou e
        pequeno, mas e informacao dada de graca. Aqui a ordem e garantida por
        construcao, e continua garantida se alguem acrescentar parametro ao
        handler amanha.
        """
        if request.url.path.startswith(PROTEGIDOS):
            cid = _cliente(request.headers.get("authorization"))
            if cid is None:
                return JSONResponse({"detail": "token invalido ou ausente"},
                                    status_code=401)
            request.state.client_id = cid
        return await chamada(request)

    def _visao(r) -> dict[str, Any]:
        """
        A MESMA representacao para estado e resultado.

        Nao existe um "resultado" que possa divergir do "estado": duas fontes
        para o mesmo fato acabam discordando, e o cliente nao teria como saber
        qual acreditar. O que muda entre os dois endpoints e QUANDO respondem,
        nao O QUE respondem.
        """
        d = r.to_dict()
        d["schema"] = SCHEMA_RESPOSTA
        d["terminal"] = r.terminal
        return d

    def _exige(request, task_id: str):
        r = svc.estado(task_id, request.state.client_id)
        if r is None:
            # 404 tambem para tarefa de OUTRO cliente. Devolver 403 diria ao
            # cliente que aquele task_id existe em algum lugar.
            raise HTTPException(status_code=404, detail="tarefa nao encontrada")
        return r

    @app.get("/", response_class=HTMLResponse)
    def raiz() -> str:
        """Mesma origem que `POST /v1/tarefas` — e por isso que dispensa CORS."""
        if not html.exists():
            raise HTTPException(status_code=404, detail=f"pagina ausente: {html}")
        return html.read_text(encoding="utf-8")

    @app.get("/health")
    def health() -> dict[str, Any]:
        # `propositor` no /health de proposito: o cliente precisa poder
        # distinguir uma resposta de modelo real de uma resposta do eco
        # deterministico. Sem isso, o mesmo JSON significaria duas coisas.
        return {"ok": True, "schema_entrada": SCHEMA,
                "schema_saida": SCHEMA_RESPOSTA,
                "propositor": nome_propositor,
                "teto_nivel": int(teto_nivel),
                "teto_segundos": TETO_SEGUNDOS, "teto_bytes": TETO_BYTES,
                "streaming": False, "assincrono": True}

    @app.get("/v1/capacidades")
    def capacidades():
        return {"teto_nivel": int(teto_nivel),
                "capacidades": catalogo_publico(teto_nivel)}

    @app.post("/v1/tarefas")
    async def submete(request: Request) -> JSONResponse:
        bruto = await request.body()
        if len(bruto) > TETO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"corpo de {len(bruto)} bytes acima do teto {TETO_BYTES}")
        try:
            d = json.loads(bruto.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=400, detail=f"JSON invalido: {e}")

        pedido = d.get("max_segundos")
        if pedido is not None and float(pedido) > TETO_SEGUNDOS:
            raise HTTPException(
                status_code=422,
                detail=(f"max_segundos={pedido} acima do teto {TETO_SEGUNDOS} "
                        f"por tarefa deste servico. Recusado na entrada: "
                        f"aceitar e cortar no meio devolveria resultado "
                        f"parcial com cara de resultado completo."))
        try:
            r = svc.submete(
                d, client_id=request.state.client_id,
                request_id=request.headers.get("x-request-id"),
                correlation_id=request.headers.get("x-correlation-id"))
        except RequisicaoInvalida as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:                      # CapacidadeDesconhecida etc.
            raise HTTPException(status_code=422,
                                detail=f"{type(e).__name__}: {e}")

        # 202: aceita, ainda nao terminada. 200 diria que ha resultado.
        return JSONResponse(_visao(r), status_code=202,
                            headers={"Location": f"/v1/tarefas/{r.task_id}"})

    @app.get("/v1/tarefas/{task_id}")
    def consulta(task_id: str, request: Request) -> dict[str, Any]:
        return _visao(_exige(request, task_id))

    @app.get("/v1/tarefas/{task_id}/resultado")
    def resultado(task_id: str, request: Request) -> dict[str, Any]:
        r = _exige(request, task_id)
        if not r.terminal:
            # 409, nao 200 com corpo vazio: "ainda nao ha resultado" e um fato
            # diferente de "o resultado e vazio", e o cliente precisa
            # distinguir os dois sem adivinhar.
            raise HTTPException(
                status_code=409,
                detail=f"tarefa em {r.status}; ainda nao ha resultado")
        return _visao(r)

    @app.post("/v1/tarefas/{task_id}/cancelar")
    def cancela(task_id: str, request: Request) -> dict[str, Any]:
        _exige(request, task_id)
        r = svc.cancela(task_id, request.state.client_id)
        # Cancelar tarefa ja terminal NAO e erro: devolve o registro como
        # esta. Tratar corrida normal como falha faria o cliente inventar
        # retry para uma coisa que ja aconteceu.
        return _visao(r)

    return app


def roda(app, host: str = "127.0.0.1", porta: int = 8010) -> None:
    """
    Sobe o servidor. RECUSA qualquer host fora de loopback.

    A checagem esta aqui e nao na documentacao porque `0.0.0.0` e o default de
    muito exemplo de uvicorn, e um copiar-colar distraido nao pode ser o que
    expoe este runtime para a rede.
    """
    if host not in LOOPBACK:
        raise TransporteMalConfigurado(
            f"host '{host}' recusado. Este transporte so aceita loopback "
            f"({sorted(LOOPBACK)}) — ver DECISAO_TRANSPORTE.md, o que a "
            f"assinatura NAO autoriza.")
    import uvicorn
    uvicorn.run(app, host=host, port=porta, log_level="info")
