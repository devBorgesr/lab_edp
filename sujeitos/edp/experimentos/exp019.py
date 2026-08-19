"""
exp019.py — harness do Experimento 019.

PERGUNTA: as instrucoes compensatorias do SYSTEM_TEMPLATE (linhas 16-48, 1.877
dos 3.095 chars) previnem os comportamentos que declaram prevenir?

Pre-registro: docs/preregistro_experimento_019.md — as constantes abaixo sao
espelhadas la e conferidas por tests/test_preregistro_espelha_harness.py.

O QUE ESTE ARQUIVO **NAO** FAZ, DE PROPOSITO

Nao escreve as queries. O §4-bis proibe: quem escreve as queries leu as 60
linhas do template primeiro, e qualquer pergunta escrita depois disso e
calibrada — mesmo sem intencao — para casar com o que as regras proibem.
Construir a prova a partir do gabarito confirma H1 por construcao. As queries
sao AMOSTRADAS do log real, que nao sabe que as regras existem.

Nao julga qualidade de resposta. O E10 mediu essa classe (verificador como
critico autonomo) e a H1 foi refutada. Aqui so entra o contavel por regra fixa.

ANTI-MOCK (§7)

O template e lido do FONTE do edp_v5, nunca transcrito — copia manual diverge
em silencio do que producao usa. Quando o pacote `edp` esta importavel,
`confere_contra_import()` prova que o literal lido do arquivo e identico ao
atributo em memoria.

USO
    PYTHONPATH=/media/sf_edp_v5_main python sujeitos/edp/experimentos/exp019.py --dry-run
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

# ── Constantes congeladas (espelhadas no §8 do pre-registro) ──────────────────

EXPERIMENTO        = "019"
N_POR_CELULA       = 40
ALPHA              = 0.05
MIN_CHARS_VERBATIM = 20
LINHAS_ABLADAS     = (16, 48)     # 1-indexado, inclusivo nas duas pontas
SEED               = 20260818
TOP_K              = 5
MIN_SCORE          = 0.0

# Guarda de tamanho do §7. MEDIDO em 18/08/2026 contra o template real, nao
# escolhido: se o SYSTEM_TEMPLATE mudar, o corte deixa de bater e o harness
# PARA — em vez de ablar silenciosamente o bloco errado.
RECORTE            = "controle"   # §6-bis: o estrato alvo tem 3 pares, nao roda
MDE_DECLARADA      = 0.30         # efeito minimo detectavel com N=40, poder >=0.90

CHARS_BLOCO_ABLADO = 1877
CHARS_TEMPLATE     = 3095

# Listas congeladas ANTES de olhar o corpus (§4-bis). Nao crescem depois do dado.
MARCADORES_ALVO = (
    # pronome / referencia a turno
    "isso", "sua resposta", "o que voce disse", "qual a base", "tirou", "falou",
    # temporal / continuidade
    "ontem", "agora", "antes", "ultima vez", "lembra",
    # citacao de memoria
    "aquela", "voce falou de",
)

# De onde a pergunta do usuario e extraida (§4-ter). NAO e `user_input`: esse
# source_type nao existe no store.
FONTES_DE_PERGUNTA = ("llm_response", "camara_response")

FRASES_NEGACAO = (
    "nao tenho memoria",
    "nao tenho acesso a",
    "nao consigo lembrar",
    "nao tenho como saber",
    "sou um modelo",
)


# ── Leitura do template (anti-mock) ───────────────────────────────────────────

def caminho_do_kernel() -> Path:
    """
    Raiz do edp_v5. Falha alto em vez de adivinhar.

    Mesma guarda do exp_e10: se EDP_KERNEL estiver setado, ele manda; senao usa
    o PYTHONPATH. Rodar contra o kernel errado e o erro que invalidou tres
    medicoes em 18/08/2026, e ele nao da sintoma — so numero errado.
    """
    env = os.environ.get("EDP_KERNEL")
    if env:
        p = Path(env)
        if not (p / "edp" / "llm_adapter.py").exists():
            raise RuntimeError(f"EDP_KERNEL={env} nao contem edp/llm_adapter.py")
        return p
    for raiz in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if raiz and (Path(raiz) / "edp" / "llm_adapter.py").exists():
            return Path(raiz)
    raise RuntimeError(
        "edp_v5 nao localizado. Rode com o kernel no PYTHONPATH:\n"
        "    PYTHONPATH=/media/sf_edp_v5_main python sujeitos/edp/experimentos/exp019.py"
    )


def carrega_template(raiz: Optional[Path] = None) -> str:
    """SYSTEM_TEMPLATE lido do FONTE — nunca transcrito."""
    raiz = raiz or caminho_do_kernel()
    fonte = (raiz / "edp" / "llm_adapter.py").read_text(encoding="utf-8")
    m = re.search(r'SYSTEM_TEMPLATE\s*=\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', fonte, re.S)
    if not m:
        raise RuntimeError("SYSTEM_TEMPLATE nao encontrado como literal em llm_adapter.py")
    return m.group(1)


def confere_contra_import(template: str) -> bool:
    """
    Prova que o literal lido do arquivo e o mesmo objeto que producao usa.

    Devolve False (sem estourar) quando `edp` nao esta importavel — o gate de
    espelhamento importa este modulo sem o kernel no path.
    """
    try:
        from edp.llm_adapter import EDPRuntime  # type: ignore
    except Exception:
        return False
    return getattr(EDPRuntime, "SYSTEM_TEMPLATE", None) == template


# ── Ablacao (§3) ──────────────────────────────────────────────────────────────

def abla(template: str) -> str:
    """
    Remove as linhas 16-48 (blocos compensatorios), preservando o resto.

    A guarda de tamanho e o ponto: um template editado desloca as linhas, e sem
    ela o experimento ablaria o bloco errado sem sintoma nenhum — exatamente o
    modo de falha silenciosa que o §7 existe para impedir.
    """
    linhas = template.splitlines()
    ini, fim = LINHAS_ABLADAS
    bloco = "\n".join(linhas[ini - 1:fim])
    if len(bloco) != CHARS_BLOCO_ABLADO or len(template) != CHARS_TEMPLATE:
        raise RuntimeError(
            f"o SYSTEM_TEMPLATE mudou: template={len(template)} chars "
            f"(esperado {CHARS_TEMPLATE}), bloco {ini}-{fim}={len(bloco)} chars "
            f"(esperado {CHARS_BLOCO_ABLADO}). O corte nao bate mais — refaca o "
            f"pre-registro em vez de ablar o bloco errado."
        )
    return "\n".join(linhas[:ini - 1] + linhas[fim:])


# ── Estratificacao e amostragem (§4-bis) ──────────────────────────────────────

def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn")


def normaliza(texto: str) -> str:
    """strip + casefold + colapso de whitespace — mesma do _dedup_pass_exp017."""
    return re.sub(r"\s+", " ", (texto or "").strip().casefold())


def extrai_pergunta(entry: dict) -> Optional[str]:
    """
    A pergunta do usuario, extraida da linha `Q:` do texto do turno.

    CORRECAO 18/08 (§4-ter): a regra original filtrava
    `source_type == "user_input"` e devolvia ZERO — esse tipo nao existe neste
    store. As 137 entradas sao llm_response, session_summary,
    meta_conversation e camara_response, e a pergunta vive DENTRO do texto do
    turno. Eu supus a estrutura do corpus sem conferir.
    """
    if (entry or {}).get("source_type") not in FONTES_DE_PERGUNTA:
        return None
    m = re.match(r"\s*Q:\s*(.+?)(?:\n\s*A:|\Z)", entry.get("text") or "", re.S)
    return m.group(1).strip() if m else None


def classifica(texto: str) -> str:
    """
    `alvo` se casa qualquer marcador congelado; `controle` se nenhum.

    FRONTEIRA DE PALAVRA, nao substring. CORRECAO 18/08 (§4-ter): `antes`
    casava dentro de `importantes` e promovia query ao alvo indevidamente —
    terceira vez no mesmo dia que casamento frouxo morde (as outras:
    `prompt_eval_count` contendo `eval_count`, e o catalogo de codigo morto).

    A correcao torna o criterio MAIS ESTRITO e o estrato MENOR (4 -> 3), entao
    nao pode ter sido escolhida para salvar a viabilidade.
    """
    t = _sem_acento(texto)
    for m in MARCADORES_ALVO:
        if re.search(r"\b" + re.escape(m) + r"\b", t):
            return "alvo"
    return "controle"


def amostra(entries: Iterable[dict], n_por_celula: int = N_POR_CELULA,
            seed: int = SEED) -> dict:
    """
    Amostra estratificada do log real. Devolve {'alvo': [...], 'controle': [...]}.

    Deduplica por texto normalizado ANTES de estratificar: medido em 18/08 ha 14
    copias extras no store, e amostrar sem deduplicar daria peso extra a quem
    esta repetido — enviesando para o que ja domina.

    NAO completa estrato curto. Se faltar, falta, e o §4-bis manda reportar o N
    alcancado com o poder recalculado: a escassez E o achado.
    """
    import random
    vistos: set = set()
    estratos: dict = {"alvo": [], "controle": []}
    for e in entries:
        txt = extrai_pergunta(e)
        if not txt:
            continue
        k = normaliza(txt)
        if k in vistos:
            continue
        vistos.add(k)
        estratos[classifica(txt)].append({**e, "_pergunta": txt})

    rng = random.Random(seed)
    return {nome: rng.sample(itens, min(n_por_celula, len(itens)))
            for nome, itens in estratos.items()}


# ── Metricas (§5 — extrativas, nenhuma usa julgamento de modelo) ──────────────

def nega_memoria(resposta: str) -> bool:
    """Casa a lista congelada de frases de negacao, sem acento e sem caixa."""
    r = _sem_acento(resposta)
    return any(f in r for f in FRASES_NEGACAO)


def usa_turno_anterior(resposta: str, texto_turno_anterior: str,
                       min_chars: int = MIN_CHARS_VERBATIM) -> bool:
    """
    True se a resposta contem >= min_chars contiguos VERBATIM do turno anterior.

    Comparacao de substring, nao juizo de relevancia — e essa a diferenca que o
    E10 cobrou caro.
    """
    a, b = normaliza(resposta), normaliza(texto_turno_anterior)
    if len(b) < min_chars or not a:
        return False
    return any(b[i:i + min_chars] in a for i in range(len(b) - min_chars + 1))


# ── Inferencia (§6) ───────────────────────────────────────────────────────────

def wilson_diff(k1: int, n1: int, k2: int, n2: int, alpha: float = ALPHA,
                b: int = 20000, seed: int = SEED) -> tuple[float, float, float]:
    """
    IC bootstrap da diferenca de proporcoes (p2 - p1). Devolve (dif, lo, hi).

    Bootstrap em vez de formula fechada pelo mesmo motivo do arco E9: a
    cobertura e verificavel por simulacao, e formula fechada com n pequeno e
    proporcao perto de 0 mente sobre a cobertura.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    p1, p2 = k1 / n1, k2 / n2
    a = rng.binomial(n1, p1, b) / n1
    c = rng.binomial(n2, p2, b) / n2
    d = c - a
    lo, hi = np.percentile(d, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(p2 - p1), float(lo), float(hi)


def veredito(alvo: tuple[int, int, int, int],
             controle: tuple[int, int, int, int]) -> dict:
    """
    §6: H1 exige IC do ALVO excluindo zero na direcao positiva E o CONTROLE
    NAO excluindo zero. Se o controle mover junto, ha confundidor e o resultado
    e INVALIDO — nao ajustado.
    """
    d_a, lo_a, hi_a = wilson_diff(*alvo)
    d_c, lo_c, hi_c = wilson_diff(*controle)
    alvo_move     = lo_a > 0
    controle_move = (lo_c > 0) or (hi_c < 0)
    if controle_move:
        v = "INVALIDO (controle negativo moveu — confundidor)"
    elif alvo_move:
        v = "H1"
    else:
        v = "H0 (nao detectado com este poder — ver §6)"
    return {"veredito": v,
            "alvo":     {"dif": d_a, "ic": [lo_a, hi_a]},
            "controle": {"dif": d_c, "ic": [lo_c, hi_c]}}


# ── Execucao (§3, §7) ─────────────────────────────────────────────────────────

def monta_condicoes(raiz=None) -> dict:
    """As duas condicoes do §3, derivadas do MESMO literal."""
    t = carrega_template(raiz)
    return {"completo": t, "ablado": abla(t)}


def exige_caminho_vivo() -> None:
    """
    Guarda contra medir o caminho MORTO.

    `stream_chat` so usa `_build_enriched_context` (o caminho de producao)
    quando `EDP_USE_CTX_MGR=1`, que e o default. Com a var em 0 ele cai no
    fallback `.format(context=...)`, que monta o prompt de OUTRO jeito — e o
    experimento mediria uma estrutura que producao nao usa.

    Foi assim que o §1 deste pre-registro nasceu errado (ver §1-bis), e e a
    terceira vez em dois dias que "qual caminho roda" custa caro. Aqui vira
    excecao, nao comentario.
    """
    if os.environ.get("EDP_USE_CTX_MGR", "1") != "1":
        raise RuntimeError(
            "EDP_USE_CTX_MGR != 1 — stream_chat cairia no fallback .format(), "
            "que NAO e a montagem de producao. Ver §1-bis."
        )


def responde(runtime, pergunta: str, system: str) -> str:
    """
    Um turno pelo caminho VIVO, com o system prompt da condicao.

    `system or self.SYSTEM_TEMPLATE` (llm_adapter.py:1714) faz o argumento
    vencer — a montagem seguinte e byte-a-byte a de producao, so o texto do
    system muda. Nao ha reimplementacao de prompt aqui, de proposito.

    `stream_chat` NAO chama `_store_to_memory` (Divida #10, llm_adapter.py),
    entao rodar o experimento nao grava turnos no store. E a segunda camada de
    protecao; a primeira continua sendo o §7 (store clonado).
    """
    exige_caminho_vivo()
    return "".join(runtime.stream_chat(pergunta, system=system))


def par_com_antecessor(qs_ordenadas: list, alvo: str) -> Optional[str]:
    """
    O turno que PRECEDEU a query no log real, ou None.

    POR QUE ISTO EXISTE (achado de 19/08, ao escrever a execucao): a metrica
    `usa_turno_anterior` do §5 compara a resposta com o item marcado
    `[turno anterior]`. Num harness de query ISOLADA nao existe turno anterior
    — a metrica devolveria False sempre, sem sinal nenhum, e pareceria medir.

    Pior: o estrato `alvo` e feito de perguntas com pronome e referencia. Uma
    pergunta como "entao voce lembra !!" sem o turno que a precedeu nao e a
    mesma pergunta — e um fragmento sem referente.

    Entao cada item do dataset e um PAR (antecessor, alvo), reproduzido na
    ordem do log. Sem antecessor, o item nao entra.
    """
    try:
        i = qs_ordenadas.index(alvo)
    except ValueError:
        return None
    return qs_ordenadas[i - 1] if i > 0 else None


def executa(runtime, dataset: dict, qs_ordenadas: list) -> list:
    """
    Roda as duas condicoes sobre os mesmos pares, na mesma ordem (§7).

    Devolve registros CRUS. O veredito e calculado depois, por `veredito()`,
    de proposito: coleta e analise separadas evitam parar a coleta ao ver o
    numero aparecer.
    """
    import random
    cond = monta_condicoes()
    itens = [(estrato, e) for estrato in ("alvo", "controle") for e in dataset[estrato]]
    random.Random(SEED).shuffle(itens)     # mesma ordem para as duas condicoes

    saida = []
    for estrato, entry in itens:
        pergunta = entry.get("_pergunta") or extrai_pergunta(entry)
        if not pergunta:
            continue
        antecessor = par_com_antecessor(qs_ordenadas, pergunta)
        if antecessor is None:
            continue                       # sem referente: fora, nao remendado
        for nome, sysprompt in cond.items():
            _ = responde(runtime, antecessor, sysprompt)   # estabelece o turno anterior
            resp = responde(runtime, pergunta, sysprompt)
            saida.append({
                "estrato":            estrato,
                "condicao":           nome,
                "pergunta":           pergunta,
                "antecessor":         antecessor,
                "resposta":           resp,
                "nega_memoria":       nega_memoria(resp),
                "usa_turno_anterior": usa_turno_anterior(resp, antecessor),
                "n_chars_resposta":   len(resp),
            })
    return saida


# ── Entrada ───────────────────────────────────────────────────────────────────

def carrega_corpus(store: Path) -> tuple[list, list]:
    """(entries, perguntas_em_ordem_cronologica) de um store CLONADO."""
    import json
    ep = store / "sessions" / "default_cognitive" / "episodic.json"
    if not ep.exists():
        raise RuntimeError(f"episodic.json nao encontrado em {ep}")
    entries = json.loads(ep.read_text(encoding="utf-8"))
    qs, vistos = [], set()
    for e in sorted(entries, key=lambda x: (x or {}).get("timestamp") or 0):
        q = extrai_pergunta(e)
        if not q:
            continue
        k = normaliza(q)
        if k in vistos:
            continue
        vistos.add(k)
        qs.append(q)
    return entries, qs


def dispara_recorte_controle(runtime, store: Path, n: int = N_POR_CELULA) -> dict:
    """
    §6-bis: roda SO o estrato `controle`.

    O `alvo` tem 3 pares contra os 40 exigidos (§4-ter) e NAO e completado nem
    reduzido em silencio — fica de fora, declarado.
    """
    exige_caminho_vivo()
    entries, qs = carrega_corpus(store)
    todos = amostra(entries, n_por_celula=10**9)          # sem cortar ainda
    ctrl = [e for e in todos["controle"]
            if par_com_antecessor(qs, e["_pergunta"]) is not None][:n]
    registros = executa(runtime, {"alvo": [], "controle": ctrl}, qs)
    return {
        "experimento":  EXPERIMENTO,
        "recorte":      RECORTE,
        "n_pares":      len(ctrl),
        "n_alvo_disponivel": len(todos["alvo"]),
        "mde_declarada": MDE_DECLARADA,
        "registros":    registros,
    }


def analisa_recorte(res: dict) -> dict:
    """
    §6-bis: veredito do recorte, com a armadilha do E9b explicita.

    IC contendo zero NAO autoriza "sem efeito" — autoriza "nao detectado
    deslocamento maior que a MDE". A frase sai pronta daqui para nao ser
    reescrita com mais confianca do que o dado tem.
    """
    reg = res["registros"]
    def conta(c):
        sub = [r for r in reg if r["condicao"] == c]
        return sum(1 for r in sub if r["nega_memoria"]), len(sub)
    k1, n1 = conta("completo")
    k2, n2 = conta("ablado")
    if not (n1 and n2):
        return {"veredito": "SEM DADO", "n": (n1, n2)}
    d, lo, hi = wilson_diff(k1, n1, k2, n2)
    move = (lo > 0) or (hi < 0)
    return {
        "completo":  f"{k1}/{n1}",
        "ablado":    f"{k2}/{n2}",
        "diferenca": round(d, 4),
        "ic95":      [round(lo, 4), round(hi, 4)],
        "veredito": (
            "A ABLACAO MOVE O CONTROLE — desenho comprometido, a previsao do §4 errou"
            if move else
            f"nao detectado deslocamento maior que MDE={MDE_DECLARADA} "
            f"(NAO e 'sem efeito' — ver §6-bis)"
        ),
        "nao_diz": "nada sobre a H1: o estrato alvo nao rodou",
    }


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description=f"Experimento {EXPERIMENTO}")
    ap.add_argument("--dry-run", action="store_true",
                    help="so mostra template/ablacao/estratos, sem chamar modelo")
    ap.add_argument("--recorte-controle", metavar="STORE_CLONADO",
                    help="§6-bis: dispara so o estrato controle contra o store clonado")
    ap.add_argument("--modelo", default="claude-haiku-4-5")
    ap.add_argument("--saida", default="resultado_exp019_recorte.json")
    a = ap.parse_args(argv)

    t = carrega_template()
    ab = abla(t)
    print(json.dumps({
        "experimento":       EXPERIMENTO,
        "template_chars":    len(t),
        "ablado_chars":      len(ab),
        "removido_chars":    len(t) - len(ab),
        "confere_com_import": confere_contra_import(t),
    }, indent=2, ensure_ascii=False))

    if a.dry_run:
        print("\n--dry-run: nada foi chamado. O disparo real exige o §8-bis "
              "com o MODELO registrado antes.")
        return 0

    if a.recorte_controle:
        chave = os.environ.get("ANTHROPIC_API_KEY", "")
        if not chave:
            raise SystemExit("ANTHROPIC_API_KEY ausente no ambiente.")
        store = Path(a.recorte_controle)
        if "edp_data_todo" in str(store) and "clone" not in str(store).lower():
            raise SystemExit(
                f"{store} parece ser o store DE PRODUCAO. O §7 exige clone. "
                "Copie antes e aponte para a copia."
            )
        from edp.llm_adapter import EDPRuntime          # type: ignore
        rt = EDPRuntime()
        if not rt.connect_anthropic(api_key=chave, model=a.modelo):
            raise SystemExit("connect_anthropic falhou.")
        res = dispara_recorte_controle(rt, store)
        res["modelo"] = a.modelo
        res["analise"] = analisa_recorte(res)
        Path(a.saida).write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        print(json.dumps(res["analise"], ensure_ascii=False, indent=2))
        print(f"\nbruto em {a.saida} ({res['n_pares']} pares, "
              f"alvo disponivel={res['n_alvo_disponivel']})")
        return 0

    raise SystemExit(
        "disparo real ainda nao armado: registre o MODELO no §8-bis do "
        "pre-registro e o dataset amostrado, conforme §4-bis."
    )


if __name__ == "__main__":
    raise SystemExit(main())
