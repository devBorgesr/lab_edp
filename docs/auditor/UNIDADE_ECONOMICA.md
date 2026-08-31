# Unidade econômica — o que já é medido, e o que ainda não

**31/08/2026. Nenhum preço definido.** Medir primeiro, precificar depois.

## O que o serviço já registra por auditoria

```
tempo_por_etapa_s      snapshot, entrada, retriever, ranking, estratos, …
tempo_total_s
tempo_servico_s        inclui validação, workspace e gravação
chamadas_ao_modelo
tokens_entrada / tokens_saida
```

## Medido, no caso real do EDP

| | |
|---|---|
| corpus | 137 documentos, 198 entradas de índice |
| queries | 50 |
| tempo do engine | **18,1 s** |
| chamadas ao modelo | **0** — bloqueou antes do julgador |
| custo de modelo | **`null`** |

O `null` é deliberado. Não há tabela de preço registrada para a configuração
congelada, e **zero seria mentira**: o campo vem com
`custo_nao_estimado_porque` dizendo exatamente isso.

## O que este número ainda não é

18,1 s é o custo de uma auditoria que **bloqueou cedo**. Uma auditoria que
chegasse ao julgador pagaria 500 chamadas de modelo, e esse é o componente que
domina. Usar 18,1 s para projetar margem seria projetar a partir do caso mais
barato possível.

## O que falta medir antes de precificar

```
custo de modelo          precisa da tabela oficial + config congelada
custo de infraestrutura  ainda roda local
armazenamento            retenção definida, volume não medido
tempo humano             o adaptador do cliente é escrito por alguém
suporte                  sem cliente, sem dado
```

**Tempo humano é o provável dominante** e é o único que não aparece no
`Contabilidade`. Escrever um adaptador para o RAG de um cliente é trabalho de
pessoa, e nenhuma medição automática vai capturá-lo.

## Quando preencher o preço

`auditor/custos.py` tem `PRECO_POR_MTOK` **vazio de propósito**. Ao preencher,
registrar junto:

```
modelo · preço entrada · preço saída · fonte · data
```

Sem esses quatro campos o custo calculado é um número sem procedência — o mesmo
defeito que este projeto passou o mês corrigindo em outro contexto.
