"""
test_exp019_execucao.py — a camada de execucao do exp019, sem gastar chamada.

POR QUE ESTE ARQUIVO EXISTE

O arco E9 falhou tres vezes seguidas por constante escolhida sem medir a
consequencia, e o padrao comum era sempre o mesmo: descobrir o problema DEPOIS
de gastar a rodada. O exp019 custa 320 chamadas (~95 min). Validar o laco, a
ordem e o pareamento contra um runtime falso custa segundos.

O que NAO e testado aqui: se o modelo responde bem. Isso e o experimento.
O que E testado: se o harness pergunta o que diz perguntar, na ordem que diz,
com o system prompt que diz.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sujeitos" / "edp" / "experimentos"))
import exp019 as H  # noqa: E402


class _RuntimeEspiao:
    """Registra (pergunta, system) de cada chamada. Nao chama modelo nenhum."""
    def __init__(self, resposta="resposta sintetica"):
        self.resposta = resposta
        self.chamadas: list = []

    def stream_chat(self, user_message, system="", correlation_id=None):
        self.chamadas.append((user_message, system))
        yield self.resposta


QS = ["primeira pergunta", "segunda pergunta", "terceira sobre isso", "quarta pergunta"]


def _dataset():
    return {
        "alvo":     [{"_pergunta": "terceira sobre isso"}],
        "controle": [{"_pergunta": "quarta pergunta"}],
    }


# ── o par ─────────────────────────────────────────────────────────────────────

def test_o_antecessor_e_o_turno_anterior_do_log():
    assert H.par_com_antecessor(QS, "terceira sobre isso") == "segunda pergunta"
    assert H.par_com_antecessor(QS, "quarta pergunta") == "terceira sobre isso"


def test_a_primeira_pergunta_do_log_nao_tem_antecessor():
    """Por definicao. O item sai — nao ganha antecessor sintetico (§5-bis)."""
    assert H.par_com_antecessor(QS, "primeira pergunta") is None


def test_item_sem_antecessor_nao_entra(monkeypatch):
    monkeypatch.setattr(H, "monta_condicoes", lambda raiz=None: {"completo": "C", "ablado": "A"})
    rt = _RuntimeEspiao()
    saida = H.executa(rt, {"alvo": [{"_pergunta": "primeira pergunta"}], "controle": []}, QS)
    assert saida == [], (
        "item sem antecessor foi medido — o §5-bis manda descartar, nao remendar"
    )


# ── a execucao ────────────────────────────────────────────────────────────────

def test_cada_par_gera_duas_chamadas_por_condicao(monkeypatch):
    """
    antecessor -> estabelece o [turno anterior]; depois a query medida.

    Se so a query fosse enviada, `usa_turno_anterior` seria False sempre e
    pareceria estar medindo. Foi esse furo que originou o §5-bis.
    """
    monkeypatch.setattr(H, "monta_condicoes", lambda raiz=None: {"completo": "C", "ablado": "A"})
    rt = _RuntimeEspiao()
    saida = H.executa(rt, _dataset(), QS)

    assert len(saida) == 4, "2 itens x 2 condicoes"
    assert len(rt.chamadas) == 8, f"esperado 8 chamadas (2 por par x 4), veio {len(rt.chamadas)}"

    # em cada dupla consecutiva, o antecessor vem ANTES da query
    for i in range(0, 8, 2):
        antecessor, sys_a = rt.chamadas[i]
        query, sys_q = rt.chamadas[i + 1]
        assert QS.index(antecessor) == QS.index(query) - 1, (
            f"ordem quebrada: {antecessor!r} nao precede {query!r} no log"
        )
        assert sys_a == sys_q, "o par rodou com system prompts diferentes"


def test_as_duas_condicoes_veem_o_system_prompt_certo(monkeypatch):
    monkeypatch.setattr(H, "monta_condicoes", lambda raiz=None: {"completo": "C", "ablado": "A"})
    rt = _RuntimeEspiao()
    H.executa(rt, _dataset(), QS)
    usados = {s for _, s in rt.chamadas}
    assert usados == {"C", "A"}, f"system prompts usados: {usados}"


def test_a_ordem_e_a_mesma_nas_duas_condicoes(monkeypatch):
    """
    §7: ordem embaralhada com seed congelado, IGUAL para as duas condicoes.

    Ordem diferente entre condicoes introduz efeito de posicao/aquecimento como
    confundidor — e ele seria indistinguivel do efeito do tratamento.
    """
    monkeypatch.setattr(H, "monta_condicoes", lambda raiz=None: {"completo": "C", "ablado": "A"})
    rt = _RuntimeEspiao()
    saida = H.executa(rt, _dataset(), QS)
    seq = {}
    for r in saida:
        seq.setdefault(r["condicao"], []).append(r["pergunta"])
    assert seq["completo"] == seq["ablado"], f"ordens divergiram: {seq}"


def test_o_registro_e_cru_e_completo(monkeypatch):
    """Coleta e analise separadas: o veredito nao e calculado aqui."""
    monkeypatch.setattr(H, "monta_condicoes", lambda raiz=None: {"completo": "C", "ablado": "A"})
    saida = H.executa(_RuntimeEspiao(), _dataset(), QS)
    campos = {"estrato", "condicao", "pergunta", "antecessor", "resposta",
              "nega_memoria", "usa_turno_anterior", "n_chars_resposta"}
    assert campos <= set(saida[0]), f"faltando: {campos - set(saida[0])}"
    assert "veredito" not in saida[0], "o veredito nao pode sair junto da coleta"


# ── as guardas ────────────────────────────────────────────────────────────────

def test_a_guarda_do_caminho_vivo_morde(monkeypatch):
    """
    Com EDP_USE_CTX_MGR=0, stream_chat cai no fallback `.format(context=...)`,
    que NAO e a montagem de producao (§1-bis). Sem esta guarda o experimento
    rodaria verde medindo a estrutura errada.
    """
    monkeypatch.setenv("EDP_USE_CTX_MGR", "0")
    with pytest.raises(RuntimeError, match="EDP_USE_CTX_MGR"):
        H.exige_caminho_vivo()


def test_a_guarda_de_tamanho_do_template_morde():
    """§7: template alterado desloca as linhas — o corte tem de PARAR, nao ablar errado."""
    with pytest.raises(RuntimeError, match="SYSTEM_TEMPLATE mudou"):
        H.abla("linha1\nlinha2\nlinha3")


# ── as metricas ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("txt,esperado", [
    ("Nao tenho memoria entre sessoes.", True),
    ("Não tenho memória entre sessões.", True),      # acento nao muda o resultado
    ("NÃO TENHO ACESSO A HORÁRIOS",      True),      # caixa idem
    ("Tenho memoria sim, veja as tags.", False),
    ("",                                 False),
])
def test_nega_memoria(txt, esperado):
    assert H.nega_memoria(txt) is esperado


def test_usa_turno_anterior_exige_verbatim_longo():
    anterior = "o efeito Doppler e a mudanca na frequencia percebida"
    assert H.usa_turno_anterior("como eu disse, o efeito Doppler e a mudanca na frequencia percebida", anterior)
    assert not H.usa_turno_anterior("falamos de fisica ondulatoria ontem", anterior)


def test_usa_turno_anterior_nao_casa_por_coincidencia_curta():
    """MIN_CHARS_VERBATIM=20 existe para 'o' e 'a' nao contarem como citacao."""
    assert not H.usa_turno_anterior("sim", "sim, exatamente isso mesmo que voce disse")
