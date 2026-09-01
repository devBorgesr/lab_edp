"""
Propriedades do SERVICO, nao de um protocolo.

A distincao que estes testes protegem: `min_distintos=50` e uma escolha do
REL-001. Quando um sistema nao a satisfaz, a unica afirmacao autorizada e
"nao pode ser auditado SOB O REL-001 v1" — nunca "este RAG e inauditavel".
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from auditor import Auditoria, Protocolo, relatorio                  # noqa: E402
from auditor.cli import PROTOCOLOS                                   # noqa: E402
from auditor.estados import StatusAuditoria                          # noqa: E402
from auditor.fixtures import (ClienteSintetico, SistemaFalso,        # noqa: E402
                              queries_cliente)
from auditor.medicoes import Medicao                                 # noqa: E402
from auditor.redacao import Politica                                 # noqa: E402

BASICO = PROTOCOLOS["BASICO"]


def audita(tmp, taxa=0.0, n=24, prot=None):
    s = ClienteSintetico(tmp, taxa_duplicacao=taxa)
    s.estatistica = lambda: {"cobertura": 0.71}
    return Auditoria(prot or BASICO, s, queries_cliente(n)).roda()


# ── item 1 e 2: protocolo e uma regua, nao uma verdade ──────────────────────

def test_bloqueio_nomeia_a_regua_e_nao_condena_o_sistema(tmp_path):
    m = audita(tmp_path, taxa=0.6)
    md = relatorio.executivo(m)
    assert "BASICO v1" in md
    assert "não pôde ser executado sobre este sistema" in md
    assert "outra régua pode se aplicar" in md
    for frase in ("impossível de auditar", "inauditável.", "não pode ser auditado."):
        assert frase not in md, f"relatorio afirma demais: {frase!r}"


def test_motivo_do_check_cita_o_protocolo(tmp_path):
    m = audita(tmp_path, taxa=0.6)
    motivo = [c.motivo for c in m.barreiras][0]
    assert "BASICO v1" in motivo and "NAO diz que o sistema e inauditavel" in motivo


def test_versoes_diferentes_nunca_sao_a_mesma_regua():
    a = Protocolo("P", 50, {"topo": 5}, (19, 50), 50, versao=1)
    b = Protocolo("P", 40, {"topo": 5}, (19, 40), 50, versao=2)
    assert a.identidade != b.identidade == "P v2"


def test_protocolo_demonstrativo_se_declara(tmp_path):
    assert PROTOCOLOS["BASICO"].tipo == "demonstrativo"
    assert PROTOCOLOS["REL-001"].tipo == "experimental"
    md = relatorio.executivo(audita(tmp_path, taxa=0.6))
    assert "demonstrativa" in md and "não certifica" in md


def test_tipo_invalido_e_recusado():
    with pytest.raises(ValueError, match="tipo de protocolo"):
        Protocolo("X", 10, {"topo": 5}, (5, 10), 10, tipo="certificatorio")


# ── item 4: medicao sobrevive a bloqueio de PROTOCOLO, nao a ranking falso ──

def test_bloqueio_estatistico_nao_apaga_medicoes(tmp_path):
    """
    Um BLOCKED na ultima etapa nao pode apagar o que ja era valido nas
    anteriores. O ranking era real; a medicao continua de pe.
    """
    prot = Protocolo("P", 10, {"topo": 5, "cauda": 3, "controle": 2},
                     (5, 10), 10, min_unidades=999, versao=1)
    m = audita(tmp_path, prot=prot)
    assert m.status is StatusAuditoria.BLOCKED
    assert "estatistica.unidades_suficientes" in [c.nome for c in m.barreiras]
    assert len(m.medicoes) == 5, "bloqueio estatistico apagou medicao valida"


def test_ranking_invalido_nao_produz_nenhuma_medicao(tmp_path):
    m = Auditoria(BASICO, SistemaFalso(tmp_path, defeito="ordem_de_arquivo"),
                  queries_cliente(12)).roda()
    assert m.medicoes == []


def test_snapshot_invalido_nao_produz_medicao(tmp_path):
    m = Auditoria(BASICO, SistemaFalso(tmp_path, defeito="sem_snapshot"),
                  queries_cliente(12)).roda()
    assert m.medicoes == []


# ── itens 5 e 6: o nome carrega a definicao, e o numero carrega o referente ─

def test_jaccard_tem_nome_explicito(tmp_path):
    m = audita(tmp_path, taxa=0.6)
    nomes = [x.to_dict()["nome"] for x in m.medicoes]
    assert "jaccard_cross_query" in nomes
    assert not any("repeat" in n or "sobreposicao" in n for n in nomes)
    j = next(x for x in m.medicoes if x.nome == "jaccard_cross_query")
    assert "Jaccard mediano" in j.o_que_mede and "PARES" in j.o_que_mede


def test_medicao_sem_N_e_recusada():
    with pytest.raises(ValueError, match="sem N valido"):
        Medicao("x", 1.0, "mede algo", 0, "unidade", fonte="f")


def test_medicao_com_ic_sem_metodo_e_recusada():
    with pytest.raises(ValueError, match="metodo e seed"):
        Medicao("x", 1.0, "mede", 5, "u", ic95=(0.1, 0.2), fonte="f")


def test_medicao_sem_ic_precisa_declarar_por_que():
    with pytest.raises(ValueError, match="nao diz por que"):
        Medicao("x", 1.0, "mede", 5, "u", fonte="f")
    ok = Medicao("x", 1.0, "mede", 5, "u", fonte="f",
                 sem_ic_porque="estatistica de contagem unica")
    assert ok.to_dict()["sem_ic_porque"]


def test_ic_reamostra_a_mesma_estatistica_do_valor(tmp_path):
    """
    O valor e a mediana; o IC precisa ser da mediana. Um IC da media ao lado
    de um ponto que e mediana produz intervalo que nao contem o proprio ponto.
    """
    m = audita(tmp_path, taxa=0.6)
    for x in m.medicoes:
        d = x.to_dict()
        if d.get("ic95"):
            lo, hi = d["ic95"]
            assert lo <= round(d["valor"], 4) <= hi, \
                f"{d['nome']}: ponto {d['valor']} fora do IC {d['ic95']}"
            assert "MEDIANA" in d["metodo_ic"] and d["seed_ic"] is not None


# ── item 7: procedencia verificavel ─────────────────────────────────────────

def test_manifesto_registra_versoes_e_hashes(tmp_path):
    d = audita(tmp_path, taxa=0.6).to_dict()
    assert d["snapshot"]["sha256_episodic"] and d["snapshot"]["sha256_semantic"]
    assert d["protocolo_spec"]["versao"] == 1
    assert d["versao_servico"]
    assert d["retriever"]["adaptador"] and d["retriever"]["top_k"]
    t = d["retriever"]["telemetria"]
    assert t["origem_do_ranking"] and t["formato_valido"] is True


def test_caminho_sozinho_nao_e_identidade_do_corpus(tmp_path):
    """Mesmo caminho, conteudo diferente -> hash diferente."""
    s = ClienteSintetico(tmp_path / "c")
    h1 = hashlib.sha256((s.snapshot_dir / "episodic.json").read_bytes()).hexdigest()
    (s.snapshot_dir / "episodic.json").write_text(
        json.dumps([{"id": "z", "text": "outro"}]), encoding="utf-8")
    h2 = hashlib.sha256((s.snapshot_dir / "episodic.json").read_bytes()).hexdigest()
    assert h1 != h2


# ── item 8: segredo nao sobrevive, em nenhum modo ───────────────────────────

@pytest.mark.parametrize("segredo,rotulo", [
    ("sk-ant-api03-" + "A" * 40,                    "ANTHROPIC_KEY"),
    ("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NX0.abc", "JWT"),
    ("123.456.789-00",                               "CPF"),
    ("fulano.silva@empresa.com.br",                  "EMAIL"),
    ("-----BEGIN RSA PRIVATE KEY-----",              "PRIVATE_KEY"),
    ("ghp_" + "x" * 36,                              "GITHUB_TOKEN"),
    ("AKIAIOSFODNN7EXAMPLE",                         "AWS_KEY"),
])
@pytest.mark.parametrize("em_claro", [False, True])
def test_segredo_nao_sobrevive(segredo, rotulo, em_claro):
    p = Politica(exemplos_em_claro=em_claro)
    saida = p.documento(f"contexto {segredo} fim")
    assert segredo not in saida
    assert rotulo in p.relatorio()["segredos_removidos"]


# ── item 10: o manifesto e a fonte de verdade ───────────────────────────────

def test_markdown_nao_afirma_numero_ausente_do_manifesto(tmp_path):
    m = audita(tmp_path, taxa=0.6)
    d = m.to_dict()
    md = relatorio.executivo(m)
    for x in d["medicoes"]:
        assert x["nome"] in md, f"{x['nome']} no relatorio precisa estar no manifesto"
    assert d["sha256_manifesto"][:16] in md
    assert d["protocolo_identidade"] in md


# ── item 12: auditar nao altera o auditado ──────────────────────────────────

def test_duas_execucoes_nao_alteram_o_snapshot(tmp_path):
    sis = ClienteSintetico(tmp_path / "imut")
    epi = sis.snapshot_dir / "episodic.json"
    antes = hashlib.sha256(epi.read_bytes()).hexdigest()
    for _ in range(2):
        Auditoria(BASICO, sis, queries_cliente(24)).roda()
    assert hashlib.sha256(epi.read_bytes()).hexdigest() == antes


# ── item 13: reprodutibilidade ──────────────────────────────────────────────

def test_mesma_entrada_produz_mesmas_medicoes(tmp_path):
    sis = ClienteSintetico(tmp_path / "rep", taxa_duplicacao=0.6)
    a = Auditoria(BASICO, sis, queries_cliente(24)).roda()
    b = Auditoria(BASICO, sis, queries_cliente(24)).roda()
    assert ([x.to_dict() for x in a.medicoes] ==
            [x.to_dict() for x in b.medicoes])
    assert ([c.nome for c in a.checks] == [c.nome for c in b.checks])


def test_fontes_de_nao_determinismo_estao_declaradas(tmp_path):
    """
    Reprodutibilidade PERFEITA nao existe aqui, e fingir que existe seria pior
    que declarar. O manifesto carrega os campos que MUDAM entre execucoes.
    """
    sis = ClienteSintetico(tmp_path / "nd")
    a = Auditoria(BASICO, sis, queries_cliente(24)).roda().to_dict()
    b = Auditoria(BASICO, sis, queries_cliente(24)).roda().to_dict()
    difs = {k for k in a if a[k] != b[k]}
    # audit_id, criado_em, custos (tempo) e o hash que os cobre
    assert difs <= {"audit_id", "criado_em", "custos", "sha256_manifesto"}, \
        f"nao-determinismo nao declarado em: {difs}"


# ── item 15: instalacao limpa ───────────────────────────────────────────────

def test_auditor_nao_depende_de_caminho_pessoal():
    """
    Um servico nao pode carregar /home/<alguem> nem /media/<share> no CODIGO.
    E a diferenca entre "funciona no laboratorio" e "e um servico".

    Confere literais que o programa EXECUTA, nao docstring nem comentario: a
    primeira versao deste teste reprovou `procedencia.py` porque a docstring
    dele MENCIONA `edp_data_todo/` ao explicar por que a procedencia importa.
    Mencao em prosa nao e dependencia — a grandeza certa e o literal executavel
    (NORTE §4.15, e a ironia de o teste violar a propria regra nao passou).
    """
    import ast

    proibido = ("/home/", "/media/sf_", "C:" + chr(92), "edp_data_todo")
    for f in sorted((RAIZ / "auditor").rglob("*.py")):
        arvore = ast.parse(f.read_text(encoding="utf-8"))
        docstrings = set()
        for no in ast.walk(arvore):
            corpo = getattr(no, "body", None)
            if isinstance(corpo, list) and corpo:
                pri = corpo[0]
                if (isinstance(pri, ast.Expr) and isinstance(pri.value, ast.Constant)
                        and isinstance(pri.value.value, str)):
                    docstrings.add(id(pri.value))
        for no in ast.walk(arvore):
            if (isinstance(no, ast.Constant) and isinstance(no.value, str)
                    and id(no) not in docstrings):
                for pr in proibido:
                    assert pr not in no.value, (
                        f"{f.name}:{no.lineno} literal executavel com caminho "
                        f"pessoal: {pr}")


def test_auditor_importa_sem_o_edp_instalado():
    """
    O nucleo do servico nao pode depender de `edp`. So o adaptador depende, e
    ele e importado sob demanda.
    """
    cod = ("import sys; sys.modules['edp']=None; "
           "sys.path.insert(0, %r); "
           "import auditor, auditor.pipeline, auditor.medicoes, auditor.cli; "
           "print('ok')" % str(RAIZ))
    r = subprocess.run([sys.executable, "-c", cod], capture_output=True, text=True)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr[-400:]


def test_cli_roda_como_modulo(tmp_path):
    r = subprocess.run([sys.executable, "-m", "auditor", "--help"],
                       capture_output=True, text=True, cwd=str(RAIZ))
    assert r.returncode == 0 and "check" in r.stdout and "run" in r.stdout


# ── item 16: as duas demonstracoes, sem dado real ───────────────────────────

def test_demo_A_completa_e_demo_B_bloqueia(tmp_path):
    a = audita(tmp_path / "A", taxa=0.0)
    b = audita(tmp_path / "B", taxa=0.6)
    assert a.status is StatusAuditoria.COMPLETE and a.resultado
    assert b.status is StatusAuditoria.BLOCKED and len(b.medicoes) == 5
    # nenhuma das duas expoe dado real
    for m in (a, b):
        assert "indexacao postgres" not in json.dumps(m.to_dict(), ensure_ascii=False)


# ── escopo `diagnostico`: entrega sem afirmar demais ────────────────────────

def diag(tmp, taxa=0.6, n=24):
    from auditor.cli import PROTOCOLOS
    s = ClienteSintetico(tmp, taxa_duplicacao=taxa)
    return Auditoria(PROTOCOLOS["DIAGNOSTICO"], s, queries_cliente(n)).roda()


def test_diagnostico_completa_sem_estratos(tmp_path):
    """
    A regua comercial nao usa estrato nem controle negativo. Rodar essas
    verificacoes bloquearia em requisito que ela mesma nao usa, e entregaria o
    resultado dela debaixo de um BLOCKED.
    """
    m = diag(tmp_path)
    assert m.status is StatusAuditoria.COMPLETE
    assert not m.barreiras
    assert len(m.medicoes) == 5


def test_diagnostico_nao_finge_que_verificou_estrato(tmp_path):
    """
    A etapa pulada fica PENDING com motivo, nunca PASS. Dizer que passou uma
    verificacao que nao rodou seria a mentira que o servico existe para evitar.
    """
    m = diag(tmp_path)
    e = next(x for x in m.etapas if x["etapa"] == "estratos")
    assert e["estado"] == "PENDING" and "nao se aplica" in e["motivo"]
    assert not any(c.nome.startswith("estratos.") for c in m.checks)


def test_diagnostico_ainda_exige_ranking_real(tmp_path):
    """Escopo estreito nao afrouxa procedencia: e a unica coisa que ele exige."""
    from auditor.cli import PROTOCOLOS
    m = Auditoria(PROTOCOLOS["DIAGNOSTICO"],
                  SistemaFalso(tmp_path, defeito="ordem_de_arquivo"),
                  queries_cliente(24)).roda()
    assert m.status is StatusAuditoria.BLOCKED
    assert "ranking.veio_do_retriever" in [c.nome for c in m.barreiras]
    assert m.medicoes == []


def test_resultado_do_diagnostico_diz_o_que_nao_afirma(tmp_path):
    r = diag(tmp_path).resultado
    assert r["escopo"] == "diagnostico do material recuperado"
    assert set(r["medicoes"]) and "NAO_AFIRMA" in r


def test_relatorio_completo_nunca_diz_que_nada_ficou_de_fora(tmp_path):
    """
    O defeito corrigido: sob COMPLETE o relatorio imprimia "(nada — a auditoria
    completou)" na secao do que NAO foi medido. Para um diagnostico isso e
    falso, e convida a ler escopo estreito como auditoria plena.
    """
    md = relatorio.executivo(diag(tmp_path))
    assert "nada — a auditoria completou" not in md
    for exigido in ("qualidade das respostas", "Recall@K",
                    "nenhum julgamento", "certificação"):
        assert exigido in md, f"relatorio de diagnostico nao ressalva: {exigido}"


def test_diagnostico_nao_se_apresenta_como_certificacao(tmp_path):
    md = relatorio.executivo(diag(tmp_path)).lower()
    for proibido in ("certificamos", "aprovado", "selo", "validado por recall"):
        assert proibido not in md


def test_escopo_invalido_e_recusado():
    with pytest.raises(ValueError, match="escopo desconhecido"):
        Protocolo("X", 10, {"topo": 5}, (5, 10), 10, escopo="auditoria_plena")


# ── matriz de claims: o texto entregue nao afirma mais do que se mediu ──────

from auditor import claims                                          # noqa: E402

RESSALVAS = (" qualidade das respostas Recall@K nenhum julgamento certificação ")


@pytest.mark.parametrize("frase,esperado", [
    # permitidos — NIVEL 1, com referente
    ("37 documentos distintos por query (N=50)",                        []),
    ("26% dos slots foram ocupados por id repetido",                    []),
    ("Esta régua não certifica nada.",                                  []),
    ("documentos duplicados e sobrepostos foram observados",            []),
    # proibidos — consequencia nao medida
    ("26% do contexto é desperdiçado",              ["desperdicio"]),
    ("um quarto da janela vai em documento repetido", ["consumo por repeticao"]),
    ("a duplicação prejudica a resposta",           ["prejuizo"]),
    ("metade do contexto é inútil",                 ["inutilidade"]),
    # proibidos — NIVEL 3
    ("Certificamos a qualidade do seu retrieval",   ["certificacao"]),
    ("seu RAG está aprovado",                       ["aprovacao"]),
])
def test_matriz_de_claims(frase, esperado):
    achados = [v["termo"] for v in claims.verifica(frase + RESSALVAS)]
    assert achados == esperado, f"{frase!r} -> {achados}"


def test_a_frase_que_eu_escrevi_e_reprovada():
    """
    Regressao da violacao real: esta frase saiu em documento commitado, depois
    de eu ja ter escrito a regra que ela quebra.
    """
    minha = ("de 50 slots de contexto, chegam 37 documentos. "
             "Um quarto da janela vai em documento repetido.")
    assert claims.verifica(minha + RESSALVAS)


def test_ressalva_ausente_e_violacao(tmp_path):
    """Faltar a ressalva pesa igual a afirmar demais."""
    v = claims.verifica("37 documentos distintos por query.")
    assert {x["tipo"] for x in v} == {"ressalva_ausente"}
    assert len(v) == 4


def test_relatorios_de_diagnostico_passam_na_trava(tmp_path):
    m = diag(tmp_path)
    esc = m.protocolo_spec["escopo"]
    for txt in (relatorio.executivo(m), relatorio.markdown(m)):
        claims.exige_limpo(txt, esc, "relatorio")


def test_relatorio_tecnico_tambem_carrega_as_ressalvas(tmp_path):
    """
    Um documento mais detalhado que ressalva menos e pior: parece mais
    autoritativo justamente onde afirma menos.
    """
    md = relatorio.markdown(diag(tmp_path))
    assert "Limites desta régua" in md and "não há linha de base" in md


def test_relatorio_diz_que_nao_ha_linha_de_base(tmp_path):
    """
    NIVEL 2 exige saber o que e normal. Um sistema real medido nao e
    distribuicao de referencia, e o cliente precisa saber disso.
    """
    assert "linha de base" in relatorio.markdown(diag(tmp_path))


def test_servico_recusa_entregar_relatorio_com_claim_proibido(tmp_path, monkeypatch):
    """A barreira e antes da entrega, como a de segredo, e falha alto."""
    import auditor.servico as S
    monkeypatch.setattr(S.relatorio, "executivo",
                        lambda m: "26% do contexto é desperdiçado" + RESSALVAS)
    q = tmp_path / "q.json"
    q.write_text(json.dumps({"queries": queries_cliente(24)}), encoding="utf-8")
    with pytest.raises(claims.ClaimProibido, match="desperdicio"):
        S.executa({"snapshot": str(tmp_path / "c"), "queries": str(q),
                   "protocol": "DIAGNOSTICO", "adapter": "sintetico",
                   "options": {"taxa_duplicacao": 0.6}},
                  tmp_path / "svc", PROTOCOLOS)


# ── adaptador de referencia: o caminho do cliente ───────────────────────────

def test_referencia_resolve_o_caso_L2_que_reprovava(tmp_path):
    """
    Um indice L2 devolve distancia CRESCENTE e reprova em veio_do_retriever.
    A conversao monotona preserva a ordem e muda so a escala.
    """
    from auditor.adaptadores.referencia import AdaptadorDeReferencia, de_distancia
    from auditor.cli import PROTOCOLOS

    corpus = {f"d{i:03d}": f"texto {i}" for i in range(120)}
    l2 = lambda q, k: [(f"d{(abs(hash(q)) + i * 7) % 120:03d}", float(i) * 0.1)
                       for i in range(k)]
    sis = AdaptadorDeReferencia(corpus, l2, tmp_path / "ref",
                                converte_score=de_distancia,
                                nota_da_conversao="L2 -> 1/(1+d), monotona")
    qs = [{"id": f"q{i}", "query": f"p {i}", "dominio": ""} for i in range(24)]
    m = Auditoria(PROTOCOLOS["DIAGNOSTICO"], sis, qs).roda()
    assert m.status is StatusAuditoria.COMPLETE and len(m.medicoes) == 5


def test_conversao_de_score_sem_nota_e_recusada(tmp_path):
    """
    Conversao nao-monotona mudaria o ranking em silencio. Quem le o manifesto
    precisa poder conferir o que foi feito.
    """
    from auditor.adaptadores.referencia import AdaptadorDeReferencia, de_distancia
    with pytest.raises(ValueError, match="sem nota"):
        AdaptadorDeReferencia({"a": "x"}, lambda q, k: [], tmp_path / "r",
                              converte_score=de_distancia)


def test_exemplos_publicos_nao_tem_dado_real(tmp_path):
    from auditor.demo import gera
    st = gera(tmp_path / "ex")
    assert st == {"complete": "COMPLETE", "blocked": "BLOCKED"}
    for rot in ("complete", "blocked"):
        d = tmp_path / "ex" / rot
        for f in ("input.json", "manifesto.json", "relatorio.md",
                  "relatorio_tecnico.md", "COMO_LER.md"):
            assert (d / f).exists(), f"{rot}/{f} ausente"
