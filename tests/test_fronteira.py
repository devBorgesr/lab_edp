"""
tests/test_fronteira.py — FASE B5: a fronteira bancada/sujeito vira invariante
executavel.

Varre bancada/ inteiro por AST e falha se qualquer import (absoluto, relativo
que escape do pacote, ou tardio/lazy dentro de funcao ou try/except) resolver
para edp, sujeitos, ou um dos subpacotes nus do EDP. E a versao executavel do
INV-5 invertido: a bancada nao conhece sujeito nenhum.

ast.walk() percorre a arvore inteira (inclui corpos de funcao e blocos
try/except), entao imports tardios sao capturados igual aos de topo de modulo.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANCADA_DIR = ROOT / "bancada"

# edp e sujeitos: os pacotes de sujeito propriamente ditos. Os demais sao
# subpacotes "nus" do EDP — se algum dia acabarem instalados/vendorizados
# soltos (sem o prefixo edp.), o import ainda deve ser barrado aqui.
NOMES_PROIBIDOS = {
    "edp", "sujeitos",
    "runtime", "memory", "llm", "clock", "echo_chamber",
    "retrieval_hybrid", "embeddings", "memory_classifier",
}


def _arquivos_bancada() -> list:
    return sorted(BANCADA_DIR.rglob("*.py"))


def _raiz(nome: str) -> str:
    return nome.split(".")[0] if nome else ""


def _violacoes_do_arquivo(path: Path) -> list:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rel = path.relative_to(ROOT)
    violacoes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _raiz(alias.name) in NOMES_PROIBIDOS:
                    violacoes.append(f"{rel}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level >= 2:
                # relativo que sobe 2+ niveis a partir de um arquivo dentro de
                # bancada/<...>.py escaparia do proprio pacote bancada.
                if node.module and _raiz(node.module) in NOMES_PROIBIDOS:
                    violacoes.append(
                        f"{rel}:{node.lineno}: from {'.' * node.level}{node.module} import ..."
                    )
                continue
            if node.level == 1:
                # relativo dentro do proprio pacote bancada (from .X import Y) — permitido.
                continue
            if node.module and _raiz(node.module) in NOMES_PROIBIDOS:
                violacoes.append(f"{rel}:{node.lineno}: from {node.module} import ...")
    return violacoes


def test_bancada_nao_importa_sujeito_nenhum():
    arquivos = _arquivos_bancada()
    assert arquivos, f"nenhum arquivo .py encontrado em {BANCADA_DIR}"

    todas_violacoes = []
    for path in arquivos:
        todas_violacoes.extend(_violacoes_do_arquivo(path))

    assert not todas_violacoes, (
        "bancada/ importou algo proibido (edp, sujeitos, ou subpacote nu do EDP):\n"
        + "\n".join(todas_violacoes)
    )


def test_lista_de_arquivos_varridos_nao_esta_vazia_nem_suspeita():
    """Guarda-corpo: se bancada/ ficar vazio por engano (ex.: rename mal feito),
    o teste acima passaria trivialmente (sem violacoes porque sem arquivos).
    Confere que ha pelo menos os modulos esperados do nucleo."""
    nomes = {p.stem for p in _arquivos_bancada()}
    esperados = {"prontuario", "isolamento", "scorer", "sujeito", "auditoria"}
    faltando = esperados - nomes
    assert not faltando, f"modulos esperados do nucleo ausentes em bancada/: {faltando}"


def _imports_relativos_de_bancada() -> list:
    """Todo `from .X import ...` ou `from . import X` dentro de bancada/ (nivel 1
    -- o unico permitido pela funcao acima). Devolve (path, lineno, nome_do_alvo)
    por alvo referenciado, ja que `from . import A, B` referencia 2 alvos."""
    alvos = []
    for path in _arquivos_bancada():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level != 1:
                continue
            if node.module:
                # from .X import Y  -> o alvo do import relativo e o proprio X
                alvos.append((path, node.lineno, node.module))
            else:
                # from . import X, Y  -> cada nome importado E um modulo/pacote alvo
                for alias in node.names:
                    alvos.append((path, node.lineno, alias.name))
    return alvos


def test_imports_relativos_de_bancada_apontam_para_arquivo_existente():
    """FASE B6: fecha o ponto cego que deixou 12 `from . import expNNN` quebrados
    passarem no B5 -- test_bancada_nao_importa_sujeito_nenhum (acima) so barra
    NOMES PROIBIDOS; nunca conferiu se o alvo de um import relativo `nivel == 1`
    (permitido, pulado com `continue`) de fato existe em disco. bancada/scorer.py
    tinha 12 call-sites `from . import expNNN` apontando para modulos que so
    existem em sujeitos/edp/experimentos/ -- ImportError garantido em qualquer
    chamada, nunca pego por nenhum teste ate esta FALHAR e forcar o conserto
    (ver RELATORIO_B6.md para a prova de que este teste falha no estado
    anterior a FASE B6 e passa depois)."""
    faltando = []
    for path, lineno, nome in _imports_relativos_de_bancada():
        rel = path.relative_to(ROOT)
        alvo_modulo = BANCADA_DIR / f"{nome}.py"
        alvo_pacote = BANCADA_DIR / nome / "__init__.py"
        if not alvo_modulo.exists() and not alvo_pacote.exists():
            faltando.append(
                f"{rel}:{lineno}: import relativo aponta para '{nome}', mas nem "
                f"bancada/{nome}.py nem bancada/{nome}/__init__.py existem"
            )
    assert not faltando, (
        "import relativo dentro de bancada/ aponta para arquivo inexistente "
        "(ImportError garantido em qualquer chamada que exercite o caminho):\n"
        + "\n".join(faltando)
    )
