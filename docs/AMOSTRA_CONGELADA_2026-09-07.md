# Amostra congelada — diagnóstico de retrieval sob duas configurações

**07/09/2026.** Duas execuções do protocolo `DIAGNOSTICO v1` sobre o **mesmo
snapshot**, variando **uma** flag do sujeito.

## O que esta amostra é, e o que ela não é

**É** uma comparação descritiva, com intervalo de confiança, entre duas
configurações do mesmo sistema.

**NÃO é** um experimento. Não houve pré-registro, não há hipótese e não há
critério de decisão congelado antes do dado. Portanto **não sustenta** nenhuma
afirmação sobre uma configuração ser melhor que a outra — só sobre o que muda
entre elas.

Quem quiser afirmar "ligar a dedup melhora o retrieval" precisa de um critério
de qualidade, e isso é a Zona 2 da
[triagem de sintoma](../../sf_edp_v5_main/comercial/TRIAGEM_DE_SINTOMA.md):
exige rotulação de relevância, que não existe aqui.

---

## Identidade das duas execuções

```
sujeito ......... EDP, /media/sf_edp_v5_main/edp/__init__.py, versao 3.0.0
                  (o REPOSITORIO, nao a copia instalada em site-packages)
snapshot ........ ~/Desktop/edp_data_todo/edp_data/sessions/default_cognitive
                  sha256_episodic d64fcc74a0c7e9b0...
dataset ......... amostra_congelada.json, 50 queries
protocolo ....... DIAGNOSTICO v1
janela .......... top_k = 50

7642c0ad8597 .... EDP_RETRIEVE_DEDUP = False   (o default do kernel)
30c1462fd945 .... EDP_RETRIEVE_DEDUP = True

as outras nove flags de FORMAT_STATE_FLAGS ficaram iguais nas duas execucoes,
e estao gravadas nos dois manifestos.
```

Ambos os manifestos registram, além disso, a origem do snapshot, a identidade
do módulo medido e a procedência do carimbo de data — campos que não existiam
na auditoria `400f691a3fa6` e cuja ausência está declarada na errata dela.

---

## O resultado

| medição | dedup OFF | dedup ON | IC se sobrepõe? |
|---|---|---|---|
| `cardinalidade_do_ranking` | 37 — IC [37, 38] | 50 — IC [50, 50] | **não** |
| `duplicacao_intra_query_por_id` | 0,26 — IC [0,24; 0,26] | 0 — IC [0, 0] | **não** |
| `duplicacao_por_texto` | 0 — IC [0, 0] | 0 — IC [0, 0] | idêntico |
| `jaccard_cross_query` | 0,283 — IC [0,2759; 0,2903] | 0,3889 — IC [0,3699; 0,3889] | **não** |
| `razao_score_topo_cauda` | 1,814 — IC [1,75; 1,858] | 1,948 — IC [1,902; 2,001] | **não** |

N = 50 queries para todas, exceto `jaccard_cross_query`, com N = 1225 pares.

### O que é permitido dizer

> "Com a flag de dedup no default (desligada), 26% dos slots do top-k foram
> ocupados por documentos cujo ID já estava no ranking — IC [0,24; 0,26], 50
> queries, k=50. Com a flag ligada, 0%, IC [0, 0]. A janela passou a entregar
> 50 documentos distintos em vez de 37."

> "No mesmo movimento, a sobreposição entre pares de queries distintas subiu de
> 0,283 para 0,3889 — IC [0,3699; 0,3889], 1225 pares. Os intervalos não se
> sobrepõem."

### O que NÃO é permitido dizer

> ~~"Ligar a dedup melhora o retrieval."~~
> ~~"A dedup piora a diversidade entre queries."~~
> ~~"26% do orçamento de token estava indo para repetição."~~

As duas primeiras precisam de critério de qualidade, que esta amostra não tem.
A terceira é a frase proibida registrada em
`audit/PROCEDENCIA_DOGFOOD.md`: todas essas grandezas medem **repetição de
slot**, e converter fração de slot em fração de token exigiria comprimento
uniforme — que a família de chunking já mostrou não existir.

---

## A leitura honesta, e é ela que interessa comercialmente

Ligar uma flag eliminou completamente um comportamento medido e aumentou outro,
os dois com intervalos que não se sobrepõem.

**Qual dos dois estados é preferível, este diagnóstico não responde** — e não
responder é o resultado, não a limitação. Um instrumento que dissesse qual é
melhor sem critério de qualidade estaria inventando a parte que falta.

O que ele entrega é a forma do compromisso: *"eis o que sua configuração atual
custa em repetição de slot, eis o que a alternativa custa em sobreposição entre
consultas, e a escolha é sua"*.

## O que falta nesta amostra

```
familia de chunking .... nao existe no protocolo do lab, so no auditor
                         standalone (audit/retrieval_audit.py). Nenhuma
                         execucao entrega IC e chunking ao mesmo tempo.
offline ................ o protocolo carrega sentence-transformers/
                         all-MiniLM-L6-v2 e avisa sobre requisicao ao HF Hub.
                         A frase "nao faz nenhuma chamada de rede" vale para o
                         auditor standalone e NAO vale para esta amostra.
relevancia ............. Zona 2 e 3 da triagem. Fora do alcance sem rotulo.
```
