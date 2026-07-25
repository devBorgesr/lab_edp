"""
Teste de fumaça (FASE B1) — cada modulo da raiz importa isolado, em subprocess,
COM e SEM 'edp' disponivel no ambiente. Bloqueio de 'edp' via sys.meta_path
(sem precisar de venv separada).

Criterio de saida do B1: prontuario, isolation, scorer e window_formats
importam nos dois cenarios. Os exp0NN podem falhar (tipicamente por ausencia
de 'edp') — este teste registra o motivo de cada falha, sem exigir sucesso.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Modulos que a FASE B1 promete deixar importaveis, com ou sem edp.
NUCLEO_OBRIGATORIO = ["prontuario", "isolation", "scorer", "window_formats"]

# Demais modulos da raiz: informativos apenas (podem depender de edp/sibling
# relativo ainda nao resolvido antes da reestruturacao da FASE B2).
OUTROS_MODULOS = [
    "sampler", "repeater", "rodizio",
    "exp001", "exp003", "exp004", "exp006", "exp006b", "exp007",
    "exp008", "exp009", "exp010", "run_once",
]

_BLOQUEIA_EDP = """\
import sys

class _BloqueiaEDP:
    def find_spec(self, name, path, target=None):
        if name == "edp" or name.startswith("edp."):
            raise ModuleNotFoundError(
                f"'{name}' bloqueado neste teste (simula ambiente sem edp)"
            )
        return None

sys.meta_path.insert(0, _BloqueiaEDP())
"""


def _tenta_importar(module_name: str, *, bloquear_edp: bool) -> tuple[bool, str]:
    script = (_BLOQUEIA_EDP if bloquear_edp else "") + f"\nimport {module_name}\n"
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    erro = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ""
    return proc.returncode == 0, erro


def test_nucleo_importa_sem_edp():
    falhas = {}
    for mod in NUCLEO_OBRIGATORIO:
        ok, erro = _tenta_importar(mod, bloquear_edp=True)
        if not ok:
            falhas[mod] = erro
    assert not falhas, f"nucleo deveria importar sem edp instalado: {falhas}"


def test_nucleo_importa_com_edp():
    falhas = {}
    for mod in NUCLEO_OBRIGATORIO:
        ok, erro = _tenta_importar(mod, bloquear_edp=False)
        if not ok:
            falhas[mod] = erro
    assert not falhas, f"nucleo deveria importar com edp instalado: {falhas}"


def test_outros_modulos_registra_motivo_de_falha(capsys):
    """Nao exige sucesso: so registra, por modulo, se falhou e por que.
    Uso: `pytest tests/test_imports.py -k outros -s` para ver a lista."""
    resultados = {}
    for mod in OUTROS_MODULOS:
        ok, erro = _tenta_importar(mod, bloquear_edp=True)
        resultados[mod] = "OK" if ok else erro
    linhas = "\n".join(f"  {m}: {r}" for m, r in resultados.items())
    print(f"\n[test_imports] modulos fora do nucleo (sem edp):\n{linhas}")
