# Piloto externo — protocolo

**Status: não executado.** Este documento é o preparo, não o resultado. Nenhum
cliente externo rodou este serviço até 31/08/2026.

O piloto é a prova que falta, e ela não é técnica.

## O que o piloto testa

Não testa se o código funciona — 276 testes cobrem isso. Testa se **alguém
entende e valoriza um `BLOCKED`**.

Essa é a aposta central do produto: um relatório que diz *"não pude medir isto,
e aqui está exatamente por quê"* vale dinheiro. Se o piloto mostrar que o
cliente lê `BLOCKED` como *"o serviço falhou"*, a aposta está errada, e é
melhor descobrir com três clientes do que com trinta.

## O que o cliente precisa entregar

```json
{
  "schema":   "AuditInput v1",
  "snapshot": "<diretório do corpus>",
  "queries":  "<arquivo de perguntas reais>",
  "protocol": "BASICO",
  "adapter":  "<a ser escrito para o sistema dele>"
}
```

O adaptador é o único trabalho de integração: quatro métodos
(`snapshot_dir`, `consulta`, `texto`, `controle_para`). O `consulta` precisa
devolver `(doc_id, score)` — sem score não há prova de procedência e o serviço
barra.

**Este é o ponto de atrito previsto.** Um RAG que não expõe score do retriever
não pode ser auditado como está. Vale medir quantos clientes esbarram nisso.

## Sequência

```
snapshot → check → READY/BLOCKED → run → relatório → entrevista
```

O `check` vem antes de propósito: o cliente descobre se o material dele
sustenta a régua **antes** de qualquer processamento pago.

## Entrevista — perguntas, na ordem

Perguntar **depois** de entregar o relatório, e não antecipar a resposta.

1. Conseguiu fornecer os dados? Onde travou?
2. Entendeu o que o `check` respondeu?
3. Leu o relatório executivo inteiro? O que pulou?
4. Quais números foram úteis? Quais não significaram nada?
5. O que você esperava receber e não recebeu?
6. **`BLOCKED` soou como "o serviço falhou" ou como "o serviço me disse algo"?**
7. Pagaria por isto? Quanto?
8. Pagaria de novo, daqui a um mês?

A pergunta 6 é a que decide a tese. As 7 e 8 só valem depois dela — quem não
entendeu o que recebeu não sabe dizer se pagaria.

### Sinais, do mais fraco ao mais forte

```
"interessante"                        não significa nada
"quanto custa?"                       sinal
"posso mandar nosso RAG?"             melhor
"preciso disso todo mês"              é produto
```

## O que NÃO dizer ao cliente

- que existe Recall@K validado — **não existe**;
- que o serviço certifica, aprova ou emite selo;
- que `BLOCKED` é problema dele. `BLOCKED` diz que **aquela régua** não se
  aplica **àquele sistema**;
- que o `BASICO` sustenta afirmação científica. Ele é demonstrativo, e o
  relatório diz isso sozinho.

## Registro obrigatório por piloto

```
cliente ........... ____________  data ......... ____________
adaptador escrito por ........... cliente / nós
tempo até o primeiro `check` .... ____________
status do check ................. READY / BLOCKED
travou em ....................... ____________
entendeu o BLOCKED .............. sim / não / parcialmente
números citados espontaneamente . ____________
pagaria ......................... ____________
```

Preencher **durante** a entrevista. Reconstruir de memória depois é a forma
mais fácil de ouvir o que se queria ouvir.
