"""
test_curadoria_numeros.py — os números da curadoria viram alegação verificada
(Fase 3, 01/09/2026), no mesmo espírito de
`edp_v5/tests/test_catalogo_de_modulos_mortos.py`.

A curadoria (`docs/curadoria/`) afirmou, em tres fases, uma sequencia de
numeros sobre o repositorio `edp_v5` — e errou duas vezes: uma afirmacao sem
medida ("Synapse-Forge vazio"), uma maturidade `TESTADO` nunca confirmada por
execucao, e uma contagem de modulos mortos errada por 4x (6 declarados, 2
reais, porque duas rodadas da mesma heuristica escanearam populacoes
diferentes do repositorio sem que ninguem notasse a divergencia).

Isso e o problema do proprio `test_catalogo_de_modulos_mortos.py`, um nivel
acima: la, prosa nao conferida apodreceu; aqui, MEDICAO nao conferida
divergiu de uma rodada para a outra. O remedio e o mesmo — o numero vira
teste, ou deixa de ser afirmado.

O QUE ESTE ARQUIVO TRAVA

  - modulos de topo de edp/edp: 40 arquivos soltos + 9 subpacotes = 49
  - mortos (sem importador em TODO o repo edp_v5, AST): 2 — analytics, reranker
  - flags booleanas 0/1 em edp/config.py: 19, das quais 12 default OFF

O QUE ESTE ARQUIVO NAO TRAVA, E DIZ POR QUE

  - "21 capacidades" (MAPA_CAPACIDADES.md) e AGRUPAMENTO por julgamento, nao
    contagem automatica — duas pessoas descreveriam o kernel em números
    diferentes de capacidades sem estarem em desacordo sobre o que existe;
  - a classificacao "3 agora / 4 depois / 6 teste / 2 experimento" e
    JULGAMENTO DE RISCO (muda a regua? tem teste? depende de outra coisa
    rodar primeiro?), nao uma contagem que um script possa reproduzir sem
    reimplementar o julgamento inteiro.

Para esses dois, o teste verifica CONSISTENCIA INTERNA da documentacao (o que
o README resume bate com o que os documentos individuais listam) — nao
verdade contra a realidade do kernel. Forjar uma metrica automatica para um
agrupamento humano seria pior que nao ter metrica nenhuma.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parent.parent
CURADORIA = LAB / "docs" / "curadoria"

EDP_V5 = Path(os.environ.get("EDP_V5_PATH", "/media/sf_edp_v5_main"))
IGNORAR_DIRS = {".venv", "graphify-out", ".git", "node_modules", "__pycache__"}

pytestmark = pytest.mark.skipif(
    not (EDP_V5 / "edp" / "config.py").exists(),
    reason=(f"checkout do edp_v5 nao encontrado em {EDP_V5} (defina "
            f"EDP_V5_PATH); os numeros da curadoria nao podem ser conferidos "
            f"sem o repositorio irmao"),
)


def _fontes_edp_v5() -> list[Path]:
    """Mesma tecnica de `test_catalogo_de_modulos_mortos.py`: os.walk poda
    diretorios pesados em vez de rglob descer neles primeiro."""
    out = []
    for dirpath, dirnames, filenames in os.walk(EDP_V5):
        dirnames[:] = [d for d in dirnames if d not in IGNORAR_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                out.append(Path(dirpath) / f)
    return out


def _unidades_de_topo() -> tuple[list[str], list[str]]:
    edp = EDP_V5 / "edp"
    flat = sorted(p.stem for p in edp.glob("*.py") if p.stem != "__init__")
    pacotes = sorted(p.name for p in edp.iterdir()
                     if p.is_dir() and p.name != "__pycache__"
                     and (p / "__init__.py").exists())
    return flat, pacotes


def _importadores_reais(unidades: list[str], fontes: list[Path]) -> dict[str, set[str]]:
    """AST no repo INTEIRO — a mesma regra do gate canonico do edp_v5.
    Duas rodadas desta funcao, ontem e hoje, precisam bater; se nao baterem,
    o bug esta aqui, nao no kernel."""
    usos: dict[str, set[str]] = {m: set() for m in unidades}
    for p in fontes:
        try:
            arv = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for no in ast.walk(arv):
            if isinstance(no, ast.Import):
                alvos = [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom):
                alvos = [no.module or ""] + [
                    f"{no.module or ''}.{a.name}" for a in no.names]
            else:
                continue
            for alvo in alvos:
                partes = alvo.split(".")
                for m in unidades:
                    if m in partes and p.stem != m:
                        rel = p.relative_to(EDP_V5)
                        if str(rel).startswith(f"edp/{m}/") or str(rel) == f"edp/{m}.py":
                            continue  # auto-import de dentro do proprio pacote
                        usos[m].add(str(rel))
    return usos


# ── os tres numeros que SAO medicao direta ──────────────────────────────────

def test_total_de_unidades_de_topo_e_49():
    flat, pacotes = _unidades_de_topo()
    total = len(flat) + len(pacotes)
    assert total == 49, (
        f"edp/ tem {len(flat)} arquivos soltos + {len(pacotes)} subpacotes "
        f"= {total}, nao 49. INVENTARIO_ECOSSISTEMA.md precisa ser corrigido "
        f"junto com este teste — nunca so o teste."
    )


def test_modulos_mortos_no_edp_v5_sao_exatamente_dois():
    """
    O numero que a Fase 1/2 errou por 4x (6 declarados, 2 reais). Trava contra
    a MESMA regra do gate canonico do proprio edp_v5
    (test_catalogo_de_modulos_mortos.py): AST, repo inteiro via os.walk, nao
    so edp/+tests/.
    """
    flat, pacotes = _unidades_de_topo()
    fontes = _fontes_edp_v5()
    usos = _importadores_reais(flat + pacotes, fontes)
    mortos = sorted(m for m, imp in usos.items() if not imp)
    assert mortos == ["analytics", "reranker"], (
        f"modulos sem importador no edp_v5 inteiro: {mortos}. "
        f"A curadoria (MAPA_CAPACIDADES.md, INVENTARIO_ECOSSISTEMA.md) afirma "
        f"exatamente ['analytics', 'reranker'] — se este teste falhar, o "
        f"kernel mudou (alguem passou a importar um modulo morto, ou parou "
        f"de importar um que estava vivo) e os documentos precisam ser "
        f"reconferidos, nao apenas este teste ajustado."
    )


def test_flags_desligadas_por_default_sao_doze():
    cfg = (EDP_V5 / "edp" / "config.py").read_text(encoding="utf-8")
    flags = re.findall(
        r'^([A-Z_]+)\s*=\s*os\.environ\.get\("([^"]+)",\s*"([^"]*)"\)\s*==\s*"1"',
        cfg, re.M)
    off = [f for f in flags if f[2] != "1"]
    assert len(flags) == 19, (
        f"{len(flags)} flags no padrao os.environ.get(X,\"0\")==\"1\" em "
        f"config.py, nao 19. MAPA_FLAGS.md cataloga exatamente 19."
    )
    assert len(off) == 12, (
        f"{len(off)} flags desligadas por default, nao 12: "
        f"{sorted(n for n,_,_ in off)}"
    )


# ── consistencia interna da documentacao — NAO verdade contra o kernel ──────

def _le(nome: str) -> str:
    p = CURADORIA / nome
    assert p.exists(), f"{nome} deveria existir em docs/curadoria/"
    return p.read_text(encoding="utf-8")


def test_readme_lista_todos_os_documentos_da_curadoria():
    """Um documento novo sem entrada no README e um documento invisivel."""
    readme = _le("README.md")
    esperados = [
        "INVENTARIO_ECOSSISTEMA.md", "MAPA_CAPACIDADES.md", "MAPA_FLAGS.md",
        "MAPA_PROVENIENCIA.md", "CANDIDATOS_ACOPLAMENTO_MVP.md",
        "CANDIDATOS_NOVOS_SERVICOS.md", "LACUNAS_E_NAO_VERIFICADO.md",
        "DECISAO_ACOPLAMENTO.md",
    ]
    for nome in esperados:
        assert nome in readme, f"{nome} existe mas nao esta listado no README"
        assert (CURADORIA / nome).exists(), f"README lista {nome}, mas o arquivo nao existe"


def test_candidatos_de_acoplamento_batem_com_o_resumo():
    """
    3/4/6/2 nao sao contaveis automaticamente (sao classificacao por
    julgamento de risco) — mas o NUMERO DE SECOES em cada categoria do
    documento fonte precisa bater com o que o README resume. Isso pega o
    caso real: alguem move um candidato de categoria no CANDIDATOS_*.md e
    esquece de atualizar o resumo executivo.
    """
    doc = _le("CANDIDATOS_ACOPLAMENTO_MVP.md")
    readme = _le("README.md")

    agora = len(re.findall(r"^## ACOPLAR AGORA \((\d+)\)", doc, re.M))
    n_agora = int(re.search(r"## ACOPLAR AGORA \((\d+)\)", doc).group(1))
    n_depois = int(re.search(r"## ACOPLAR DEPOIS DO PILOTO \((\d+)\)", doc).group(1))
    n_teste = int(re.search(r"## PRECISA DE TESTE ANTES \((\d+)\)", doc).group(1))
    n_exp = int(re.search(r"## PRECISA DE EXPERIMENTO \((\d+)\)", doc).group(1))

    declarados_no_doc = {"agora": n_agora, "depois": n_depois,
                         "teste": n_teste, "experimento": n_exp}
    resumo = {
        "agora": int(re.search(r"ACOPLÁVEIS AGORA \.+\s*(\d+)", readme).group(1)),
        "depois": int(re.search(r"ACOPLÁVEIS DEPOIS DO PILOTO \.+\s*(\d+)", readme).group(1)),
        "teste": int(re.search(r"PRECISAM DE TESTE \.+\s*(\d+)", readme).group(1)),
        "experimento": int(re.search(r"PRECISAM DE EXPERIMENTO \.+\s*(\d+)", readme).group(1)),
    }
    assert declarados_no_doc == resumo, (
        f"CANDIDATOS_ACOPLAMENTO_MVP.md declara {declarados_no_doc}, "
        f"README resume {resumo} — divergiram."
    )


def test_novos_servicos_batem_com_o_resumo():
    doc = _le("CANDIDATOS_NOVOS_SERVICOS.md")
    readme = _le("README.md")
    n_servicos = len(re.findall(r"^## SERVIÇO [A-Z] —", doc, re.M))
    n_resumo = int(re.search(r"NOVOS SERVIÇOS CANDIDATOS \.+\s*(\d+)", readme).group(1))
    assert n_servicos == n_resumo, (
        f"{n_servicos} serviços com cabeçalho `## SERVIÇO X —` em "
        f"CANDIDATOS_NOVOS_SERVICOS.md, README resume {n_resumo}"
    )


def test_lacunas_fechadas_nao_sao_mais_sete():
    """
    A Fase 2 declarava 7 NAO_VERIFICADO. A Fase 3 fechou os 7. Se alguem
    reabrir um item sem atualizar o resumo do README, este teste pega.
    """
    readme = _le("README.md")
    n = int(re.search(r"NÃO VERIFICADAS \.+\s*(\d+)", readme).group(1))
    assert n == 0, (
        f"README declara {n} NAO_VERIFICADAS; a Fase 3 fechou os 7 originais "
        f"e o README deveria dizer 0 (com ACHADOS_FORA_DE_ESCOPO documentando "
        f"o que apareceu fora do escopo dos 7, sem virar item NAO_VERIFICADO "
        f"disfarçado)."
    )
    lacunas = _le("LACUNAS_E_NAO_VERIFICADO.md")
    for item in ("1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"):
        assert f"### {item}" in lacunas, f"item {item} sem seção de fechamento"


def test_decisao_de_acoplamento_existe_e_esta_em_branco():
    """
    A curadoria apresenta o custo de cada caminho; ela nao escolhe. Se o
    campo de decisao deixar de estar em branco, alguem decidiu pela
    curadoria — o mesmo erro que DECISAO_RANKING.md existe para impedir do
    lado cientifico.
    """
    doc = _le("DECISAO_ACOPLAMENTO.md")
    assert "decidido por" in doc.lower()
    linha = re.search(r"decidido por \.+\s*(.*)", doc, re.I)
    assert linha, "campo 'decidido por' ausente"
    preenchido = linha.group(1).strip().strip("_").strip()
    assert not preenchido, (
        f"DECISAO_ACOPLAMENTO.md tem 'decidido por' preenchido "
        f"({preenchido!r}) — a decisao deveria estar em branco, esperando "
        f"o pesquisador."
    )
