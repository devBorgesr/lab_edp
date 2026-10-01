"""
test_higiene_de_corpus.py — o que NUNCA pode ser versionado (21/08/2026).

POR QUE ESTE ARQUIVO EXISTE

O EDI-001 introduz uma classe de dado que os outros experimentos nao tinham:
**transcricao de conversa**. Medido em 21/08 no corpus local — 53 MB, 11
sessoes — ha zero chaves de API (a disciplina segurou) mas **121 mencoes a
nomes de arquivo de gabarito** restritos pelo `AVISO_INSTANCIA_LIMPA.md`.

E quando esse mecanismo virar `edp_engineering`, o corpus deixa de ser conversa
do pesquisador e passa a ser conversa de uma equipe. O custo de um vazamento
muda de categoria.

O QUE MUDA AQUI: A DIRECAO DO PADRAO

O `.gitignore` do lab bloqueia `.jsonl` **por nome** — `export_fase0.jsonl`,
`e10_pares.jsonl`, `e9*_amostras.jsonl`. Isso e allowlist por omissao: todo
arquivo novo depende de alguem lembrar de adiciona-lo, e esquecer nao da
sintoma nenhum ate ser tarde.

Este teste inverte: `.jsonl` e **negado por classe**, e o que fica precisa
estar nomeado na `PERMITIDOS` abaixo, com o motivo escrito. Manter passa a
custar uma linha; esquecer passa a custar vermelho.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _rastreados(padrao: str = "") -> list[str]:
    out = subprocess.run(["git", "-C", str(RAIZ), "ls-files"] + ([padrao] if padrao else []),
                         capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if l.strip()]


# ── A allowlist: o que pode ser .jsonl versionado, e POR QUE ──────────────────
#
# Cada entrada e uma decisao registrada, nao uma excecao tecnica. Acrescentar
# aqui deveria doer um pouco.
PERMITIDOS: dict[str, str] = {}


def test_jsonl_versionado_precisa_estar_na_allowlist():
    """
    `.jsonl` e negado por classe. O que sobrevive precisa de motivo escrito.

    Este e o teste que muda a direcao do padrao. Antes: esquecer de ignorar um
    arquivo novo passava em silencio. Agora: quebra o build com o nome do
    arquivo na mensagem.
    """
    achados = [Path(f).name for f in _rastreados("*.jsonl")]
    nao_declarados = [f for f in achados if f not in PERMITIDOS]
    assert not nao_declarados, (
        f".jsonl versionado sem estar na allowlist: {nao_declarados}\n\n"
        f"Transcricao de conversa NAO se versiona. Se este arquivo e um dataset "
        f"congelado de experimento, acrescente-o a PERMITIDOS em "
        f"{Path(__file__).name} COM O MOTIVO — a linha existe para doer um pouco."
    )


def test_a_allowlist_nao_apodrece():
    """
    Entrada na allowlist que nao corresponde a arquivo nenhum e lixo que
    autoriza sem proteger — e daqui a seis meses ninguem sabe se pode remover.
    """
    achados = {Path(f).name for f in _rastreados("*.jsonl")}
    fantasmas = [f for f in PERMITIDOS if f not in achados]
    assert not fantasmas, (
        f"PERMITIDOS lista arquivo que nao existe mais: {fantasmas} — remova a "
        f"entrada em vez de deixar autorizacao orfa"
    )


def test_nenhuma_chave_em_arquivo_rastreado():
    """
    Chave de API em repositorio publico e irreversivel: rotacionar e obrigatorio
    mesmo depois de remover, porque o objeto fica no histórico do git.

    Padroes deliberadamente amplos — falso positivo custa uma conversa, falso
    negativo custa uma chave.
    """
    padrao = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{30,}")
    ofensores = []
    for rel in _rastreados():
        p = RAIZ / rel
        if not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if padrao.search(txt):
            ofensores.append(rel)
    assert not ofensores, f"padrao de chave em arquivo rastreado: {ofensores}"


def test_nenhum_arquivo_de_gabarito_rastreado():
    """
    REGRA 1 do AVISO_INSTANCIA_LIMPA.md. Os tres resultados do Gap Score sao
    gabarito-adjacentes e ficam untracked por decisao, nao por acaso.
    """
    proibidos = ("resultado_e2_extracao.json", "resultado_honeypot_14q.json",
                 "resultado_precondicao_wiki.json")
    rastreados = {Path(f).name for f in _rastreados()}
    achados = [p for p in proibidos if p in rastreados]
    assert not achados, f"arquivo de gabarito versionado: {achados} (AVISO Regra 1)"


def test_o_gate_morde():
    """
    Prova que a checagem acusa, em vez de confiar que acusa.

    Sem isto, os testes acima passariam identicamente contra um `_rastreados()`
    que devolve lista vazia — e um gate que nao le nada passa sempre.
    """
    assert _rastreados(), "git ls-files devolveu vazio — a checagem nao le nada"
    # Zero JSONL rastreado e um estado valido e preferivel para o repositorio
    # publico. Datasets reais/conversacionais ficam fora do Git; experimentos
    # reproduziveis devem publicar hash/protocolo ou fixtures sinteticas.
