# O que você recebe

```
<audit_id>/
  manifest.json          fonte de verdade
  job.json               estado, versões, tempos
  reports/executive.md   uma página
  reports/technical.md   evidência completa
  artifacts/checks.json  cada verificação
  input/                 o que você enviou
```

## Relatório executivo

Uma página, cinco seções: **status · protocolo · o que foi medido · o que NÃO
foi medido · qual decisão está pendente**.

Cada número vem com `N`, unidade e intervalo de confiança. Número sem esses
campos não sai daqui — sem referente, um número é alegação.

A seção *"o que NÃO foi medido"* é obrigatória, inclusive quando tudo deu
certo. Sem ela o leitor completa a lacuna sozinho, e completa para o lado
otimista.

## Relatório técnico

A evidência inteira: cada verificação, **o que cada uma detecta**, a evidência
numérica de cada uma, as etapas executadas e as não executadas, procedência e
custo.

Carrega as mesmas ressalvas do executivo. Um documento mais detalhado que
ressalva menos seria pior — pareceria mais autoritativo justamente onde afirma
menos.

## Manifesto

A fonte de verdade, e o que permite contestar. Traz:

- `sha256` do corpus e do conjunto de perguntas;
- identidade e versão da régua, do adaptador e do serviço;
- toda verificação, com estado e evidência;
- as medições com metadados completos;
- tempos e custos;
- `sha256` do manifesto inteiro.

Tudo que aparece nos relatórios está representado aqui.

## Evidência

`checks.json` traz cada verificação com o defeito que ela detecta. Toda
verificação é obrigada a declarar isso — uma checagem cuja grandeza o defeito
não moveria não é evidência de nada.

## Reprodutibilidade

Mesma entrada produz as mesmas medições e os mesmos hashes. O que muda entre
execuções: `audit_id`, horário e tempos medidos.

O seu sistema **não é alterado**: o snapshot é copiado antes de qualquer
consulta, e há teste garantindo que o original não muda.
