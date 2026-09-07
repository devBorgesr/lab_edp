"""
A configuracao do SUJEITO no manifesto.

O QUE ESTES TESTES PROTEGEM

O manifesto registrava `configuracao` — e ela e a do AUDITOR (modo,
min_unidades, exemplos_em_claro). A do sistema AUDITADO nao era registrada em
lugar nenhum.

Consequencia medida na auditoria 400f691a3fa6 (31/08/2026): ela reporta
`duplicacao_intra_query_por_id = 0,26` com IC, sobre dataset congelado por
sha256 — e NAO e possivel saber, de nenhum artefato dela, se
`EDP_RETRIEVE_DEDUP` estava ligada. Essa flag esta em
`edp.config.FORMAT_STATE_FLAGS` com o comentario "muda o conjunto recuperado",
e o default e "0".

Sem esta captura, a duplicacao medida e indistinguivel entre defeito do
retriever e flag desligada por default. Um comprador tecnico pergunta "medido
sob qual configuracao?" na primeira reuniao, e o relatorio nao responde.

O que falha se alguem desfizer isto:
  * manifesto volta a nao dizer sob qual config mediu -> `test_manifesto_sempre_*`
  * silencio vira indistinguivel de "nao havia config" -> `test_default_*`
  * adaptador quebrado derruba a auditoria inteira    -> `test_falha_ao_coletar_*`
  * a lista de flags passa a ser mantida em dois lugares -> `test_edp_nao_*`
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from auditor import Auditoria, Protocolo                       # noqa: E402
from auditor.fixtures import ClienteSintetico, queries_cliente  # noqa: E402

BASICO = Protocolo("BASICO", 10, {"topo": 5, "cauda": 3, "controle": 2},
                   (5, 10), 10, min_unidades=10)


def _roda(tmp, sistema=None):
    s = sistema or ClienteSintetico(tmp, taxa_duplicacao=0.0)
    s.estatistica = lambda: {"cobertura": 0.71}
    return Auditoria(BASICO, s, queries_cliente(60)).roda()


# ── o manifesto sempre responde "sob qual configuracao" ─────────────────────

def test_manifesto_sempre_carrega_configuracao_do_sujeito(tmp_path):
    """
    SEMPRE escrita, mesmo indisponivel. A ausencia da chave passa a significar
    "manifesto anterior a esta versao"; `disponivel: false` significa "o
    adaptador nao sabe reportar". Os dois casos precisam ser distinguiveis.
    """
    m = _roda(tmp_path)
    cfg = m.to_dict()["retriever"]["configuracao_sujeito"]
    assert "disponivel" in cfg, "manifesto sem configuracao do sujeito"
    assert isinstance(cfg["disponivel"], bool)


def test_default_do_contrato_diz_que_nao_sabe(tmp_path):
    """
    Um adaptador que nao implementa nao pode ficar em silencio — silencio e
    indistinguivel de "o sujeito nao tinha configuracao".
    """
    m = _roda(tmp_path)
    cfg = m.to_dict()["retriever"]["configuracao_sujeito"]
    assert cfg["disponivel"] is False
    assert cfg["motivo"], "recusa sem motivo nao e recusa honesta"
    assert "ClienteSintetico" in cfg["motivo"], (
        "o motivo tem de nomear QUAL adaptador nao reporta")


def test_falha_ao_coletar_nao_derruba_a_auditoria(tmp_path):
    """
    Coletar configuracao e instrumentacao, nao protocolo. Se quebrar, a
    auditoria continua e o manifesto registra a quebra — o contrario faria uma
    melhoria de registro virar ponto unico de falha.
    """
    s = ClienteSintetico(tmp_path, taxa_duplicacao=0.0)
    s.estatistica = lambda: {"cobertura": 0.71}

    def explode():
        raise RuntimeError("adaptador quebrado de proposito")
    s.configuracao_do_sujeito = explode

    m = _roda(tmp_path, sistema=s)
    cfg = m.to_dict()["retriever"]["configuracao_sujeito"]
    assert cfg["disponivel"] is False
    assert "quebrado de proposito" in cfg["motivo"]


# ── o adaptador do EDP ──────────────────────────────────────────────────────

def test_edp_nao_mantem_lista_propria_de_flags():
    """
    A lista canonica e `edp.config.FORMAT_STATE_FLAGS`, travada por
    `tests/test_token_telemetry.py` no proprio EDP. O adaptador FOTOGRAFA essa
    lista; nao mantem uma copia. Flag nova aparece aqui sozinha, e a decisao
    de incluir foi tomada uma vez, no lugar certo.
    """
    fonte = (RAIZ / "auditor/adaptadores/edp.py").read_text(encoding="utf-8")
    assert "FORMAT_STATE_FLAGS" in fonte, "o adaptador nao le a lista canonica"
    # nenhuma flag literal pode estar escrita aqui: se estiver, ha duas fontes
    # de verdade e a segunda envelhece em silencio.
    for literal in ('"EDP_HYBRID_RETRIEVAL"', '"EDP_CTX_SLOTS"',
                    '"EDP_RETRIEVE_SHUFFLE"'):
        assert literal not in fonte, (
            f"{literal} hardcoded no adaptador — a lista tem UMA fonte")


def test_edp_reporta_identidade_do_modulo_nos_dois_ramos():
    """
    A identidade do sujeito e independente da lista de flags existir.

    Medido em 07/09/2026: a partir do lab, `import edp` resolve para a copia
    INSTALADA em site-packages, que e mais antiga que o repositorio — tem
    EDP_RETRIEVE_DEDUP e nao tem FORMAT_STATE_FLAGS. Sem registrar de onde o
    modulo veio, o manifesto afirma ter medido "o EDP" sem dizer qual.
    """
    pytest.importorskip("edp.config")
    from auditor.adaptadores.edp import EDPAuditavel

    # o metodo nao toca em self — le apenas o modulo edp
    cfg = EDPAuditavel.configuracao_do_sujeito(object())
    assert "identidade" in cfg, "identidade ausente"
    assert cfg["identidade"]["modulo"], "de qual arquivo veio o edp medido?"
    assert isinstance(cfg["disponivel"], bool)
    if cfg["disponivel"]:
        assert cfg["fonte"] == "edp.config.FORMAT_STATE_FLAGS"
        assert "EDP_RETRIEVE_DEDUP" in cfg["flags"], (
            "a flag que motivou esta captura precisa aparecer nela")
    else:
        assert "FORMAT_STATE_FLAGS" in cfg["motivo"]
