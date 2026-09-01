# O que não fazemos

Esta página é normativa e coerente com `CLAIMS.md`. Se um relatório nosso
contradisser algo aqui, é defeito nosso.

## Não certificamos

Não emitimos selo, aprovação ou conformidade. Não somos organismo
certificador, e nada que entregamos deve ser apresentado como certificação.

## Não declaramos qualidade de resposta

O diagnóstico descreve **o que foi recuperado**, não **se o que foi recuperado
era o certo**. São coisas diferentes, e só a primeira está no relatório.

## Não calculamos Recall@K no `DIAGNOSTICO v1`

Recall@K exige julgamento de relevância — humano ou automático — e um conjunto
de referência. Nenhum dos dois existe nesta régua.

## Não inventamos score

Se o seu retriever não expõe score, recusamos em vez de fabricar um. Conversão
monótona declarada (distância → similaridade) é legítima e fica registrada;
inventar não é.

## Não inferimos causalidade

Medimos que documentos se repetem. **Não afirmamos o que a repetição causa** —
custo, latência ou qualidade. Isso exigiria um experimento comparativo: o mesmo
sistema com e sem a repetição, com desfecho definido antes. Ele não foi feito.

Então dizemos *"26% dos slots foram ocupados por id repetido"*, e nunca *"26%
do seu contexto é desperdiçado"*.

## Não dizemos se um valor é alto ou baixo

Não há linha de base. Com poucos sistemas medidos, não existe distribuição de
referência, e chamar um valor de "anômalo" seria opinião com aparência de
medida. Quando houver base, isso muda — e será dito.

## Não alteramos o seu sistema

O snapshot é copiado antes de qualquer consulta.

## Não guardamos seu material indefinidamente

Material bruto expira em 7 dias; relatórios em 90; o manifesto em 365. Query e
documento nunca aparecem em claro por caminho automático — o que aparece é
hash. Credencial é removida sempre, inclusive no modo de exemplos em claro.
