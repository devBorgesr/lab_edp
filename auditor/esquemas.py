"""
Formatos de entrada e saida, VERSIONADOS.

Por que versionar: um cliente que integrou contra `AuditResult v1` precisa
saber, sem ler codigo, se o que chegou hoje ainda e o mesmo contrato. Campo
novo e compativel; campo que muda de significado nao e, e isso exige bump.

Entrada invalida e recusada ANTES de qualquer trabalho — validar depois de
copiar o snapshot do cliente e trabalho jogado fora, e pior: e uma auditoria
que comeca sem saber o que esta auditando.
"""
from __future__ import annotations

from typing import Any

ENTRADA_VERSAO = "AuditInput v1"
RESULTADO_VERSAO = "AuditResult v1"

CAMPOS_ENTRADA = {
    "snapshot": str,     # caminho do corpus
    "queries":  str,     # caminho do dataset de perguntas
    "protocol": str,     # nome da regua
    "adapter":  str,     # tradutor do sistema do cliente
}
OPCIONAIS_ENTRADA = {"options": dict, "request_id": str, "schema": str}

# O que TODO AuditResult v1 carrega. A ausencia de qualquer um e defeito.
CAMPOS_RESULTADO = (
    "schema", "status", "audit_id", "protocolo", "protocolo_spec",
    "protocolo_identidade", "versao_servico", "snapshot", "dataset",
    "retriever", "configuracao", "checks", "medicoes", "resultado",
    "custos", "privacidade", "sha256_manifesto",
)


class EntradaInvalida(ValueError):
    """Recusa antes de qualquer trabalho."""


def valida_entrada(d: dict[str, Any], protocolos, adaptadores) -> dict[str, Any]:
    """
    `AuditInput v1`. Recusa alto e cedo.

    Nao aceita campo desconhecido: um `protocolo` escrito no lugar de
    `protocol` seria ignorado em silencio e a auditoria rodaria com a regua
    errada — e o cliente so descobriria lendo o manifesto.
    """
    if not isinstance(d, dict):
        raise EntradaInvalida(f"entrada precisa ser objeto, veio {type(d).__name__}")

    schema = d.get("schema", ENTRADA_VERSAO)
    if schema != ENTRADA_VERSAO:
        raise EntradaInvalida(
            f"schema '{schema}' desconhecido; este servico fala "
            f"'{ENTRADA_VERSAO}'. Versao de contrato nao se adivinha."
        )

    faltando = [c for c in CAMPOS_ENTRADA if c not in d]
    if faltando:
        raise EntradaInvalida(f"{ENTRADA_VERSAO}: faltam campos {faltando}")

    conhecidos = set(CAMPOS_ENTRADA) | set(OPCIONAIS_ENTRADA)
    estranhos = sorted(set(d) - conhecidos)
    if estranhos:
        raise EntradaInvalida(
            f"campos desconhecidos {estranhos}. Ignorar campo em silencio "
            f"faria a auditoria rodar com configuracao diferente da pedida."
        )

    for c, t in CAMPOS_ENTRADA.items():
        if not isinstance(d[c], t) or not str(d[c]).strip():
            raise EntradaInvalida(f"`{c}` precisa ser {t.__name__} nao-vazio")
    for c, t in OPCIONAIS_ENTRADA.items():
        if c in d and not isinstance(d[c], t):
            raise EntradaInvalida(f"`{c}` precisa ser {t.__name__}")

    if d["protocol"] not in protocolos:
        raise EntradaInvalida(
            f"protocolo '{d['protocol']}' desconhecido; ha "
            f"{sorted(protocolos)}")
    if d["adapter"] not in adaptadores:
        raise EntradaInvalida(
            f"adaptador '{d['adapter']}' desconhecido; ha {sorted(adaptadores)}")
    return {**d, "schema": ENTRADA_VERSAO}


def confere_resultado(d: dict[str, Any]) -> list[str]:
    """Campos de `AuditResult v1` ausentes. Vazio = contrato cumprido."""
    return [c for c in CAMPOS_RESULTADO if c not in d]
