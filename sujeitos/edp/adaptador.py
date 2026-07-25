"""
sujeitos.edp.adaptador — SujeitoEDP: ensina a bancada a falar EDP.

Implementa o Protocol Sujeito (bancada/sujeito.py) sobre o runtime edp. Todo
conhecimento de schema de sessao, layout em disco e atributos privados do
MemoryStore mora AQUI — a bancada nunca importa isto, so o Protocol.

Migrado de isolation.py e exp008.py (FASE B3): a bancada nao pode mais saber
nada de "sessions/<id>_cognitive/episodic.json" nem de "mem._episodic.entries".
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from bancada.isolamento import LAB_PREFIX, is_lab_session, new_lab_session_id

logger = logging.getLogger("sujeitos.edp.adaptador")


def _sessions_root() -> Path:
    """Raiz das sessoes em disco. Espelha config.MEMORY_DIR = EDP_BASE_DIR /
    'sessions' SEM importar config (mantem o adaptador leve e desacoplado)."""
    base = os.environ.get("EDP_BASE_DIR", "data")
    return Path(base) / "sessions"


class SujeitoEDP:
    """Adaptador EDP do Protocol Sujeito (bancada/sujeito.py)."""

    nome = "edp"

    def __init__(self, prod_session: str = "default", scope: str = "cognitive"):
        self.prod_session = prod_session
        self.scope = scope
        try:
            from bancada.prontuario import set_clock
            from edp.clock import is_verified, now
            set_clock(now, is_verified)
        except Exception as e:
            logger.debug("[adaptador] set_clock falhou: %s", e)

    # ── sessao (ex-isolation.py: experimental_session) ──────────────────────
    def abrir_sessao(self) -> str:
        """Cria sessao ISOLADA da producao: prefixo __lab__, scope proprio no
        registry. Livre dos jobs de background (presos a session_id='default')."""
        session_id = new_lab_session_id()
        try:
            from edp.runtime.registry import get_memory
            mem = get_memory(session_id)
            try:
                mem.set_scope(self.scope)
            except Exception as e:
                logger.debug("[adaptador] set_scope(%s) falhou: %s", self.scope, e)
        except Exception as e:
            logger.debug("[adaptador] get_memory(%s) falhou: %s", session_id, e)
        logger.info("[adaptador] sessao ABERTA: %s | scope=%s", session_id, self.scope)
        return session_id

    def fechar_sessao(self, session_id: str) -> dict:
        """Purga a sessao: registry (memoria) + disco. DESCARTAVEL.

        GUARDA DURA (mantida byte a byte da isolation.py original): so opera em
        sessoes __lab__. Purgar producao LEVANTA excecao — nunca se apaga
        producao por engano. A delecao em disco RE-confere, por caminho, que o
        nome do diretorio contem o id de lab antes de remover.
        """
        if not is_lab_session(session_id):
            raise ValueError(
                f"fechar_sessao RECUSADO: '{session_id}' nao tem prefixo "
                f"'{LAB_PREFIX}'. Producao NUNCA e purgada por esta funcao."
            )
        try:
            from edp.runtime.registry import reset_session
            reset_session(session_id)
        except Exception as e:
            logger.debug("[adaptador] reset_session(%s) falhou: %s", session_id, e)
        removed_dirs = []
        root = _sessions_root()
        if root.exists():
            for d in root.glob(f"{session_id}_*"):
                if not d.is_dir():
                    continue
                try:
                    if LAB_PREFIX not in d.name or session_id not in d.name:
                        logger.warning("[adaptador] dir suspeito IGNORADO no purge: %s", d)
                        continue
                    shutil.rmtree(d)
                    removed_dirs.append(str(d))
                except Exception as e:
                    logger.warning("[adaptador] rmtree(%s) falhou: %s", d, e)
        logger.info(
            "[adaptador] purga | sessao=%s | dirs_removidos=%d",
            session_id, len(removed_dirs),
        )
        return {"session_id": session_id, "removed_dirs": removed_dirs}

    # ── snapshot (ex-exp008.py L352-362) ────────────────────────────────────
    def carregar_snapshot(self, session_id: str, entries: list) -> None:
        """Injeta o corpus clonado na sessao isolada.

        Fix A, descoberto via inspect_cognitive.py (exp008): o retrieve real
        le de mem._episodic.entries (ou mem._cognitive.episodic.entries em
        builds mais novas do EDP), nao de mem.entries. Escreve nos tres para
        cobrir a forma que a build instalada usar.

        RISCO: atributo privado do MemoryStore — quebra silenciosamente se o
        EDP renomear/reestruturar esses campos num refactor futuro do store.
        """
        from edp.runtime.registry import get_memory
        mem = get_memory(session_id)
        clone = copy.deepcopy(entries)
        mem.entries = clone
        if hasattr(mem, "_episodic") and hasattr(mem._episodic, "entries"):
            mem._episodic.entries = clone
        elif hasattr(mem, "_cognitive") and hasattr(mem._cognitive, "episodic"):
            mem._cognitive.episodic.entries = clone

    # ── consulta (ex-exp008.py: mem.retrieve) ───────────────────────────────
    def consultar(self, session_id: str, query: str, k: int) -> list:
        """Retrieve real sobre a sessao isolada.

        layers fixo em ["episodic"]: unico consumidor migrado ate aqui
        (exp008, categoria retrieval-quality sobre o cognitive episodic). v2
        do Protocol pode expor layers/min_score se outro sujeito precisar.

        Retorna os dicts originais do EDP (id, text, ranking_score,
        cognitive_decisions, source_type, ...) ACRESCIDOS das chaves do
        contrato (texto, score) — o Protocol pede "no minimo" essas chaves,
        nao troca as demais. Quem so conhece o Protocol usa texto/score; quem
        (ainda) precisa de campos EDP especificos (ex.: exp008) continua
        achando-os no mesmo dict.
        """
        from edp.runtime.registry import get_memory
        mem = get_memory(session_id)
        pool = mem.retrieve(query, top_k=k, min_score=0.0, layers=["episodic"])
        out = []
        for item in pool:
            row = dict(item)
            row["texto"] = item.get("text", "")
            row["score"] = float(item.get("ranking_score", 0.0) or 0.0)
            out.append(row)
        return out

    # ── producao (ex-isolation.py cognitive_fingerprint / exp008.py load_cognitive_clone) ─
    def fingerprint_producao(self) -> dict:
        """Fingerprint do exocortex cognitive da producao (em disco). Disco e a
        verdade do EDP: le episodic.json/semantic.json e tira um hash. Antes ==
        depois prova que o experimento nao tocou a memoria cognitiva (INV-5)."""
        root = _sessions_root() / f"{self.prod_session}_cognitive"
        out = {"session": self.prod_session, "episodic_n": 0, "semantic_n": 0, "hash": "0" * 16}
        try:
            blobs = []
            for name, key in (("episodic.json", "episodic_n"), ("semantic.json", "semantic_n")):
                p = root / name
                if p.exists():
                    raw = p.read_text(encoding="utf-8")
                    blobs.append(raw)
                    try:
                        data = json.loads(raw)
                        if isinstance(data, list):
                            out[key] = len(data)
                        elif isinstance(data, dict):
                            out[key] = len(data.get("entries", data))
                    except Exception:
                        pass
            out["hash"] = hashlib.sha256("".join(blobs).encode("utf-8")).hexdigest()[:16]
        except Exception as e:
            logger.debug("[adaptador] fingerprint falhou: %s", e)
        return out

    def exportar_producao(self) -> list:
        """Clone READ-ONLY das entries do scope cognitive de producao — SEM
        chamar retrieve, SEM mutar, SEM salvar.

        DISCO PRIMEIRO (verdade da casa): le episodic.json direto — garantido
        nao-mutante. Evita de proposito construir get_memory(), cujo __init__
        roda _migrate_legacy_session_files (memory.py:1386) — um possivel
        WRITE em producao. Fallback (so se o disco falhar): registry em RAM.
        """
        try:
            p = _sessions_root() / f"{self.prod_session}_cognitive" / "episodic.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data = data.get("entries", [])
                if isinstance(data, list) and data:
                    return copy.deepcopy(data)
        except Exception as e:
            logger.warning("[adaptador] clone do disco falhou (%s); tentando registry", e)
        try:
            from edp.runtime.registry import get_memory, is_valid
            mem = get_memory(self.prod_session)
            if is_valid(mem):
                cog = getattr(mem, "_cognitive_view", None)
                if cog is not None:
                    return copy.deepcopy(list(cog.episodic.entries))
        except Exception as e:
            logger.warning("[adaptador] registry clone falhou: %s", e)
        return []
