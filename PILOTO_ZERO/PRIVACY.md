# Privacidade

## O que sai nos artefatos

**Query e documento nunca aparecem em claro por caminho automático.** O que
aparece é hash:

```
<query:b8e56193c10f>
```

Texto em claro exige `--exemplos-em-claro`, decisão explícita de quem executa.

## Segredo é removido nos dois modos

Chave de API, token, JWT, chave privada, e-mail e CPF são removidos **mesmo
com** `--exemplos-em-claro`. Quem executa pode autorizar mostrar texto do
cliente; não pode autorizar vazar credencial.

A varredura roda sobre a estrutura inteira antes de gravar, inclusive em campos
que ninguém previu. **Se um segredo sobreviver, a gravação falha** em vez de
escrever — vazamento é irreversível.

## Retenção

```
input      7 dias      material bruto que você enviou
artifacts  30 dias
reports    90 dias
manifest  365 dias     a prova de que a auditoria aconteceu
```

O material bruto é o mais sensível e expira primeiro.

**A expiração não roda sozinha.** É o comando `auditor expirar`, que o operador
agenda; sem `--executar` ele apenas lista o que passou do prazo.

Isso é deliberado — apagar material de cliente por conta própria, dentro de um
processo que atende requisição, é pior que não apagar. Mas significa que **os
prazos acima são política, não automatismo**: se ninguém agendar o comando,
nada expira.

*Errata 01/09: até esta data os prazos estavam documentados e nenhum mecanismo
os aplicava. Uma garantia de retenção sem mecanismo é uma garantia que não
existe.*

## Isolamento

Cada auditoria tem diretório próprio por `audit_id`. Reaproveitar diretório é
recusado, e escrever fora da própria raiz é recusado.

## O sistema auditado não é alterado

O adaptador **copia** o snapshot antes de consultar. Há teste garantindo que o
arquivo de origem não muda entre duas execuções. Auditar um sistema não pode
alterar o sistema auditado.
