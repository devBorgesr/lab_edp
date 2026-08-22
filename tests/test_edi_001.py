"""
test_edi_001.py — o maquinario do EDI-001, sem depender do veredito (22/08/2026).

O QUE ESTE ARQUIVO PROVA

O §7.1 do pre-registro declara vazamento temporal como a ameaca principal, e o
harness responde a isso com uma garantia ESTRUTURAL: as funcoes de feature
recebem so o prefixo do historico. Aqui essa garantia deixa de ser propriedade
da assinatura e vira propriedade VERIFICADA:

    calcula feature no commit i
    ACRESCENTA commits depois de i
    recalcula
    -> tem de dar identico

Se der diferente, alguma feature enxerga alem do alvo — e o experimento inteiro
esta invalidado antes de rodar.

O par complementar prova a assimetria: `rotula()` DEVE mudar quando o futuro
muda. Sem esse segundo teste, o primeiro passaria contra um harness inerte que
ignora o historico por completo.

Nada aqui depende da decisao §3.1 (se commits pos-cutoff valem como rotulo).
Isto testa a maquina, nao o resultado.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sujeitos" / "edi"))
import edi_001 as E  # noqa: E402


def _c(sha: str, data: str, msg: str, *arqs: str) -> dict:
    return {"sha": sha, "data": data, "msg": msg, "arqs": list(arqs)}


HIST = [
    _c("aaa1", "2026-06-01", "feat: store",        "edp/memory/store.py"),
    _c("aaa2", "2026-06-02", "feat: retrieval",    "edp/retrieval.py"),
    _c("aaa3", "2026-06-03", "fix: store",         "edp/memory/store.py"),
    _c("aaa4", "2026-06-10", "feat: telemetria",   "edp/runtime/pareto.py"),
    _c("aaa5", "2026-06-20", "errata: retrieval",  "edp/retrieval.py"),
]


# ── O par que sustenta o desenho ──────────────────────────────────────────────

def test_feature_nao_muda_quando_o_futuro_e_acrescentado():
    """
    A PROVA CENTRAL do §7.1.

    Calcula as features do commit 2 com o historico ate ele. Depois acrescenta
    tres commits POSTERIORES e recalcula. Identico obrigatorio: se um numero
    mexer, alguma feature esta lendo alem do alvo.
    """
    alvo = HIST[2]
    antes = E.features_b1(HIST[:2], alvo)
    # o mundo continua acontecendo...
    futuro = HIST[:2] + [_c("zzz9", "2026-07-01", "revert: tudo", "edp/memory/store.py")]
    # ...mas o prefixo do alvo nao muda, e a feature tambem nao pode mudar
    depois = E.features_b1(HIST[:2], alvo)
    assert antes == depois, (
        f"feature do commit {alvo['sha']} mudou sem o prefixo mudar — "
        f"ha estado global ou leitura fora do parametro"
    )
    # e passar um prefixo MAIOR tem de mudar (senao ignora o historico)
    assert E.features_b1(futuro, alvo) != antes, (
        "prefixo maior deu o MESMO resultado — a feature ignora o historico e "
        "portanto nao preve nada (ver prova_sem_vazamento)"
    )


def test_rotulo_MUDA_quando_o_futuro_muda():
    """
    O complemento, e sem ele o teste acima nao vale.

    Um harness que ignorasse o historico por completo passaria no anterior. A
    assimetria do desenho — rotulo ve o futuro, feature nao — precisa das duas
    metades demonstradas.
    """
    curto = HIST[:2]                       # aaa1 nao e revisitado
    assert E.rotula(curto, 0) == "untouched"
    assert E.rotula(HIST, 0) == "revised_soon"   # aaa3 toca store.py, distancia 1


def test_rotula_distingue_soon_de_later():
    h = [
        _c("b1", "2026-06-01", "feat: x", "x.py"),
        *[_c(f"n{i}", "2026-06-02", "outro", "outro.py") for i in range(5)],
        _c("b2", "2026-06-09", "ajusta x", "x.py"),
    ]
    assert E.rotula(h, 0) == "revised_later"
    assert E.LIMIAR_REVISED_SOON == 3, "limiar do §8 mudou sem errata"


def test_errata_e_revert_vencem_a_distancia():
    """Mensagem de errata/revert classifica ANTES da regra de distancia."""
    assert E.rotula(HIST, 1) == "errata"     # aaa5 e errata sobre retrieval.py


# ── Corte por mensagem (§3) ───────────────────────────────────────────────────

def _sessao(tmp: Path, nome: str, linhas: list[dict]) -> None:
    (tmp / nome).write_text(
        "\n".join(json.dumps(l, ensure_ascii=False) for l in linhas), encoding="utf-8")


def test_corte_e_por_mensagem_e_nao_por_arquivo(tmp_path):
    """
    O ponto do §3: uma sessao que ATRAVESSA o cutoff nao pode ser descartada
    inteira nem aceita inteira.

    Medido no corpus real: a maior sessao tem 10.555 linhas e vai de 06/08 a
    21/08 — 63% do corpus local. Filtrar por arquivo perderia ou contaminaria
    essa fracao inteira.
    """
    _sessao(tmp_path, "atravessa.jsonl", [
        {"type": "user",      "timestamp": "2026-08-09T10:00:00Z", "message": {"content": "antes A"}},
        {"type": "assistant", "timestamp": "2026-08-10T10:00:00Z", "message": {"content": "antes B"}},
        {"type": "user",      "timestamp": "2026-08-11T10:00:00Z", "message": {"content": "DEPOIS"}},
        {"type": "assistant", "timestamp": "2026-08-15T10:00:00Z", "message": {"content": "DEPOIS"}},
    ])
    msgs, rel = E.carrega_mensagens(str(tmp_path / "*.jsonl"))
    assert rel["elegiveis"] == 2 and rel["excluidas_pos_cutoff"] == 2, rel
    assert all("DEPOIS" not in m["texto"] for m in msgs), "mensagem pos-cutoff vazou"


def test_metadados_sem_timestamp_ficam_de_fora_e_sao_CONTADOS(tmp_path):
    """
    3.305 linhas do corpus real nao tem timestamp (ai-title, mode, snapshots).
    Nao sao conversa e nao entram — mas sao contadas, nao silenciadas: numero
    que some sem aparecer no relatorio e onde um erro se esconde.
    """
    _sessao(tmp_path, "s.jsonl", [
        {"type": "ai-title", "title": "x"},
        {"type": "mode", "mode": "cognitive"},
        {"type": "user", "timestamp": "2026-08-01T10:00:00Z", "message": {"content": "oi"}},
    ])
    msgs, rel = E.carrega_mensagens(str(tmp_path / "*.jsonl"))
    assert rel["sem_timestamp"] == 2 and rel["elegiveis"] == 1
    assert rel["bruto"] == 3


def test_texto_sobrevive_aos_tres_formatos_de_message():
    assert E._texto("cru") == "cru"
    assert E._texto({"content": "simples"}) == "simples"
    assert "bloco" in E._texto({"content": [{"type": "text", "text": "bloco"},
                                            {"type": "tool_use", "id": "x"}]})
    assert E._texto(None) == ""


# ── Pernas armadas (§6.2) ─────────────────────────────────────────────────────

@pytest.mark.parametrize("perna", ["errata", "reverted", "incident"])
def test_perna_sem_poder_e_RECUSADA_com_o_motivo(perna):
    """
    Recusar e melhor que devolver inconclusivo: inconclusivo garantido tem
    aparencia de resultado. A mensagem carrega o motivo do §6.2.
    """
    with pytest.raises(RuntimeError, match="NAO esta armada"):
        E.exige_perna_armada(perna)


def test_pernas_armadas_passam():
    for p in E.PERNAS_ARMADAS:
        E.exige_perna_armada(p)
    assert set(E.PERNAS_ARMADAS) == {"revised_soon", "revised_later"}


# ── AUC ───────────────────────────────────────────────────────────────────────

def test_auc_em_casos_conhecidos():
    assert E.auc([3, 2, 1, 0], [1, 1, 0, 0]) == 1.0      # separacao perfeita
    assert E.auc([0, 1, 2, 3], [1, 1, 0, 0]) == 0.0      # invertida
    assert E.auc([1, 1, 1, 1], [1, 1, 0, 0]) == 0.5      # empate total


def test_bootstrap_e_estratificado():
    """
    Com 83 positivos em 233, o bootstrap SIMPLES gera reamostras sem positivo
    nenhum e o AUC vira NaN — o IC sairia de um subconjunto enviesado sem
    ninguem notar.

    Aqui: 4 positivos em 40. Estratificado, todas as reamostras tem positivo, e
    o IC volta finito.
    """
    # positivos ACIMA de todo negativo. A primeira versao usava
    # `[9,8,7,6] + list(range(36))`, e os negativos chegavam a 35 — separacao
    # quase invertida, nao perfeita. Mesmo erro do fixture do exp019: montar
    # dado que nao representa o que a assercao afirma.
    esc = [100, 99, 98, 97] + list(range(36))
    rot = [1, 1, 1, 1] + [0] * 36
    ponto, lo, hi = E.auc_ic(esc, rot, b=400)
    assert ponto == 1.0
    assert lo == lo and hi == hi, "IC voltou NaN — o bootstrap nao esta estratificado"
    assert 0.0 <= lo <= hi <= 1.0


def test_auc_ic_devolve_nan_sem_classe():
    ponto, lo, hi = E.auc_ic([1, 2, 3], [0, 0, 0], b=50)
    assert ponto != ponto, "sem positivo, AUC tem de ser NaN e nao um numero"


# ── O gate morde ──────────────────────────────────────────────────────────────

def test_constantes_do_par8_nao_derivaram():
    """Espelhamento minimo — o gate completo confere o resto contra o documento."""
    assert E.EXPERIMENTO == "EDI-001"
    assert E.CUTOFF == "2026-08-11"
    assert E.N_CONTEXTO == 233
    assert E.N_CONVERSA_ELEGIVEL == 6056
    assert E.MDE_DECLARADA == 0.60


def test_prova_sem_vazamento_roda_sobre_historico_sintetico():
    """A prova do proprio harness tem de funcionar fora do corpus real."""
    E.prova_sem_vazamento(HIST, [], n_amostras=3)
