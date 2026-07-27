"""
bancada.isolamento — Isolamento experimental da Bancada (Bug 3 da varredura),
agnostico de sujeito.

O PROBLEMA (achado no espelho, no EDP): campos mutaveis compartilhados num
singleton por-sessao, lidos ASSINCRONAMENTE por jobs de background, tornam
trocar o escopo da sessao de PRODUCAO para rodar experimento uma CORRIDA: um
job disparando no meio pode jogar conteudo experimental na memoria de
producao. Isso contamina o sujeito e invalida o prontuario.

A SOLUCAO (por construcao, nao por corrida): todo experimento roda numa
SESSAO DEDICADA e DESCARTAVEL, "__lab__<uuid>". A bancada so sabe que existe
esse prefixo e que o Sujeito sabe abrir/fechar essa sessao isolada — como a
sessao e fisicamente separada da producao (registry, disco, schema) e
conhecimento do adaptador (sujeitos/<nome>/adaptador.py), nunca daqui.

INV-1 (isolamento) e INV-5 (producao intocada) moram aqui, expressos sobre o
Protocol Sujeito (bancada/sujeito.py) — nao sobre um sistema concreto.

SEGURANCA: o prefixo "__lab__" e a unica coisa que a bancada exige de um
session_id de lab. A guarda dura de purge (recusar apagar producao) e
responsabilidade do Sujeito.abrir_sessao/fechar_sessao — a bancada so chama.

NAO-GATE: abrir uma sessao descartavel nao toca producao, entao isolamento
nao e travado por nenhuma env var de "armado". O gate de disparo real vive no
sujeito/runner (onde o experimento de fato manda ao modelo).
"""
from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .sujeito import Sujeito

logger = logging.getLogger("bancada.isolamento")

# Prefixo que marca uma sessao como de laboratorio. Nenhuma sessao de producao
# usa este prefixo — e o que torna o purge seguro em qualquer sujeito.
LAB_PREFIX = "__lab__"


def new_lab_session_id() -> str:
    """Gera um session_id de lab unico: '__lab__<12hex>'."""
    return f"{LAB_PREFIX}{uuid.uuid4().hex[:12]}"


def is_lab_session(session_id: str) -> bool:
    """True se o session_id e de laboratorio (prefixo __lab__)."""
    return isinstance(session_id, str) and session_id.startswith(LAB_PREFIX)


@contextmanager
def experimental_session(sujeito: Sujeito, purge: bool = True) -> Iterator[str]:
    """Context manager: entrega uma sessao de lab DEDICADA e ISOLADA do sujeito.

    Isolamento por construcao (Bug 3): quem sabe separar a sessao de lab da
    producao (registry, disco, schema) e o sujeito — a bancada so abre/fecha.

    Ao sair, a sessao e purgada (descartavel) via sujeito.fechar_sessao — a
    menos que purge=False, para inspecao pos-morte de um experimento.

    Uso:
        with experimental_session(sujeito) as session_id:
            sujeito.carregar_snapshot(session_id, entries)
            resultados = sujeito.consultar(session_id, query, k)
        # aqui a sessao ja foi purgada; producao intocada.
    """
    session_id = sujeito.abrir_sessao()
    logger.info("[isolamento] sessao de lab ABERTA: %s | sujeito=%s", session_id, sujeito.nome)
    try:
        yield session_id
    finally:
        if purge:
            try:
                sujeito.fechar_sessao(session_id)
            except Exception as e:
                logger.warning("[isolamento] purga de %s falhou: %s", session_id, e)
        else:
            logger.info("[isolamento] sessao de lab MANTIDA (purge=False): %s", session_id)


def verify_no_leak(before: dict, after: dict) -> bool:
    """True se a memoria da producao esta INALTERADA (sem vazamento).
    Comparacao por hash (forte) + contagens (informativas)."""
    return (
        before.get("hash") == after.get("hash")
        and before.get("episodic_n") == after.get("episodic_n")
        and before.get("semantic_n") == after.get("semantic_n")
    )


def production_contains(sentinel: str, root: Path) -> bool:
    """True se o texto sentinela aparece em algum arquivo direto sob `root`.
    Usado para provar que conteudo experimental NAO vazou para a producao.
    `root` e responsabilidade de quem chama (o sujeito conhece o layout em
    disco da producao) — esta funcao nao presume schema nenhum."""
    root = Path(root)
    try:
        for p in root.iterdir() if root.exists() else ():
            if p.is_file() and sentinel in p.read_text(encoding="utf-8"):
                return True
    except Exception as e:
        logger.debug("[isolamento] production_contains falhou: %s", e)
    return False
