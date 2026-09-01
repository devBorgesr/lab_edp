# Quickstart — diagnóstico do seu retrieval

Para um engenheiro que nunca viu este projeto. Leitura: 5 minutos.

## O que você envia

Um **adaptador** de ~40 linhas com quatro métodos, e um arquivo de perguntas.

```python
from auditor.contrato import SistemaAuditavel

class MeuRAG(SistemaAuditavel):
    VERSAO = "meurag-1"

    @property
    def snapshot_dir(self):          # diretório com episodic.json do seu corpus
        return self._dir

    def consulta(self, query, top_k):
        # [(doc_id, score), ...] na ordem que SEU retriever devolveu
        return [(d.id, float(d.score)) for d in meu_retriever.search(query, top_k)]

    def texto(self, doc_id):
        return meu_corpus[doc_id]

    def controle_para(self, q):      # só o protocolo BASICO usa; DIAGNOSTICO ignora
        return []
```

**O `score` não é opcional.** É a prova de que o ranking saiu de um retriever e
não de uma lista qualquer de ids. Sem ele o serviço recusa e você recebe zero
medições — ver "Se o seu retriever não devolve score", abaixo.

## Como executar

```bash
pip install auditor-retrieval
auditor check --input <snapshot> --queries perguntas.json \
              --protocol DIAGNOSTICO --adaptador <o seu>
```

`check` é um **dry-run**: diz `READY` ou `BLOCKED` sem processar nada. Rode-o
primeiro — ele custa segundos e evita descobrir um problema depois do trabalho.

```bash
auditor run --input <snapshot> --queries perguntas.json \
            --protocol DIAGNOSTICO --adaptador <o seu> --output ./saida
```

## O que você recebe

```
<audit_id>/
  manifest.json          fonte de verdade, com sha256
  reports/executive.md    uma página
  reports/technical.md    evidência completa
  artifacts/checks.json   cada verificação e o que ela detecta
```

## Quanto tempo leva

Medido em corpus de 137 documentos e 50 perguntas: **~18 segundos**, zero
chamadas a modelo. Corpus maior escala com o número de perguntas.

## `COMPLETE` e `BLOCKED`

**`COMPLETE`** — a régua executou. Você recebe as medições.

**`BLOCKED`** — *aquela régua* não pôde ser executada sobre *aquele sistema*.
Não é erro do serviço, e não diz que seu sistema é inauditável: outra régua pode
se aplicar a ele. O relatório diz exatamente qual pré-condição falhou.

Você **ainda recebe as medições descritivas** sob `BLOCKED`, desde que o ranking
tenha procedência provada.

Exit codes: `0` COMPLETE/READY · `2` BLOCKED · `3` entrada inválida · `4` erro
do serviço.

## Se o seu retriever não devolve score

Casos medidos:

| situação | o que fazer |
|---|---|
| índice retorna **distância** (FAISS L2, por ex.) | converta com função monótona decrescente, ex. `1/(1+d)`, e **declare a conversão** |
| score pode ser ≤ 0 (cosseno) | desloque: `s + 1 + ε`. Monótono, preserva a ordem |
| retriever não expõe score algum | **não dá para auditar como está.** O serviço recusa em vez de inventar |

Conversão monótona preserva a ordem e muda só a escala — é legítima. Inventar
score não é, e é por isso que o serviço barra.

## O que este diagnóstico NÃO faz

Não mede qualidade de resposta, Recall@K nem relevância — nenhum julgamento é
feito. Não certifica nada. Descreve **o que foi recuperado**, não **se o que foi
recuperado era o certo**.

Ver `CLAIMS.md` para a lista completa do que o serviço pode e não pode afirmar.
