"""
Transporte HTTP — opcao `A` de `docs/agent_runtime/DECISAO_TRANSPORTE.md`,
assinada em 03/09/2026 (porta 8010, servidor em `lab_edp_novo`, cliente v1 =
pagina separada).

    GET  /                  pagina de teste (MESMA ORIGEM — ver CORS abaixo)
    GET  /health
    GET  /v1/capacidades    o que este runtime aceita, com nivel e teto
    POST /v1/tarefas        TarefaRequest v1  ->  TarefaResponse v1

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

SINCRONO, DE PROPOSITO
----------------------
A instrucao foi "request/response confiavel antes de streaming". Entao a
tarefa roda dentro da requisicao, e o transporte tem teto proprio de tempo
(`TETO_SEGUNDOS`). Um pedido com `max_segundos` acima do teto e **recusado na
entrada**, com o motivo — em vez de aceito e cortado no meio, que devolveria
resultado parcial parecendo resultado completo.
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
import time
from pathlib import Path
from typing import Any, Callable

from .capacidades import CATALOGO, Nivel
from .contrato import Observacao, ProvedorDeCapacidade
from .executor import Executor, Intencao
from .politica import Politica
from .requisicao import SCHEMA, RequisicaoInvalida, para_tarefa
from .tarefa import Tarefa

SCHEMA_RESPOSTA = "TarefaResponse v1"

#: Teto de corpo. Uma `TarefaRequest` tem centenas de bytes; 64 KiB e folga de
#: duas ordens de grandeza e ainda impede que o transporte vire canal de upload.
TETO_BYTES = 64 * 1024

#: Teto de tempo do transporte. Nao e o orcamento da tarefa — e o limite do que
#: cabe numa requisicao sincrona sem virar conexao pendurada.
TETO_SEGUNDOS = 30.0

LOOPBACK = {"127.0.0.1", "localhost", "::1"}

#: Rotas que exigem token. `/` e `/health` ficam abertas de proposito: a pagina
#: nao carrega segredo nenhum, e `/health` precisa responder a quem ainda nao
#: tem token para dizer que o servidor esta de pe.
PROTEGIDAS = {"/v1/tarefas", "/v1/capacidades"}

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


def cria_app(politica: Politica,
             provedores: list[ProvedorDeCapacidade],
             propositor: Propositor,
             teto_nivel: Nivel = Nivel.OBSERVAR,
             pagina: Path | str | None = None,
             nome_propositor: str = "?"):
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

    token = _token_configurado()
    executor = Executor(politica, provedores)
    html = Path(pagina) if pagina else Path(__file__).parent / "pagina_teste.html"

    app = FastAPI(title="Agent Runtime — transporte", docs_url=None, redoc_url=None)

    def _autenticado(authorization):
        prefixo = "Bearer "
        dado = authorization[len(prefixo):] if (
            authorization or "").startswith(prefixo) else ""
        # compare_digest sempre, inclusive com string vazia: sair mais cedo
        # quando o header falta devolve "sem token" em tempo diferente de
        # "token errado".
        return hmac.compare_digest(dado, token)

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
        if request.url.path in PROTEGIDAS and not _autenticado(
                request.headers.get("authorization")):
            return JSONResponse({"detail": "token invalido ou ausente"},
                                status_code=401)
        return await chamada(request)

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
                "streaming": False}

    @app.get("/v1/capacidades")
    def capacidades():
        return {"teto_nivel": int(teto_nivel),
                "capacidades": catalogo_publico(teto_nivel)}

    @app.post("/v1/tarefas")
    async def submete(request: Request):
        bruto = await request.body()
        if len(bruto) > TETO_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"corpo de {len(bruto)} bytes acima do teto {TETO_BYTES}")
        try:
            d = json.loads(bruto.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=400, detail=f"JSON invalido: {e}")

        # Teto de tempo conferido ANTES de virar Tarefa: aceitar e cortar no
        # meio devolveria resultado parcial com cara de completo.
        pedido = d.get("max_segundos")
        if pedido is not None and float(pedido) > TETO_SEGUNDOS:
            raise HTTPException(
                status_code=422,
                detail=(f"max_segundos={pedido} acima do teto {TETO_SEGUNDOS} "
                        f"deste transporte. Ele e sincrono por decisao "
                        f"(DECISAO_TRANSPORTE.md, opcao A); tarefa mais longa "
                        f"exige a opcao B, que nao esta assinada."))
        try:
            tarefa = para_tarefa(d, teto_nivel)
        except RequisicaoInvalida as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:                      # CapacidadeDesconhecida etc.
            raise HTTPException(status_code=422,
                                detail=f"{type(e).__name__}: {e}")

        t0 = time.perf_counter()
        res = executor.roda(tarefa, propositor)
        ms = (time.perf_counter() - t0) * 1000.0

        return JSONResponse({
            "schema": SCHEMA_RESPOSTA,
            "task_id": tarefa.id,
            "estado": tarefa.estado.value,
            "motivo_parada": tarefa.motivo_parada,
            "iteracoes": tarefa.iteracao,
            "concluida": res.concluida,
            "negadas": res.negadas,
            "observacoes": [o.to_dict() for o in res.observacoes],
            "duracao_ms": round(ms, 2),
        })

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
