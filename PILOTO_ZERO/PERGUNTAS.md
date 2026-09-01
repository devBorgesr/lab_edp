# As oito perguntas

Feitas **depois** de você receber o relatório. Respostas registradas
literalmente — nada é inferido.

```
1. Você conseguiu executar?
2. Entendeu o que COMPLETE significa?
3. Entendeu o que BLOCKED significa?
4. O relatório foi útil?
5. O relatório mudou alguma decisão?
6. Você pagaria por isso?
7. Quanto pagaria?
8. Usaria novamente?
```

A **3** é a que mais importa para nós. Se `BLOCKED` soou como *"o serviço
falhou"* em vez de *"o serviço me disse algo"*, o problema é do nosso
relatório, não da sua leitura.

As **6 e 7** só valem depois da **4**: quem não achou o relatório útil não tem
como dizer se pagaria.

## Registro de integração — preenchido DURANTE, não depois

O relatório pode ser excelente e o produto ainda falhar aqui. Se o cliente
levar seis horas para conectar, o problema não está no diagnóstico — está no
onboarding, e é isto que mede.

### O RAG

```
framework ........................ ____________
vector DB ........................ ____________
retriever ........................ ____________
reranker ......................... ____________  (proprietário? sim/não)
score exposto .................... sim / não
tipo de score .................... similaridade / distância / nenhum
conversão necessária ............. ____________
ids estáveis ..................... sim / não
snapshot reproduzível ............ sim / não
```

### Tempo — quatro marcos, em relógio

```
primeiro contato  -> `check` READY ......... ____________
primeiro contato  -> `check` BLOCKED ....... ____________
adaptador escrito -> `check` READY ......... ____________
adaptador escrito -> `run` COMPLETE ........ ____________
```

### Intervenção

```
linhas de código do adaptador .............. ____________
alterações feitas pelo CLIENTE ............. ____________
alterações feitas por NÓS .................. ____________
bloqueios encontrados ...................... ____________
perguntas que o cliente fez ................ ____________
```

Toda intervenção nossa é registrada **no momento em que acontece**. Consertar
durante o piloto sem anotar transforma um problema de onboarding em um
problema invisível.

## Preço

```
preço ofertado ... ______   aceito / recusado
motivo ........... ____________________
```

Preço não está no código, e nenhuma resposta aqui altera o serviço.
