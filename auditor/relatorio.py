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
Dois niveis (item 9):

    executivo(m)  -> REPORT_EXECUTIVE, quatro perguntas
    markdown(m)   -> REPORT_TECHNICAL, a evidencia inteira

O executivo NUNCA simplifica removendo o referente. Um numero sem N e sem
unidade nao entra, porque e assim que uma medicao vira alegacao.
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


def _medicoes(m: Manifesto, L: list) -> None:
    """
    A entrega que existe mesmo sob BLOCKED.

    Cada linha carrega o referente. Uma tabela de numeros sem "o que mede",
    N e snapshot e o formato em que uma medicao vira alegacao.
    """
    if not m.medicoes:
        return
    A = L.append
    A("## Medições")
    A("")
    A("Fatos observáveis sobre o material recuperado. **Não são métricas de "
      "qualidade de resposta** e não substituem o resultado do protocolo.")
    A("")
    A("| medição | valor | IC 95% | N | unidade |")
    A("|---|---|---|---|---|")
    for x in m.medicoes:
        d = x.to_dict()
        ic = (f"[{d['ic95'][0]:.4g}, {d['ic95'][1]:.4g}]".replace(".", ",")
              if d.get("ic95") and d["ic95"][0] == d["ic95"][0] else "—")
        A(f"| `{d['nome']}` | {_num(round(d['valor'], 4))} | {ic} | "
          f"{d['N']} | {d['unidade']} |")
    A("")
    for x in m.medicoes:
        d = x.to_dict()
        A(f"**`{d['nome']}`** — {d['o_que_mede']}")
        A("")
        A(f"*N = {d['N']} · k = {d.get('k', '—')} · snapshot `{d['snapshot']}` "
          f"· fonte: {d['fonte']}*")
        A("")


def executivo(m: Manifesto) -> str:
    """
    REPORT_EXECUTIVE. Quatro perguntas, nesta ordem.

    Nunca simplifica removendo o referente: um numero aqui aparece com N e
    unidade, ou nao aparece.
    """
    d = m.to_dict()
    L: list[str] = []
    A = L.append
    A(f"# Auditoria — {m.protocolo}")
    A("")
    A(f"`{m.audit_id}` · {d['criado_em']} · **{d['status']}**")
    A("")

    A("## O sistema foi auditável?")
    A("")
    if m.status is StatusAuditoria.BLOCKED:
        A("**Não sob este protocolo.** A execução foi interrompida antes de "
          "qualquer cálculo, por pré-condição de validade não satisfeita.")
    elif m.status is StatusAuditoria.READY:
        A("**Sim.** Todas as pré-condições foram satisfeitas. Nenhuma métrica "
          "de protocolo estava configurada para esta execução — o que segue "
          "são medições descritivas.")
    else:
        A("**Sim.** Todas as pré-condições de validade foram satisfeitas.")
    A("")

    A("## O que foi encontrado")
    A("")
    if m.medicoes:
        for x in m.medicoes:
            dd = x.to_dict()
            A(f"- **{dd['nome'].replace('_', ' ')}**: "
              f"{_num(round(dd['valor'], 4))} {dd['unidade']} "
              f"(N = {dd['N']})")
        A("")
    for c in m.barreiras:
        A(f"- {c.motivo}")
    if not m.medicoes and not m.barreiras:
        A("- (nada a relatar)")
    A("")

    A("## O que NÃO foi possível concluir")
    A("")
    if m.status is not StatusAuditoria.COMPLETE:
        A("Nenhuma métrica de protocolo foi calculada — sem Recall@K, sem "
          "índice de acordo, sem *ground truth*.")
        A("")
        pend = [e["etapa"] for e in d["etapas"] if e["estado"] == "PENDING"]
        if pend:
            A(f"Etapas não executadas: {', '.join(f'`{x}`' for x in pend)}.")
            A("")
        A("As medições acima descrevem o material recuperado. Elas **não** "
          "autorizam afirmação sobre a qualidade das respostas do sistema.")
    else:
        A("(nada — a auditoria completou)")
    A("")

    A("## Qual decisão precisa ser tomada")
    A("")
    if m.status is StatusAuditoria.BLOCKED:
        A("Entre **alterar o objeto auditado** e **alterar o protocolo**. As "
          "duas mudam o que está sendo medido; nenhuma pode ser adotada em "
          "silêncio, e a escolha não é do serviço.")
    else:
        A("Nenhuma pendente.")
    A("")
    A("---")
    A("")
    A(f"Evidência detalhada em `relatorio_tecnico.md`. Manifesto "
      f"`{d['sha256_manifesto'][:16]}…` em `manifesto.json`.")
    return "\n".join(L)


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

    _medicoes(m, L)

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
    if d.get("custos"):
        A("## Custo desta auditoria")
        A("")
        A("```")
        for k, v in d["custos"].items():
            if not isinstance(v, dict):
                A(f"{k} = {v}")
        A("```")
        A("")
    if d.get("privacidade"):
        A("## Privacidade")
        A("")
        A("```")
        for k, v in d["privacidade"].items():
            A(f"{k} = {v}")
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
