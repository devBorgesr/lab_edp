"""
O relatorio. A unica peca que o cliente le.

REGRA: um relatorio BLOQUEADO nao e um relatorio pela metade. Ele responde
quatro coisas que a maioria das ferramentas de avaliacao nao responde:

    por que nao pude medir
    com qual evidencia afirmo isso
    o que EXPLICITAMENTE nao foi concluido
    o que precisa ser decidido para destravar

"O que nao foi concluido" e obrigatorio. Sem essa secao o leitor completa a
lacuna sozinho, e completa para o lado otimista.
"""
from __future__ import annotations

from .estados import StatusAuditoria
from .manifest import Manifesto


def _num(v) -> str:
    if isinstance(v, float):
        return f"{v:.4g}".replace(".", ",")
    return str(v)


def _evidencia(ev: dict, ident: str = "  ") -> list[str]:
    return [f"{ident}{k} = {_num(v)}" for k, v in ev.items()
            if not isinstance(v, (dict, list))]


def markdown(m: Manifesto) -> str:
    d = m.to_dict()
    L: list[str] = []
    A = L.append

    A(f"# Auditoria `{m.audit_id}` — {m.protocolo}")
    A("")
    A(f"**Status: {d['status']}**")
    A("")

    if m.status is StatusAuditoria.BLOCKED:
        A("## Resumo executivo")
        A("")
        A("Esta auditoria **não produziu métricas**. Uma ou mais pré-condições "
          "de validade não foram satisfeitas, e o pipeline foi interrompido "
          "antes de qualquer cálculo.")
        A("")
        A("Isto não é uma falha do serviço: é o resultado que o serviço deve "
          "entregar quando o sistema auditado não sustenta o protocolo pedido.")
        A("")

        A("## Motivo")
        A("")
        for c in m.barreiras:
            A(f"**`{c.nome}` — {c.estado.value}**")
            A("")
            A(f"{c.motivo}")
            A("")
            if c.evidencia:
                A("```")
                L.extend(_evidencia(c.evidencia, ""))
                A("```")
                A("")
            A(f"*Este check detecta:* {c.detecta}")
            A("")

        A("## O que NÃO foi concluído")
        A("")
        A("Nenhuma métrica foi calculada. Especificamente:")
        A("")
        pend = [e for e in d["etapas"] if e["estado"] == "PENDING"]
        for e in pend:
            A(f"- etapa `{e['etapa']}` — não executada")
        if not pend:
            A("- (o bloqueio ocorreu na última etapa)")
        A("")
        A("Qualquer número que apareça em outro lugar sobre este sistema **não "
          "veio desta auditoria**.")
        A("")

        A("## Próximo passo")
        A("")
        A("Decisão do responsável, entre alterar o objeto auditado e alterar o "
          "protocolo. As duas mudam o que está sendo medido e nenhuma pode ser "
          "adotada em silêncio.")
        A("")
    else:
        A("## Resultado")
        A("")
        for k, v in (d.get("resultado") or {}).items():
            A(f"- **{k}**: {_num(v)}")
        A("")

    A("## Verificações")
    A("")
    A("| check | estado | barra? | detecta |")
    A("|---|---|---|---|")
    for c in d["checks"]:
        A(f"| `{c['nome']}` | {c['estado']} | "
          f"{'**sim**' if c['barra'] else 'não'} | {c['detecta']} |")
    A("")

    A("## Etapas")
    A("")
    A("| etapa | estado |")
    A("|---|---|")
    for e in d["etapas"]:
        A(f"| `{e['etapa']}` | {e['estado']} |")
    A("")

    A("## Procedência")
    A("")
    A("```")
    for k, v in (d["snapshot"] or {}).items():
        A(f"{k} = {v}")
    for k, v in (d["retriever"] or {}).items():
        A(f"retriever.{k} = {v}")
    A(f"manifesto.sha256 = {d['sha256_manifesto']}")
    A("```")
    A("")
    if d["invalidados"]:
        A("## Artefatos invalidados")
        A("")
        for i in d["invalidados"]:
            A(f"- `{i['artefato']}` — {i['motivo']}")
        A("")
    A("---")
    A("")
    A(f"Manifesto completo em `manifesto.json`. Modo: `{d['modo']}`. "
      f"O sha256 acima cobre o manifesto inteiro e permite contestar cada "
      f"número deste relatório.")
    return "\n".join(L)
