"""
O pipeline. Onde "nunca inventar metrica" deixa de ser convencao.

    INPUT -> snapshot -> validacao de entrada -> retriever -> validacao do
    ranking -> validacao dos estratos -> amostragem -> julgadores ->
    validacao estatistica -> RELATORIO

A propriedade central: uma etapa bloqueante que nao passa **interrompe a
execucao**. As etapas seguintes ficam PENDING e nunca rodam. Nao e que o
relatorio deixe de imprimir o numero — o numero nunca chega a ser calculado.

Foi o que faltou no REL-001: a coleta rodou 492 chamadas sobre pares que uma
verificacao de cardinalidade teria barrado antes da primeira.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from .checks import (estatistica as CS, estratos as CE,
                     procedencia as CP, ranking as CR)
from .custos import Contabilidade
from .estados import Estado, StatusAuditoria
from .redacao import Politica
from .manifest import Manifesto


@dataclass(frozen=True)
class Protocolo:
    """
    A regua, congelada. O pipeline nunca a ajusta para caber.

    UM PROTOCOLO E UMA REGUA ESPECIFICA, NAO UMA VERDADE UNIVERSAL.

    `min_distintos=50` e uma escolha do REL-001, nao uma propriedade de RAGs em
    geral. Quando um sistema nao a satisfaz, a unica afirmacao autorizada e
    "nao pode ser auditado SOB O PROTOCOLO REL-001 v1" — nunca "este RAG e
    impossivel de auditar". Por isso `nome` e `versao` acompanham todo
    BLOCKED, em relatorio e em manifesto.

    `tipo` separa o que pode e o que nao pode sustentar afirmacao cientifica.
    """
    nome:              str
    min_distintos:     int                  # documentos DISTINTOS no ranking
    estratos:          dict[str, int]       # {"topo":5,"cauda":3,"controle":2}
    janela_cauda:      tuple[int, int]      # (inicio, fim) 0-based
    top_k:             int
    min_unidades:      int = 30            # clusters p/ bootstrap, nao itens
    versao:            int = 1
    tipo:              str = "experimental"  # experimental | demonstrativo
    descricao:         str = ""

    def __post_init__(self):
        if self.tipo not in ("experimental", "demonstrativo"):
            raise ValueError(f"tipo de protocolo desconhecido: {self.tipo}")

    @property
    def identidade(self) -> str:
        """`REL-001 v1`. Duas versoes NUNCA sao a mesma regua."""
        return f"{self.nome} v{self.versao}"

    def to_dict(self) -> dict:
        return {"nome": self.nome, "versao": self.versao,
                "identidade": self.identidade, "tipo": self.tipo,
                "descricao": self.descricao, "top_k": self.top_k,
                "min_distintos": self.min_distintos,
                "estratos": dict(self.estratos),
                "janela_cauda": list(self.janela_cauda),
                "min_unidades": self.min_unidades}


class SistemaAuditado(Protocol):
    """O que o cliente entrega. Um store e uma forma de consultar."""
    snapshot_dir: Path
    def consulta(self, query: str, top_k: int) -> list[tuple[str, float]]: ...
    def texto(self, doc_id: str) -> str: ...
    def controle_para(self, query: dict) -> list[str]: ...


@dataclass
class Auditoria:
    protocolo: Protocolo
    sistema:   Any
    queries:   Sequence[dict]
    modo:      str = "AUDIT"                # AUDIT | DIAGNOSTIC
    politica:  Politica = field(default_factory=Politica)
    audit_id:  str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    manifesto: Manifesto = field(init=False)
    conta:     Contabilidade = field(default_factory=Contabilidade)

    ETAPAS = ("snapshot", "entrada", "retriever", "ranking", "estratos",
              "amostragem", "julgadores", "estatistica")

    def __post_init__(self):
        self.manifesto = Manifesto(self.audit_id, self.protocolo.nome, self.modo)
        self.manifesto.protocolo_spec = self.protocolo.to_dict()

    # ── execucao ────────────────────────────────────────────────────────────

    # Tudo que identifica a auditoria. Se um campo faltar na abertura, o
    # manifesto de um BLOCKED nasce incompleto — e um bloqueio sem identidade
    # nao e contestavel.
    IDENTIDADE = ("snapshot", "dataset", "protocolo_spec", "retriever",
                  "privacidade", "configuracao")

    def _abertura(self, m: Manifesto) -> None:
        """
        TODA a identidade e registrada ANTES da primeira etapa.

        Regra aprendida em 31/08: o hash do dataset ficava na etapa
        `amostragem` e SUMIA quando o pipeline bloqueava antes — o manifesto de
        uma auditoria bloqueada nao dizia sobre quais queries o bloqueio
        aconteceu. A regra virou geral: fato de ENTRADA nao depende de o
        pipeline chegar ate ele.

        A partir daqui, qualquer BLOCKED ja nasce com identidade completa.
        """
        import hashlib

        m.snapshot = {"dir": str(getattr(self.sistema, "snapshot_dir", "?"))}

        m.retriever = {
            "top_k":            self.protocolo.top_k,
            "origem":           type(self.sistema).__name__,
            "adaptador":        type(self.sistema).__name__,
            "versao_adaptador": getattr(self.sistema, "VERSAO", "?"),
        }
        if hasattr(self.sistema, "telemetria_do_ranking") and self.queries:
            try:
                m.retriever["telemetria"] = self.sistema.telemetria_do_ranking(
                    self.queries[0]["query"], self.protocolo.top_k)
            except Exception as e:
                m.retriever["telemetria_falhou"] = str(e)

        m.amostra = {"n_queries": len(self.queries)}

        # PONTO DE EXTENSAO (item 18): o dataset e entrada do protocolo, nao
        # responsabilidade do nucleo.
        #     Question Dataset -> Benchmark -> Protocol -> Audit
        # Trocar a fonte muda `sha256_queries` e fica visivel aqui.
        m.dataset = {
            "n_queries": len(self.queries),
            "sha256_queries": hashlib.sha256(
                "\n".join(sorted(q["query"] for q in self.queries)
                          ).encode("utf-8")).hexdigest(),
            "origem": getattr(self, "origem_do_dataset", "fornecido"),
            "nota": ("o conjunto de queries e entrada do protocolo; trocar a "
                     "fonte muda `sha256_queries` e fica visivel aqui"),
        }

        m.protocolo_spec = self.protocolo.to_dict()
        m.privacidade = self.politica.relatorio()
        # NAO repetir `audit_id` aqui: ele ja e campo de topo do manifesto, e
        # o mesmo identificador em dois lugares convida a divergir. Como efeito
        # colateral util, `configuracao` fica deterministica — duas execucoes
        # da mesma entrada produzem a mesma configuracao, e o teste de
        # reprodutibilidade consegue afirmar isso.
        m.configuracao = {
            "modo":              self.modo,
            "min_unidades":      self.protocolo.min_unidades,
            "exemplos_em_claro": self.politica.exemplos_em_claro,
        }

        faltando = [c for c in self.IDENTIDADE if not getattr(m, c, None)]
        if faltando:
            raise RuntimeError(
                f"abertura incompleta: {faltando}. Um BLOCKED com identidade "
                f"parcial nao e contestavel."
            )

    def roda(self) -> Manifesto:
        m = self.manifesto
        self._abertura(m)

        for etapa in self.ETAPAS:
            fn = getattr(self, f"_etapa_{etapa}")
            self.conta.inicia(etapa)
            fn(m)
            self.conta.encerra()
            self._fecha(m)
            if m.barreiras:
                # PARA AQUI. As etapas restantes nao rodam — e por isso que
                # nenhuma metrica pode existir.
                m.etapa(etapa, Estado.BLOCKED,
                        barrado_por=[c.nome for c in m.barreiras])
                for resto in self.ETAPAS[self.ETAPAS.index(etapa) + 1:]:
                    m.etapa(resto, Estado.PENDING,
                            motivo="nao executada: pipeline interrompido")
                return m
            m.etapa(etapa, Estado.PASS)
        return m

    def _fecha(self, m: Manifesto) -> None:
        """Medicoes, custo e privacidade — inclusive quando a auditoria para."""
        m.custos = self.conta.resumo()
        m.privacidade = self.politica.relatorio()
        if getattr(self, "_rank", None) and m.procedencia_ok and not m.medicoes:
            from . import medicoes as MD
            m.publica_medicoes(MD.calcula(
                self._rank, self.sistema.texto,
                m.snapshot.get("sha256_episodic", "")[:16],
                self.protocolo.top_k))

    # ── etapas ──────────────────────────────────────────────────────────────

    def _etapa_snapshot(self, m: Manifesto) -> None:
        d = Path(getattr(self.sistema, "snapshot_dir", "."))
        r = CP.snapshot_tem_hash(d)
        m.snapshot.update(r.evidencia)
        m.registra(r)

    def _etapa_entrada(self, m: Manifesto) -> None:
        art = getattr(self.sistema, "artefato", None)
        if art is not None:
            r = CP.artefato_e_auditavel(art, "insumo do cliente")
            m.registra(r)
            if r.estado is Estado.INVALID:
                m.invalida("insumo do cliente", r.motivo)
        if not self.queries:
            m.registra(CR.veio_do_retriever([]))

    def _etapa_retriever(self, m: Manifesto) -> None:
        """Consulta uma vez e guarda; as etapas seguintes leem daqui."""
        self._rank: dict[str, list[tuple[str, float]]] = {}
        for q in self.queries:
            self._rank[q["id"]] = self.sistema.consulta(
                q["query"], self.protocolo.top_k)

    def _etapa_ranking(self, m: Manifesto) -> None:
        piores_card, piores_proc = None, None
        for q in self.queries:
            rk = self._rank[q["id"]]
            p = CR.veio_do_retriever(rk)
            if p.barra:
                # PROCEDENCIA PRIMEIRO. `cardinalidade` desempacota (id, score);
                # rodar contra um ranking de formato desconhecido rebenta com
                # stack trace em vez de diagnostico — e um servico de auditoria
                # que estoura no insumo do cliente nao auditou nada.
                if piores_proc is None:
                    piores_proc = p
                continue
            c = CR.cardinalidade(rk, self.protocolo.min_distintos)
            if c.barra and (piores_card is None or
                            c.evidencia["ids_distintos"] <
                            piores_card.evidencia["ids_distintos"]):
                piores_card = c
        # A PROCEDENCIA E SEMPRE REGISTRADA, passando ou nao.
        #
        # Defeito 31/08: a versao anterior so registrava o PASS quando nenhum
        # outro check falhava. Com a cardinalidade barrando, a prova de que o
        # ranking e real nunca entrava no manifesto — e as medicoes
        # descritivas, que dependem so dela, desapareciam. A auditoria perdia
        # a entrega comercial justamente no caso em que ela mais importa.
        m.registra(piores_proc if piores_proc is not None
                   else CR.veio_do_retriever(self._rank[self.queries[0]["id"]]))
        if piores_card is not None:
            m.registra(self._agrega_cardinalidade(piores_card))
        if self.modo == "DIAGNOSTIC":
            for q in self.queries[:1]:
                m.registra(CR.duplicacao_medida(
                    self._rank[q["id"]],
                    {d: self.sistema.texto(d) for d, _ in self._rank[q["id"]]}))

    def _agrega_cardinalidade(self, pior):
        """Uma linha para as N queries: min/mediana/max e quantas reprovam."""
        import statistics as st
        d = [len({i for i, _ in self._rank[q["id"]]}) for q in self.queries
             if not CR.veio_do_retriever(self._rank[q["id"]]).barra]
        if not d:
            return pior
        reprovam = sum(1 for x in d if x < self.protocolo.min_distintos)
        pior.evidencia.update({
            "queries":            len(d),
            "distintos_min":      min(d),
            "distintos_mediana":  st.median(d),
            "distintos_max":      max(d),
            "queries_reprovadas": reprovam,
        })
        pior.motivo = (
            f"sob o protocolo {self.protocolo.identidade}: {reprovam} de "
            f"{len(d)} queries nao alcancam os {self.protocolo.min_distintos} "
            f"documentos distintos que ELE exige (min={min(d)}, "
            f"mediana={st.median(d)}, max={max(d)}). Os slots estao cheios; os "
            f"documentos, nao. Isto NAO diz que o sistema e inauditavel — diz "
            f"que esta regua nao se aplica a ele."
        )
        return pior

    def _etapa_estratos(self, m: Manifesto) -> None:
        ini, fim = self.protocolo.janela_cauda
        for q in self.queries:
            rk = self._rank[q["id"]]
            vistos, dist = set(), []
            for i, s in rk:
                if i not in vistos:
                    vistos.add(i); dist.append((i, s))
            ctrl = self.sistema.controle_para(q)
            m.registra(CE.controle_fora_do_ranking(ctrl, dist))
            pool = ([{"doc": d, "estrato": "topo"}
                     for d, _ in dist[:self.protocolo.estratos["topo"]]] +
                    [{"doc": d, "estrato": "cauda"}
                     for d, _ in dist[ini:fim][:self.protocolo.estratos["cauda"]]] +
                    [{"doc": d, "estrato": "controle"}
                     for d in ctrl[:self.protocolo.estratos["controle"]]])
            m.registra(CE.sem_sobreposicao(pool),
                       CE.tamanhos(pool, self.protocolo.estratos))
            if m.barreiras:
                return

    def _etapa_amostragem(self, m: Manifesto) -> None:
        """A procedencia do dataset ja foi registrada na abertura (`roda`)."""
        m.dataset["pool_por_query"] = sum(self.protocolo.estratos.values())

    def _etapa_julgadores(self, m: Manifesto) -> None:
        juiz = getattr(self.sistema, "juiz", None)
        if juiz is None:
            m.juiz = {"configurado": False,
                      "nota": "MVP-0: execucao de juiz fora de escopo"}
            return
        m.juiz = {"configurado": True, **getattr(self.sistema, "juiz_config", {})}

    def _etapa_estatistica(self, m: Manifesto) -> None:
        """
        Pre-condicoes ANTES do calculo. Uma metrica calculavel nem sempre e
        interpretavel, e o servico nao publica numero que so a prevalencia
        explica.
        """
        m.registra(CS.unidades_suficientes(
            len(self.queries), self.protocolo.min_unidades))
        rot = getattr(self.sistema, "rotulos_do_gate", None)
        if rot is not None:
            m.registra(CS.prevalencia_permite_acordo(rot, "gate"))
        if m.barreiras:
            return
        calc: Callable | None = getattr(self.sistema, "estatistica", None)
        if calc is None:
            return
        m.publica_resultado(calc())        # o portao do manifesto tranca de novo
