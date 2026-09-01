"""
Cliente, chave e isolamento. O que separa "roda na minha maquina" de "aceita
o material de outra pessoa".

    data/<client_id>/<audit_id>/{input,artifacts,reports}/manifest.json job.json

Uma requisicao do cliente A **nunca** alcanca um `audit_id` do cliente B. Isso
nao pode depender de o handler lembrar de checar: o `client_id` entra no
CAMINHO, entao um id de outro cliente simplesmente nao existe na raiz de quem
perguntou.

A chave nunca aparece em URL nem em log. O que se registra e o `client_id`.
"""
from __future__ import annotations

import hmac
import json
import secrets
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


class NaoAutorizado(RuntimeError):
    """Chave ausente, desconhecida ou de outro cliente."""


class LimiteExcedido(ValueError):
    """A entrada passa de um limite declarado. INVALID, nao ERROR."""


# Limites default. Nao existem para punir: existem porque sem eles um unico
# cliente consome a maquina inteira e derruba a auditoria dos outros.
LIMITES_PADRAO: dict[str, int] = {
    "max_queries":          500,
    "max_documentos":     50_000,
    "max_snapshot_bytes": 512 * 1024 * 1024,
    "max_request_bytes":       64 * 1024,
    "max_segundos":              900,
}


def _hash(chave: str) -> str:
    return sha256(chave.encode("utf-8")).hexdigest()


@dataclass
class Cliente:
    client_id: str
    limites: dict[str, int]

    def limite(self, nome: str) -> int:
        return self.limites.get(nome, LIMITES_PADRAO[nome])


class Clientes:
    """
    Registro de clientes. A chave e guardada como HASH, nunca em claro.

    Se o arquivo de clientes vazar, ele nao entrega acesso — entrega hashes. E
    a comparacao usa `compare_digest`, para que o tempo de resposta nao conte
    quantos caracteres da chave estavam certos.
    """

    def __init__(self, arquivo: Path):
        self.arquivo = Path(arquivo)
        self._dados: dict[str, Any] = {}
        if self.arquivo.exists():
            self._dados = json.loads(self.arquivo.read_text(encoding="utf-8"))

    def _salva(self) -> None:
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo.write_text(
            json.dumps(self._dados, ensure_ascii=False, indent=2),
            encoding="utf-8")

    def cria(self, client_id: str, limites: dict[str, int] | None = None) -> str:
        """Devolve a chave em claro UMA vez. Depois so existe o hash."""
        if client_id in self._dados:
            raise ValueError(f"cliente '{client_id}' ja existe")
        chave = f"ak_{secrets.token_urlsafe(32)}"
        self._dados[client_id] = {"hash_chave": _hash(chave),
                                  "limites": limites or {}}
        self._salva()
        return chave

    def autentica(self, chave: str | None) -> Cliente:
        if not chave:
            raise NaoAutorizado("chave ausente")
        h = _hash(chave)
        for cid, d in self._dados.items():
            if hmac.compare_digest(d["hash_chave"], h):
                return Cliente(cid, d.get("limites", {}))
        # mensagem identica para chave inexistente e chave errada: distinguir
        # as duas informa a quem esta tentando adivinhar
        raise NaoAutorizado("chave invalida")

    def existe(self, client_id: str) -> bool:
        return client_id in self._dados


def raiz_do_cliente(base: Path, client_id: str) -> Path:
    """
    `<base>/<client_id>`, com o id validado.

    Um `client_id` como `../outro` transformaria isolamento em travessia de
    diretorio — a defesa e recusar o id, nao normalizar o caminho depois.
    """
    if not client_id or not all(c.isalnum() or c in "-_" for c in client_id):
        raise NaoAutorizado(f"client_id invalido: {client_id!r}")
    return Path(base) / client_id


def confere_limites(entrada: dict, cliente: Cliente,
                    n_queries: int, n_documentos: int,
                    bytes_snapshot: int) -> None:
    """Ultrapassar limite e INVALID com motivo, nunca ERROR nem truncamento."""
    checks = [
        ("max_queries", n_queries, "perguntas"),
        ("max_documentos", n_documentos, "documentos"),
        ("max_snapshot_bytes", bytes_snapshot, "bytes de snapshot"),
        ("max_request_bytes", len(json.dumps(entrada).encode()), "bytes de requisicao"),
    ]
    for nome, valor, unidade in checks:
        lim = cliente.limite(nome)
        if valor > lim:
            raise LimiteExcedido(
                f"{valor} {unidade} excede o limite de {lim} para o cliente "
                f"`{cliente.client_id}`. A auditoria nao roda truncada — "
                f"medir metade do material daria um numero sobre outro sistema."
            )


# ── privacidade de log (item 18) ────────────────────────────────────────────

CAMPOS_DE_LOG = ("audit_id", "client_id", "status", "tempo_s", "erro_tecnico")


def linha_de_log(**kw: Any) -> dict[str, Any]:
    """
    So o que esta em CAMPOS_DE_LOG entra. Query, documento, chave e conteudo de
    snapshot nunca — log e o lugar onde material sensivel sobrevive mais tempo
    e com menos controle de acesso.
    """
    return {k: v for k, v in kw.items() if k in CAMPOS_DE_LOG}
