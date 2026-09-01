"""
O que o servico pode e nao pode AFIRMAR, verificado no texto gerado.

TRES NIVEIS DE AFIRMACAO

    NIVEL 1  OBSERVACAO   o que o retriever devolveu
    NIVEL 2  DIAGNOSTICO  anomalia medida no material recuperado
    NIVEL 3  QUALIDADE    efeito sobre relevancia ou resposta

O DIAGNOSTICO v1 emite NIVEL 1. Nunca NIVEL 3.

E NIVEL 2 TAMBEM NAO — e vale explicar por que, porque nao era o plano.

Chamar 26% de duplicacao de "anomalia" exige saber o que e normal. Nao
sabemos: ha UM sistema real medido (o EDP) e tres sinteticos que eu mesmo
escrevi. Sem distribuicao de referencia, "anomalo" e opiniao com aparencia de
medida — exatamente o erro que este arquivo existe para impedir. NIVEL 2 fica
disponivel quando houver baseline, e nao antes.

POR QUE ISTO E CODIGO E NAO CONVENCAO

Eu ja tinha escrito a regra em `NUMEROS_DE_DUPLICACAO.md` —

    "Nenhum e 'X% do contexto do RAG e inutil'. Todos medem repeticao de slot.
     Que a repeticao desperdice contexto e inferencia plausivel e NAO MEDIDA."

— e violei mesmo assim, duas vezes, no gerador de relatorio e no documento do
MVP. Saber a regra nao impediu de quebra-la. Por isso ela virou verificacao
sobre o TEXTO GERADO: a grandeza certa e o que o cliente le, nao o que o codigo
comenta (NORTE §4.15).
"""
from __future__ import annotations

import re
from typing import Any

NIVEL_OBSERVACAO, NIVEL_DIAGNOSTICO, NIVEL_QUALIDADE = 1, 2, 3

NIVEL_MAXIMO_POR_ESCOPO = {"diagnostico": NIVEL_OBSERVACAO,
                           "protocolo":   NIVEL_QUALIDADE}

# Consequencia causal nao medida. Barrado no texto entregue ao cliente.
CAUSAIS = [
    (re.compile(r"\bdesperdi[çc]", re.I),                    "desperdicio"),
    (re.compile(r"\bin[úu]til|\bin[úu]teis\b", re.I),        "inutilidade"),
    (re.compile(r"\bjogad[oa]s? fora\b", re.I),              "descarte"),
    (re.compile(r"\bcusto causado\b|\bcausa (?:um )?custo", re.I), "custo causado"),
    (re.compile(r"\bperda de qualidade\b|\bpiora a qualidade", re.I), "perda de qualidade"),
    (re.compile(r"\bqueda de (?:precis|qualidade|recall)", re.I), "queda"),
    (re.compile(r"\bprejudica\b|\bdegrada\b", re.I),         "prejuizo"),
    (re.compile(r"\bvai em\b.{0,30}\brepetid", re.I),        "consumo por repeticao"),
]

# Afirmacao de qualidade ou conformidade — NIVEL 3, fora do diagnostico.
QUALIDADE = [
    (re.compile(r"\bcertificam?o?s?\b|\bcertificad[oa]\b", re.I), "certificacao"),
    (re.compile(r"\bselo\b", re.I),                          "selo"),
    (re.compile(r"\baprovad[oa]\b", re.I),                   "aprovacao"),
    (re.compile(r"\bvalidado por recall\b", re.I),           "recall validado"),
    (re.compile(r"\brecall@\d+\s*[=:]\s*[\d.,]", re.I),      "valor de Recall@K"),
    (re.compile(r"\bqualidade (?:e|é|esta|está) (?:boa|ruim|alta|baixa)", re.I),
     "juizo de qualidade"),
]

# Ressalvas que um relatorio de diagnostico e OBRIGADO a conter. A ausencia de
# uma delas e tao defeito quanto a presenca de um termo proibido: o leitor
# completa a lacuna sozinho, e completa para o lado otimista.
RESSALVAS_OBRIGATORIAS = [
    ("qualidade das respostas", "nao mediu qualidade de resposta"),
    ("Recall@K",                "nao mediu Recall@K"),
    ("nenhum julgamento",       "nao houve julgamento de relevancia"),
    ("certificação",            "nao certifica"),
]


# Negacao imediatamente antes do termo. Mesma tecnica do gate de comentarios
# do edp_v5 (`test_comentario_nao_mente_sobre_default.py`): "nao certifica
# nada" CONTEM "certifica" e afirma o oposto. Sem isto o linter reprova a
# propria ressalva e forca a apaga-la — piorando o texto que deveria proteger.
_NEGADO = re.compile(r"(n[ãa]o|nunca|sem|jamais)\s+(?:\w+\s+){0,2}$", re.I)


def _esta_negado(texto: str, inicio: int) -> bool:
    return bool(_NEGADO.search(texto[max(0, inicio - 40):inicio]))


# Texto entre aspas e CITACAO, nao afirmacao do documento.
# Aspas podem atravessar quebra de linha — markdown quebra frase no meio da
# citacao. O limite de 200 caracteres impede que uma aspa orfa engula o
# documento inteiro e apague violacoes reais junto.
_CITACAO = re.compile(r'["“”][^"“”]{1,200}["“”]')


def _tira_citacoes(texto: str) -> str:
    """
    Remove trechos entre aspas antes de procurar violacao.

    TERCEIRA vez que citacao virou falso positivo — primeiro a ressalva em item
    de lista, depois a negacao inline, agora a frase que existe PARA PROIBIR a
    frase: `dizemos "...id repetido", e nunca "26% do contexto e desperdicado"`.
    O guard de negacao olha 40 caracteres atras, e o `nunca` estava a 50, do
    outro lado da citacao.

    Alargar a janela seria remendo. A regra que cobre os tres casos e mais
    simples: o documento afirma com as proprias palavras, e cita com aspas.

    LIMITE ACEITO CONSCIENTEMENTE: isto abre um falso negativo — um claim
    escrito entre aspas passa. E aceitavel porque nossos relatorios sao
    gerados por codigo e nunca poem afirmacao entre aspas, e porque o erro
    oposto ja se mostrou pior: um linter que reprova a ressalva forca a
    apaga-la, piorando exatamente o texto que deveria proteger.
    """
    return _CITACAO.sub(" [citacao] ", texto)


class ClaimProibido(RuntimeError):
    """Texto entregue afirma mais do que foi medido."""


# Abre um bloco de RESSALVA: o que vem depois enumera o que NAO se afirma.
_ABRE_RESSALVA = re.compile(
    r"errata|n[ãa]o permite afirmar|n[ãa]o foi medid|n[ãa]o afirma|"
    r"este relat[óo]rio n[ãa]o|sem Recall@K", re.I)


def _ignora_errata(texto: str) -> str:
    """
    Remove ERRATAS e BLOCOS DE RESSALVA antes de procurar violacao.

    Citar um termo para nega-lo nao e afirma-lo. A primeira versao disto
    filtrava LINHA a linha, e reprovou o proprio relatorio: a ressalva
    "conformidade, certificacao ou aprovacao de qualquer especie" e um item de
    lista sob o cabecalho "nao permite afirmar", e o item sozinho nao carrega a
    negacao.

    Um linter que obriga a apagar a ressalva para passar esta invertido — ele
    piora exatamente o texto que deveria proteger. Por isso o filtro segue o
    BLOCO: aberta a ressalva, os itens de lista e linhas de continuacao que a
    seguem pertencem a ela, ate a proxima linha que nao seja item nem vazia.
    """
    saida, em_ressalva = [], False
    for linha in texto.splitlines():
        se = linha.strip()
        if _ABRE_RESSALVA.search(se):
            em_ressalva = True
            continue
        if em_ressalva:
            if not se or se.startswith(("-", "*", ">")):
                continue
            em_ressalva = False
        saida.append(linha)
    return "\n".join(saida)


def verifica(texto: str, escopo: str = "diagnostico") -> list[dict[str, Any]]:
    """Violacoes no texto ENTREGUE. Lista vazia = pode sair."""
    alvo = _tira_citacoes(_ignora_errata(texto))
    faltas: list[dict[str, Any]] = []

    def trecho(m):
        return alvo[max(0, m.start() - 60):m.end() + 60]

    for padrao, rot in CAUSAIS:
        for m in padrao.finditer(alvo):
            if _esta_negado(alvo, m.start()):
                continue
            faltas.append({"tipo": "causal_nao_medido", "termo": rot,
                           "trecho": trecho(m),
                           "porque": ("afirma consequencia da medicao; efeito "
                                      "sobre custo, latencia ou qualidade nao "
                                      "foi medido")})

    if NIVEL_MAXIMO_POR_ESCOPO.get(escopo, 3) < NIVEL_QUALIDADE:
        for padrao, rot in QUALIDADE:
            for m in padrao.finditer(alvo):
                if _esta_negado(alvo, m.start()):
                    continue
                faltas.append({"tipo": "nivel_3_fora_de_escopo", "termo": rot,
                               "trecho": trecho(m),
                               "porque": f"escopo `{escopo}` nao emite NIVEL 3"})

    if escopo == "diagnostico":
        for marca, desc in RESSALVAS_OBRIGATORIAS:
            if marca not in texto:
                faltas.append({"tipo": "ressalva_ausente", "termo": desc,
                               "trecho": "", "porque":
                               "o leitor completa a lacuna para o lado otimista"})
    return faltas


def exige_limpo(texto: str, escopo: str, rotulo: str) -> None:
    """Barreira antes de entregar. Falha alto — o texto vai para o cliente."""
    f = verifica(texto, escopo)
    if f:
        linhas = "\n".join(f"  [{x['tipo']}] {x['termo']}: {x['porque']}"
                           for x in f)
        raise ClaimProibido(
            f"{rotulo} afirma mais do que foi medido:\n{linhas}\n"
            f"Nao entrego — o texto vai para o cliente."
        )
