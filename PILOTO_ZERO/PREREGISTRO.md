# Pré-registro — Piloto Zero

**Escrito antes de qualquer contato com cliente externo.** Congelado em
01/09/2026, commit `53eb818`, 408 testes.

Este projeto congela hipótese e critério antes do dado desde o `NORTE §4.2`.
Um piloto qualitativo com N=1 não é experimento estatístico — mas escrever a
previsão antes é o que impede racionalizar qualquer resultado depois como
"era o que esperávamos".

## A pergunta

> Um engenheiro externo consegue conectar um RAG real ao diagnóstico,
> interpretar o resultado, e considerar a evidência suficiente para tomar
> alguma decisão?

**Não** é "o número de duplicação funciona". Isso já foi demonstrado: o
instrumento recuperou 0,56 de uma duplicação injetada de 0,55, num gerador que
não conhece o medidor.

## O que pode falhar, previsto ANTES

O contrato exige três coisas do sistema do cliente:

```
snapshot_dir          um corpus estável e hasheável
consulta(q, top_k)    [(doc_id, score), ...] na ordem do retriever
texto(doc_id)         o texto de um documento
```

Previsão de como um RAG real esbarra nisso:

| caso | o que acontece | previsão |
|---|---|---|
| **A** — retriever acessível, score exposto | adaptador em minutos | `COMPLETE` |
| **B** — retrieval atrás de API, sem score | não há prova de procedência | `BLOCKED`, e o cliente não recebe medição |
| **C** — reranker proprietário, score incompatível | escala desconhecida; conversão monótona resolve **se** a ordem for preservada | `COMPLETE` com conversão declarada, **ou** `BLOCKED` |
| **D** — sem snapshot estável | índice vivo, sem dump; não há o que hashear | **o contrato não cobre**, e este é o buraco que eu não sei tapar |

**O caso D é o que mais me preocupa e o menos coberto.** `snapshot_tem_hash`
exige um arquivo. Um cliente com índice vivo em Pinecone ou Elasticsearch não
tem "o corpus" como diretório, e materializá-lo pode ser inviável ou proibido.
Se o piloto cair em D, o contrato precisa mudar — e isso é decisão do
pesquisador, não remendo durante o piloto.

## O que contaria como fracasso

Escrito antes para não ser negociado depois:

1. **O cliente não consegue escrever o adaptador sozinho** com `QUICKSTART` e
   `SERVICE_CONTRACT` na mão, e precisa de mais de uma intervenção nossa.
2. **`BLOCKED` é lido como "o serviço falhou"** — a pergunta 3, e a que decide
   se o produto se comunica.
3. **O relatório é entendido e considerado inútil** — pior que não entender,
   porque não há o que corrigir na redação.
4. **O onboarding custa horas** enquanto o diagnóstico custa segundos. Aí o
   produto é o onboarding, e a economia do negócio muda inteira.

Qualquer um desses é resultado publicável. Nenhum é motivo para ajustar o
serviço no meio do piloto.

## O que NÃO fazer durante

- não explicar antes quais problemas esperamos encontrar — induz a resposta;
- não corrigir defeito sem registrar a intervenção no momento;
- não alterar régua, contrato ou relatório para acomodar o primeiro caso
  incompatível;
- não perguntar sobre preço antes da pergunta 4;
- não chamar o produto de "auditoria".

A abertura é: *"tenho uma ferramenta que analisa o material que o seu
retrieval realmente devolve e gera um diagnóstico reproduzível; quero testar em
um RAG real com você"*.

## O que o piloto NÃO decide

Um cliente não estabelece frequência de nada. Se o RAG dele cair no caso B,
isso não diz que "a maioria dos RAGs não expõe score" — diz que **um** não
expôs. A taxonomia acima é previsão, não amostra.

## Estado conhecido, declarado antes

```
DOCKER_TEST ......... NAO_EXECUTADO   (sem Docker na máquina de origem)
venv limpa .......... NAO_EXECUTADO   (sem ensurepip; usado pip --target)
onboarding humano ... NAO_EXECUTADO   (é este piloto)
```

O serviço **nunca rodou com material de um cliente externo**. O `PILOTO_ZERO`
está pronto tecnicamente como experimento; **não** está validado
operacionalmente como produto — a diferença é exatamente o que este piloto
mede.

## Registro da decisão

```
piloto executado por ...... ____________  data ....... ____________
caso observado ............ A / B / C / D / outro
resultado ................. ____________
fracasso? qual dos 4 ...... ____________
```

Enquanto estas linhas estiverem em branco, nenhuma afirmação sobre valor
comercial, custo de onboarding ou disposição de pagar tem base.
