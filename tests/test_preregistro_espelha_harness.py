"""
test_preregistro_espelha_harness.py — a tabela de constantes congeladas vale o
que vale a checagem dela (14/08/2026).

O `edp_v5` ganhou esse gate em 13/08 depois que o exp008 foi flagrado rodando
FORA do proprio congelamento: `POOL_SIZE` congelado em 50, rodando em 100
desde o commit que anuncia o "segundo disparo real", sem nota de desvio em
lugar nenhum, por dois meses.

Aquele gate globa `edp_v5/edp/lab/` e **nao alcanca este repositorio**. Os
pre-registros NATIVOS do lab (E7, Fase 2, E9) estavam fora de qualquer
verificacao. Este arquivo fecha isso do lado de ca.

Mesma regra, mesma assimetria: divergencia NAO declarada quebra o build;
desvio declarado numa secao `§N-bis` passa, com o valor real exigido. Declarar
custa uma linha de tabela; mudar em silencio custa vermelho.
"""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
HARNESSES = RAIZ / "sujeitos" / "edp" / "experimentos"

# | `NOME` <glosa opcional> | `literal` |
# O sufixo `[^|`]*` aceita a glosa da celula do nome mas NAO um segundo
# backtick, entao duas constantes numa celula ficam de fora — nao da para
# casar dois nomes com um valor.
LINHA = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]*)`[^|`]*\|\s*`([^`]+)`[^|]*\|", re.M)

# (pre-registro, harness) — par explicito em vez de glob, porque a nomenclatura
# do lab e por letra (E7, E9) e nao casa com `expNNN` por regra simples.
PARES = [
    ("preregistro_experimento_e9.md", "exp_e9.py"),
    # auto-ativa quando o harness aterrissar; ate la o par e ignorado por
    # nao existir o .py, o que e melhor que esquecer de registra-lo depois.
    ("preregistro_experimento_e9b.md", "exp_e9b.py"),
    ("preregistro_experimento_e9c.md", "exp_e9c.py"),
]


def _literal(txt: str):
    try:
        return ast.literal_eval(txt.strip())
    except (ValueError, SyntaxError):
        return None


def _tabelas(md: str) -> tuple[dict, dict]:
    """
    (congeladas, desvios_declarados).

    NAO corta o documento no primeiro `-bis`: o E9 tem `§7-bis` (topologia)
    ANTES da tabela congelada do `§11`, e cortar ali jogava fora a tabela
    inteira — o parser voltava vazio e os testes passavam sem conferir nada.
    Foi assim que este arquivo falhou na primeira execucao, e e exatamente o
    modo de falha que `test_o_gate_morde` existe para pegar.

    Congeladas saem do documento INTEIRO; desvios saem so das linhas de 3+
    colunas das secoes `-bis`, onde a 3a coluna e o valor REAL. Quando um nome
    aparece nos dois, o desvio vence — declarado supera congelado, que e a
    regra.
    """
    congeladas = {}
    for nome, val in LINHA.findall(md):
        lit = _literal(val)
        if lit is not None:
            congeladas[nome] = lit

    desvios = {}
    for bloco in re.split(r"^##\s+", md, flags=re.M):
        if not re.match(r"§\d+-bis", bloco):
            continue
        for ln in bloco.splitlines():
            celulas = [c.strip() for c in ln.split("|")[1:-1]]
            if len(celulas) >= 3 and re.fullmatch(r"`[A-Z][A-Z0-9_]*`", celulas[0]):
                lit = _literal(celulas[2].strip("`"))
                if lit is not None:
                    desvios[celulas[0].strip("`")] = lit
    return congeladas, desvios


def _carrega(caminho: Path):
    """
    Registra em sys.modules antes de executar.

    Sem isso, `@dataclass` estoura com AttributeError ao procurar o modulo
    dono da classe — falha que parece do arquivo testado e e do carregador.
    """
    spec = importlib.util.spec_from_file_location(caminho.stem, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[caminho.stem] = mod
    spec.loader.exec_module(mod)
    return mod


CASOS = [
    pytest.param(DOCS / md, HARNESSES / py, id=py.replace(".py", ""))
    for md, py in PARES
    if (DOCS / md).exists() and (HARNESSES / py).exists()
]


def test_ha_pares_para_conferir():
    """Se a lista esvaziar, os testes abaixo passariam vazios — teste-teatro."""
    assert CASOS, f"nenhum par pre-registro/harness encontrado: {PARES}"


@pytest.mark.parametrize("md_path,py_path", CASOS)
def test_constantes_congeladas_batem_com_o_harness(md_path, py_path):
    congeladas, desvios = _tabelas(md_path.read_text(encoding="utf-8"))
    mod = _carrega(py_path)

    divergencias = []
    for nome, esperado in congeladas.items():
        if not hasattr(mod, nome):
            continue  # constante so do documento
        real = getattr(mod, nome)
        alvo = desvios.get(nome, esperado)
        if real != alvo:
            marca = " (desvio declarado)" if nome in desvios else ""
            divergencias.append(
                f"{nome}: {py_path.name} tem {real!r}, {md_path.name} exige {alvo!r}{marca}"
            )

    assert not divergencias, (
        "constante congelada divergiu do pre-registro sem desvio declarado:\n  "
        + "\n  ".join(divergencias)
        + "\n\nDeclare o desvio numa secao §N-bis (congelado | real | quando | commit) "
          "em vez de editar a tabela congelada."
    )


@pytest.mark.parametrize("md_path,py_path", CASOS)
def test_cobertura_e_declarada(md_path, py_path, capsys):
    """
    Quantas constantes o gate realmente confere.

    Um gate que confere 1 de 20 linhas e nao diz isso e pior que nenhum: da a
    sensacao de cobertura sem a cobertura.
    """
    congeladas, _ = _tabelas(md_path.read_text(encoding="utf-8"))
    mod = _carrega(py_path)
    conferidas = sorted(n for n in congeladas if hasattr(mod, n))
    print(f"\n{md_path.name}: {len(conferidas)} constantes conferidas -> {conferidas}")
    assert conferidas, f"parser nao extraiu nenhuma constante de {md_path.name}"


def test_o_gate_morde():
    """
    Prova que ele acusa, em vez de confiar que acusa.

    Injeta uma divergencia num modulo falso e verifica que a comparacao a
    encontra. Sem isto, os testes acima passariam igualmente contra um parser
    que nao extrai nada.
    """
    md = (DOCS / "preregistro_experimento_e9.md").read_text(encoding="utf-8")
    congeladas, _ = _tabelas(md)
    assert "N_REPETICOES" in congeladas, "parser perdeu N_REPETICOES da tabela §11"

    class _Falso:
        pass
    falso = _Falso()
    for nome, val in congeladas.items():
        setattr(falso, nome, val)
    setattr(falso, "N_REPETICOES", congeladas["N_REPETICOES"] + 1)  # sabotagem

    divergiu = [n for n, v in congeladas.items() if getattr(falso, n, v) != v]
    assert divergiu == ["N_REPETICOES"], (
        f"gate nao pegou a sabotagem (achou {divergiu}) — seria teatro"
    )


def test_e9_nao_declara_medir_energia():
    """
    REGRESSAO 14/08: o §3.1 declara que joule NAO e medivel nesta maquina
    (RAPL ausente no guest, Windows sem joule por processo).

    Se alguem inserir metrica de energia no harness sem refazer o Passo 0, o
    documento passa a mentir sobre o proprio escopo. Este teste trava a
    fronteira em vez de confiar na memoria de quem editar depois.

    Proibe o MECANISMO, nao a palavra. A primeira versao deste teste barrava a
    string "rapl" e reprovava o proprio docstring do harness, que existe para
    EXPLICAR que RAPL esta ausente. Proibir mencao censura a declaracao;
    proibir mecanismo trava o escopo. Sao coisas opostas.
    """
    fonte = (HARNESSES / "exp_e9.py").read_text(encoding="utf-8").lower()

    assert "/sys/class/powercap" not in fonte, (
        "exp_e9.py le o contador RAPL — o §3.1 declara energia NAO medivel "
        "nesta maquina. Refaca o Passo 0 e emende o pre-registro antes."
    )
    atribuicao = re.search(r"\b(joules?|watts?|energia)\s*=", fonte)
    assert atribuicao is None, (
        f"exp_e9.py calcula '{atribuicao.group(1)}' — o §12 declara que nenhum "
        "resultado do E9 autoriza conclusao em joule ou watt."
    )
