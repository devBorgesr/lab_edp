"""
juiz_llm.py — o caminho B do REL-001 (§7).

O QUE ESTE ARQUIVO NAO DECIDE

O rubric ja esta congelado no `§4` do pre-registro. Este modulo o **le de la** e
monta o prompt — nao reescreve. Copia manual do rubric divergiria em silencio do
documento que governa o experimento, e foi exatamente esse o motivo de o exp019
ler o SYSTEM_TEMPLATE do fonte em vez de transcrever.

O QUE FICA PARA O PESQUISADOR

O `§7` exige congelar, antes da coleta: modelo, versao, system prompt,
temperatura, formato de saida, rubric. Deste conjunto, tres saem daqui
automaticamente (system prompt, formato, rubric) e **tres sao escolha**:

    MODELO       — nao ha default. Escolher e registrar.
    VERSAO       — quando o provedor expuser.
    TEMPERATURA  — ver a nota abaixo.

`congela_config()` recusa montar sem eles. Nao ha valor de conveniencia: um
default silencioso viraria "a configuracao que estava la" em vez de "a
configuracao escolhida", e o §7 pede a segunda.

SOBRE TEMPERATURA

Zero e o que a maioria escolheria, e vale dizer o que isso compra e o que nao:
compra reprodutibilidade da rodada; NAO compra determinismo garantido (mesmo em
0 muitos provedores variam) nem torna o juiz mais correto. Se a escolha for
outra, tambem esta certo — o que nao pode e nao registrar.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

EXPERIMENTO = "REL-001"

# Campos que o §7 exige congelados e que este modulo NAO preenche.
CAMPOS_OBRIGATORIOS = ("modelo", "temperatura")


def extrai_rubric(preregistro: Path) -> dict:
    """
    Le o rubric do `§4` do pre-registro. Falha alto se a secao mudar de forma.

    Nao aceita rubric passado por parametro de proposito: o unico rubric valido
    e o que esta no documento congelado, e um parametro abriria a porta para
    rodar com outro sem que o §8 mudasse.
    """
    txt = preregistro.read_text(encoding="utf-8")
    m = re.search(r"^## §4\. Rubric congelado\s*\n(.*?)(?=^## §5\.)", txt, re.S | re.M)
    if not m:
        raise RuntimeError(
            f"§4 nao encontrado em {preregistro.name} com o formato esperado. "
            f"O rubric e lido do documento, nunca transcrito — se a secao mudou, "
            f"o parser precisa acompanhar em vez de o prompt divergir."
        )
    corpo = m.group(1).strip()

    pergunta = re.search(r'>\s*\*\*"(.+?)"\*\*', corpo)
    if not pergunta:
        raise RuntimeError("a pergunta unica do §4 nao foi localizada")

    return {
        "pergunta": pergunta.group(1),
        "corpo": corpo,
        "sha256": hashlib.sha256(corpo.encode("utf-8")).hexdigest(),
    }


def monta_system_prompt(rubric: dict) -> str:
    """
    O system prompt do juiz, derivado do rubric.

    Curto de proposito. O REL-001 mede se o procedimento de rotulacao concorda
    com um humano sob o MESMO rubric — instrucao extra que o humano nao recebe
    mediria outra coisa, e a concordancia ficaria inflada por um lado so.
    """
    return (
        "Voce julga relevancia de documento para query, e nada mais.\n\n"
        f"PERGUNTA UNICA: {rubric['pergunta']}\n\n"
        "RELEVANTE (1): contribui materialmente; contem informacao necessaria "
        "ou evidencia diretamente utilizavel para responder a query.\n"
        "NAO_RELEVANTE (0): pode ser do mesmo assunto, usar palavras parecidas "
        "ou ser topicalmente proximo, e ainda assim nao contribuir.\n\n"
        "Similaridade tematica NAO e relevancia. Documento sobre exatamente o "
        "mesmo assunto pode receber 0.\n"
        "Documento sem informacao suficiente para decidir recebe 0.\n\n"
        'Responda APENAS o JSON: {"relevant": true} ou {"relevant": false}. '
        "Sem explicacao, sem escala, sem 'parcialmente'."
    )


def monta_user_prompt(query: str, documento: str) -> str:
    """
    O par a julgar.

    NAO inclui posicao no ranking nem score: o §4 proibe decidir por eles, e a
    unica forma de garantir isso e nao os enviar.
    """
    return f"QUERY:\n{query}\n\nDOCUMENTO:\n{documento}"


def congela_config(preregistro: Path, modelo: str = "", temperatura=None,
                   versao: str = "") -> dict:
    """
    A configuracao congelada do §7. RECUSA sem modelo e sem temperatura.

    O sha256 do rubric entra no registro: se o §4 mudar depois, a config
    congelada deixa de bater e a divergencia aparece em vez de passar.
    """
    faltando = [c for c, v in (("modelo", modelo), ("temperatura", temperatura))
                if v is None or v == ""]
    if faltando:
        raise RuntimeError(
            f"§7 exige congelar {faltando} antes da coleta, e nao ha default. "
            f"Um default silencioso viraria 'a configuracao que estava la' em "
            f"vez de 'a configuracao escolhida'."
        )
    rubric = extrai_rubric(preregistro)
    sysp = monta_system_prompt(rubric)
    return {
        "experimento":       EXPERIMENTO,
        "modelo":            modelo,
        "versao":            versao or "nao exposta pelo provedor",
        "temperatura":       temperatura,
        "formato_saida":     '{"relevant": bool}',
        "system_prompt":     sysp,
        "sha256_system":     hashlib.sha256(sysp.encode("utf-8")).hexdigest(),
        "sha256_rubric_§4":  rubric["sha256"],
        "pergunta_unica":    rubric["pergunta"],
        "nao_diz": ("congelar a config nao valida o juiz. Mede-se a concordancia "
                    "dele com UM anotador, sob ESTE rubric (NORTE §4.14)."),
    }


# §11 das instrucoes de coleta: todo modo de falha e CONTADO, e nenhum vira 0.
MODOS_DE_FALHA = ("json_invalido", "campo_ausente", "valor_fora_do_dominio",
                  "timeout", "erro_api", "resposta_vazia")

# §11 do pre-registro: acima disto, para e registra invalidacao.
MAX_INCLASSIFICAVEIS = 0.10


def classifica_falha(texto: Optional[str], erro: Optional[str] = None) -> Optional[str]:
    """
    Qual modo de falha, ou None se a resposta e valida.

    Existe para que a taxa de falha do JUIZ nao se esconda dentro da taxa de
    irrelevancia. Converter erro em 0 faria um juiz que timeouta 30% das vezes
    parecer um juiz severo.
    """
    if erro:
        return "timeout" if "timeout" in erro.lower() else "erro_api"
    if not (texto or "").strip():
        return "resposta_vazia"
    m = re.search(r"\{.*?\}", texto, re.S)
    if not m:
        return "json_invalido"
    try:
        d = json.loads(m.group(0))
    except Exception:
        return "json_invalido"
    if "relevant" not in d:
        return "campo_ausente"
    if d["relevant"] not in (True, False):
        return "valor_fora_do_dominio"
    return None


def veredito_de_falhas(falhas: list[Optional[str]]) -> dict:
    """
    Aplica o piso do §11 sobre a rodada inteira.

    Acima de MAX_INCLASSIFICAVEIS, a rodada e INVALIDA — nao se descarta o par
    ruim e segue, porque descartar seletivamente muda a amostra depois do dado.
    """
    from collections import Counter
    n = len(falhas)
    ruins = [f for f in falhas if f]
    taxa = len(ruins) / n if n else 0.0
    return {
        "n":            n,
        "inclassificaveis": len(ruins),
        "taxa":         round(taxa, 4),
        "limite":       MAX_INCLASSIFICAVEIS,
        "por_modo":     dict(Counter(ruins)),
        "veredito": ("INVALIDA — taxa acima do limite do §11; registre a "
                     "invalidacao em vez de descartar os pares"
                     if taxa > MAX_INCLASSIFICAVEIS else "dentro do limite"),
    }


def parse_resposta(texto: str) -> Optional[int]:
    """
    Extrai 0/1 da resposta do juiz. Devolve None quando nao consegue.

    None NAO vira 0. Resposta ilegivel e par INVALIDO, e o §11 manda parar se
    mais de 10% forem inclassificaveis — converter para 0 esconderia a taxa de
    falha do juiz dentro da taxa de irrelevancia.
    """
    try:
        d = json.loads(re.search(r"\{.*?\}", texto or "", re.S).group(0))
        v = d.get("relevant")
        return 1 if v is True else 0 if v is False else None
    except Exception:
        return None
