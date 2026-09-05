"""
A governança de capacidades, como TESTE e não como comentário.

O QUE ESTES TESTES EXISTEM PARA IMPEDIR

`DECISAO_ATUACAO.md` aparece em oito lugares do código — todos em string de
erro ou comentário. **Nenhum caminho lê o arquivo.** A trava real é o booleano
`implementada=False` no catálogo, e um booleano é uma linha: quem virasse
`act.click` para `True` faria `exige_implementada()`, `para_tarefa()` e a
`Politica` passarem todos, sem que assinatura nenhuma tivesse acontecido.

Estes testes ligam as duas coisas. A regra deixa de ser "está escrito que
precisa de assinatura" e passa a ser "a suíte falha se não houver".

Vale também para `VISAO_ATIVOS_E_ROADMAP.md`: o documento declara direções, e o
risco de um documento de direção é virar lista de tarefas sem passar pelo
fluxo. `test_nomes_da_visao_nao_sao_implementacao` é o que impede isso — um
nome só sai da visão para o catálogo quebrando este teste, o que obriga a
passar por decisão.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agent_runtime.capacidades import CATALOGO, Nivel                   # noqa: E402

DECISAO = RAIZ / "docs" / "agent_runtime" / "DECISAO_ATUACAO.md"
VISAO = RAIZ / "docs" / "agent_runtime" / "VISAO_ATIVOS_E_ROADMAP.md"

#: Linha de assinatura em branco: seis ou mais sublinhados seguidos.
_EM_BRANCO = re.compile(r"_{6,}")

#: Nomes de capacidade que a visão cita como DIREÇÃO FUTURA. Nenhum existe.
#: Acrescentar qualquer um ao catálogo quebra `test_nomes_da_visao_nao_sao_
#: implementacao` de propósito: o caminho para tirar um nome daqui é uma
#: decisão assinada, não um commit que também edita esta lista sem dizer.
NOMES_DA_VISAO = (
    "observe.api", "observe.database", "observe.llm", "observe.queue",
    "intercept.network", "intercept.api",
    "act.api", "act.database",
    "browser.click", "browser.fill", "browser.evaluate",
    "browser.navigate", "browser.screenshot", "browser.network",
    "browser.console", "browser.reload",
)


def assinatura_em_branco() -> int:
    if not DECISAO.exists():
        pytest.skip("DECISAO_ATUACAO.md ausente neste ambiente")
    return len(_EM_BRANCO.findall(DECISAO.read_text(encoding="utf-8")))


# ── a trava que faltava ─────────────────────────────────────────────────────

def test_sem_assinatura_nenhuma_capacidade_acima_de_L0_e_implementada():
    """
    A regra que estava só em comentário.

    Se a assinatura de `DECISAO_ATUACAO.md` ainda tem linha em branco, então
    nenhuma capacidade L1/L2 pode estar `implementada=True`. Virar esse
    booleano sem assinar passaria por todos os outros guards — este é o único
    lugar onde isso falha.
    """
    if assinatura_em_branco() == 0:
        pytest.skip("DECISAO_ATUACAO.md assinada — esta trava sai de cena")
    acima = [c.nome for c in CATALOGO.values()
             if c.nivel > Nivel.OBSERVAR and c.implementada]
    assert acima == [], (
        f"capacidades acima de L0 marcadas como implementadas sem assinatura: "
        f"{acima}. Ver docs/agent_runtime/DECISAO_ATUACAO.md — "
        f"{assinatura_em_branco()} linhas de assinatura ainda em branco.")


def test_toda_capacidade_implementada_hoje_e_L0():
    """
    Estado declarado em 05/09/2026. Se alguem implementar algo acima de L0,
    este teste falha junto com o de cima — dois lugares, para que a mudanca
    nao passe por descuido em nenhum dos dois.
    """
    implementadas = {c.nome: int(c.nivel)
                     for c in CATALOGO.values() if c.implementada}
    assert all(n == 0 for n in implementadas.values()), implementadas


def test_L1_e_L2_estao_declaradas_e_recusadas():
    """
    Declaradas de propósito: o cliente precisa saber que a capacidade EXISTE e
    está recusada, senão pede de novo achando que errou o nome.
    """
    l1 = [c for c in CATALOGO.values() if c.nivel is Nivel.ALTERAR]
    l2 = [c for c in CATALOGO.values() if c.nivel is Nivel.PRIVILEGIADO]
    assert l1 and l2, "o catalogo perdeu as capacidades declaradas"
    assert all(not c.implementada for c in l1 + l2)
    # e nenhuma delas é reversível — é por isso que a decisão existe
    assert all(not c.reversivel for c in l1 + l2)


# ── o documento de visão não vira lista de tarefas ──────────────────────────

def test_nomes_da_visao_nao_sao_implementacao():
    """
    `VISAO_ATIVOS_E_ROADMAP.md` registra direção. O risco de um documento de
    direção é virar lista de tarefas sem passar pelo fluxo de governança.

    Nenhum nome citado lá como futuro existe no catálogo. Acrescentar um exige
    quebrar este teste — e quebrar um teste é visível de um jeito que editar um
    documento não é.
    """
    vazaram = [n for n in NOMES_DA_VISAO if n in CATALOGO]
    assert vazaram == [], (
        f"nomes que a visao cita como FUTUROS entraram no catalogo: {vazaram}. "
        f"Se isso foi deliberado, o caminho e uma decisao assinada + atualizar "
        f"NOMES_DA_VISAO nesta lista, nao so o catalogo.")


def test_a_visao_declara_que_nao_e_criterio():
    """
    O documento tem de dizer, no proprio texto, que nada ali e PASS/FAIL,
    trabalho executado ou evidencia. Se alguem apagar essa declaracao, o
    documento passa a poder ser lido como backlog.
    """
    if not VISAO.exists():
        pytest.skip("VISAO_ATIVOS_E_ROADMAP.md ausente neste ambiente")
    # Normaliza espaco: o markdown quebra linha no meio da frase, e o teste
    # nao pode depender de onde a linha quebrou.
    t = " ".join(VISAO.read_text(encoding="utf-8").split())
    for marca in ("PASS/FAIL", "trabalho executado",
                  "evidência de capacidade implementada"):
        assert marca in t, f"a visao deixou de declarar que nao e {marca!r}"
    # os tres termos da distincao
    for termo in ("medido", "inferido", "planejado"):
        assert termo in t, f"a visao perdeu o termo {termo!r}"


def test_a_visao_declara_o_estado_real_ao_lado_da_direcao():
    """
    A secao de estado real existe para que a leitura da visao nao contamine a
    leitura do que esta pronto. Sem ela, os dois viram o mesmo texto.
    """
    if not VISAO.exists():
        pytest.skip("VISAO_ATIVOS_E_ROADMAP.md ausente neste ambiente")
    t = " ".join(VISAO.read_text(encoding="utf-8").split())
    assert "browser.inspect" in t and "NAO executada em Chrome real" in t
    assert "DECLARADA e RECUSADA" in t


# ── o provedor nao passa por cima do catalogo ───────────────────────────────

def test_provedores_so_declaram_capacidade_do_catalogo_e_implementada():
    """
    Um provedor que declare capacidade fora do catalogo criaria uma capacidade
    de fato, sem ficha, sem nivel e sem politica que a conheca.
    """
    from agent_runtime.provedores.browser import ChromeDebuggerProvider
    from agent_runtime.provedores.har import ProvedorHAR

    for classe, caps in (
            (ChromeDebuggerProvider, {"browser.inspect"}),
            (ProvedorHAR, {"observe.network", "observe.console", "analyze.json"})):
        for nome in caps:
            assert nome in CATALOGO, f"{classe.__name__} declara '{nome}', fora do catalogo"
            c = CATALOGO[nome]
            assert c.implementada, f"{classe.__name__} declara '{nome}', nao implementada"
            assert c.nivel is Nivel.OBSERVAR, (
                f"{classe.__name__} declara '{nome}', que e L{int(c.nivel)}")
