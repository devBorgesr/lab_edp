"""
tests/test_bancada_sem_edp.py — FASE B5: prova que o telescopio funciona
sozinho.

Subprocess com 'edp' E 'sujeitos' bloqueados via sys.meta_path (mais rigoroso
que so bloquear edp: prova que bancada/ nao depende nem indiretamente de
qualquer pacote sujeitos.*). Importa bancada.* inteiro e roda a auditoria
numa fixture minima, sem nenhum Sujeito concreto envolvido.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_SCRIPT = textwrap.dedent("""
    import sys

    class _BloqueiaSujeito:
        def find_spec(self, name, path, target=None):
            if name == "edp" or name.startswith("edp."):
                raise ModuleNotFoundError(f"'{name}' bloqueado (sem edp)")
            if name == "sujeitos" or name.startswith("sujeitos."):
                raise ModuleNotFoundError(f"'{name}' bloqueado (sem sujeitos)")
            return None

    sys.meta_path.insert(0, _BloqueiaSujeito())

    # bancada/ inteiro importa sem edp nem sujeitos.
    import bancada
    import bancada.prontuario
    import bancada.isolamento
    import bancada.scorer
    import bancada.formatos
    import bancada.sampler
    import bancada.repeater
    import bancada.rodizio
    import bancada.sujeito
    import bancada.auditoria

    # roda a auditoria numa fixture minima, sem sujeito nenhum -- prova que o
    # modo export funciona 100% desacoplado.
    import json
    import tempfile
    import pathlib
    from bancada.auditoria import gerar_relatorio

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "export.jsonl"
        p.write_text(
            json.dumps({"query": "q1", "results": [
                {"id": "1", "texto": "a", "score": 0.9},
                {"id": "1", "texto": "b", "score": 0.5},
            ]}) + "\\n"
        )
        report = gerar_relatorio(str(p))
        assert "Relatorio de Auditoria" in report or "Relat\\u00f3rio de Auditoria" in report
        assert "dup_rate" in report

    # experimental_session/verify_no_leak funcionam com um Sujeito FAKE, sem
    # tocar edp/sujeitos -- prova que o isolamento e agnostico de verdade.
    from bancada.isolamento import experimental_session, new_lab_session_id, verify_no_leak

    class FakeSujeito:
        nome = "fake"
        def abrir_sessao(self):
            return new_lab_session_id()
        def fechar_sessao(self, session_id):
            return {"session_id": session_id, "removed_dirs": []}
        def carregar_snapshot(self, session_id, entries):
            pass
        def consultar(self, session_id, query, k):
            return []
        def fingerprint_producao(self):
            return {"hash": "x"}
        def exportar_producao(self):
            return []

    with experimental_session(FakeSujeito()) as sid:
        assert sid.startswith("__lab__")
    assert verify_no_leak({"hash": "a"}, {"hash": "a"}) is True

    print("BANCADA_SEM_EDP_OK")
""")


def test_bancada_funciona_sem_edp_nem_sujeitos():
    proc = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "BANCADA_SEM_EDP_OK" in proc.stdout
