"""
Provedor L0 sobre HAR. O ponto de uniao que JA EXISTE entre os dois sistemas.

`debugger_capturer.js` do Exportador grava HAR 1.2 em
`/traffic/<data>/<sessao>.har`, dentro do sandbox da extensao, com
`authorization`, `cookie` e `x-api-key` ja redigidos por default.

Este provedor LE esse arquivo. Nao fala com `chrome.debugger`, nao abre aba,
nao pede permissao nova. A superficie de integracao e um arquivo — e por isso
a uniao pode acontecer hoje sem romper nada.

Se um dia existir atuacao (L1/L2), ela NAO entra aqui: este modulo e o lado
que so observa, e misturar os dois num arquivo so apagaria a fronteira que o
catalogo de capacidades acabou de tornar explicita.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..contrato import Observacao, ProvedorDeCapacidade

# O capturador ja redige estes. Reconferimos porque um HAR pode vir de outra
# fonte (DevTools "Save all as HAR" salva TUDO, sem redacao).
CABECALHOS_SENSIVEIS = {
    "authorization", "cookie", "set-cookie", "proxy-authorization",
    "x-api-key", "x-auth-token", "x-csrf-token", "x-access-token",
}
REDIGIDO = "[REDIGIDO]"


class ProvedorHAR(ProvedorDeCapacidade):
    nome = "har"

    def __init__(self, caminho: Path | str):
        self.caminho = Path(caminho)
        if not self.caminho.exists():
            raise FileNotFoundError(f"HAR nao encontrado: {self.caminho}")
        self._log = json.loads(self.caminho.read_text(encoding="utf-8")).get("log", {})

    def capacidades(self) -> set[str]:
        return {"observe.network", "observe.console", "analyze.json"}

    # ── redacao defensiva ───────────────────────────────────────────────────

    @staticmethod
    def _limpa(cabecalhos: list[dict]) -> list[dict]:
        """
        Redige de novo, mesmo que a origem ja tenha redigido.

        Um HAR salvo pelo DevTools do proprio usuario ("Save all as HAR") vem
        COM cookie e authorization. Confiar na origem seria confiar num
        arquivo que qualquer um pode ter produzido de outro jeito.
        """
        out = []
        for h in cabecalhos or []:
            nome = str(h.get("name", ""))
            v = REDIGIDO if nome.lower() in CABECALHOS_SENSIVEIS else h.get("value")
            out.append({"name": nome, "value": v})
        return out

    # ── execucao ────────────────────────────────────────────────────────────

    def executa(self, capacidade: str, parametros: dict[str, Any],
                tarefa_id: str, iteracao: int) -> list[Observacao]:
        if capacidade == "observe.network":
            return self._rede(parametros, tarefa_id, iteracao)
        if capacidade == "observe.console":
            return self._console(parametros, tarefa_id, iteracao)
        if capacidade == "analyze.json":
            return self._analisa(parametros, tarefa_id, iteracao)
        raise ValueError(f"{self.nome} nao implementa '{capacidade}'")

    def _rede(self, p, tarefa_id, iteracao) -> list[Observacao]:
        filtro = str(p.get("filter", "") or "")
        status = p.get("status")
        obs = []
        for e in self._log.get("entries", []):
            req, res = e.get("request", {}), e.get("response", {})
            url = req.get("url", "")
            if filtro and filtro not in url:
                continue
            if status is not None and res.get("status") != status:
                continue
            obs.append(Observacao(
                capacidade="observe.network", tarefa_id=tarefa_id,
                iteracao=iteracao, fonte=str(self.caminho.name),
                dados={
                    "url": url,
                    "metodo": req.get("method"),
                    "status": res.get("status"),
                    "mime": (res.get("content") or {}).get("mimeType"),
                    "bytes": (res.get("content") or {}).get("size"),
                    "req_headers": self._limpa(req.get("headers")),
                    "res_headers": self._limpa(res.get("headers")),
                },
            ))
        # "nao achei nada" e observacao valida, nao falha nem lista vazia muda
        if not obs:
            obs.append(Observacao(
                capacidade="observe.network", tarefa_id=tarefa_id,
                iteracao=iteracao, fonte=str(self.caminho.name),
                dados={"vazio": True, "filtro": filtro, "status": status,
                       "total_no_har": len(self._log.get("entries", []))}))
        return obs

    def _console(self, p, tarefa_id, iteracao) -> list[Observacao]:
        # HAR 1.2 nao carrega console; o capturador guarda Runtime.consoleAPICalled
        # separado. Declarado explicitamente em vez de devolver vazio mudo.
        return [Observacao(
            capacidade="observe.console", tarefa_id=tarefa_id,
            iteracao=iteracao, fonte=str(self.caminho.name),
            dados={"indisponivel": True,
                   "porque": "HAR 1.2 nao contem console; o capturador grava "
                             "Runtime.consoleAPICalled fora do HAR"})]

    def _analisa(self, p, tarefa_id, iteracao) -> list[Observacao]:
        """Estrutura de um corpo JSON JA observado — nao busca nada novo."""
        bruto = p.get("corpo")
        try:
            d = json.loads(bruto) if isinstance(bruto, str) else bruto
        except Exception as e:
            return [Observacao("analyze.json", tarefa_id, iteracao,
                               {"parse_falhou": type(e).__name__})]
        def forma(x, prof=0):
            if prof > 3:
                return "..."
            if isinstance(x, dict):
                return {k: forma(v, prof + 1) for k, v in list(x.items())[:12]}
            if isinstance(x, list):
                return [forma(x[0], prof + 1), f"...({len(x)} itens)"] if x else []
            return type(x).__name__
        return [Observacao("analyze.json", tarefa_id, iteracao,
                           {"forma": forma(d)})]
