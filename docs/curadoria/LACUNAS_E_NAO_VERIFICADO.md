# Lacunas e `NAO_VERIFICADO`

O que esta curadoria **não** apurou. Escrito para que nenhum item vire
afirmação por omissão.

## Não verificado — 7 itens

### 1. Uso de `sha256` no kernel (10 arquivos)
`store.py`, `pareto_store.py`, `cache.py`, `config.py` e outros usam `sha256`.
**Não abri cada uso.** Pode ser cache, integridade ou identidade — e a matriz
de proveniência depende disso para dizer se há duplicação com o
`sha256_episodic` do MVP.

### 2. `LineageTracker` está ativo?
`is_lineage_enabled()` existe em `runtime/lineage.py`. **Não medi o default nem
quem chama.** 340 linhas cuja execução em produção é desconhecida.

### 3. Cobertura de `write_provenance.stamp_and_classify`
`EDP_WRITE_PROVENANCE` está **LIGADA** por default, mas **não medi em quantos
caminhos de escrita ela roda**. Uma flag ligada não implica cobertura total.

### 4. Volume real de `events.jsonl`
A rotação a 10 MB sugere que o volume foi pensado. **Não medi arquivo real em
produção.** Isso é pré-requisito para o candidato de acoplamento nº 2.

### 5. Conteúdo de `observability/{logger,tracing}.py`
295 linhas, 2 importadores, 0 testes. **Não abri.**

### 6. Suíte de testes do `sf_exportador`
6.255 linhas de JS. **Não localizei suíte de teste.** Todas as afirmações
sobre o exportador nesta curadoria são sobre existência e tamanho, não sobre
funcionamento.

### 7. Por que cada flag foi desligada
Encontrei as 12 flags e seus testes. **Não encontrei registro da decisão** de
manter cada uma OFF. Sem isso, "engenharia não decidida" é leitura minha, e
pode existir motivo documentado que não achei.

---

## Lacunas de método nesta curadoria

**Não medi qualidade de código.** Só existência, importador, teste e flag. Um
módulo "vivo" pode estar mal escrito; um "sem teste" pode estar correto.

**Não executei os 27 módulos sem teste.** "Sem teste" é ausência de
verificação, não presença de defeito. A distinção importa e foi mantida em
todas as fichas.

**Não medi custo de acoplamento.** As classificações "acoplar agora / depois /
precisa de teste" são **julgamento a partir de tamanho, cobertura e risco de
alterar a régua** — não são medição. Este projeto já aprendeu duas vezes o que
acontece quando se trata julgamento como medida.

**Não testei nenhum candidato de acoplamento.** Nenhuma flag foi ligada,
nenhum código foi alterado, nenhum evento foi emitido durante esta fase.

---

## O descompasso que a curadoria expôs

| | |
|---|---|
| módulos do kernel sem teste | **27 de 49 (55%)** |
| linhas da Bancada | ~3.000 |
| arquivos de teste da Bancada | **2** |
| flags de engenharia testada, desligadas | **12** |
| `metrics.py`: importadores / testes | **22 / 0** |

**Nenhuma capacidade do kernel está em `VALIDADA`** no sentido que este
projeto usa a palavra: medida contra um critério congelado antes do dado. Elas
estão em `TESTADO` — que é mais do que a maioria dos códigos, e menos do que
"pronto".

---

## O que mudaria a curadoria se fosse verificado

Em ordem de impacto:

1. **volume do `events.jsonl`** — se for grande demais, o candidato nº 2 cai;
2. **motivo de cada flag estar OFF** — pode haver razão que desqualifica um
   candidato de "acoplar agora";
3. **`LineageTracker` ativo ou não** — muda a matriz de proveniência;
4. **testes do exportador** — todo o Serviço C depende disso, e ele já está
   marcado como não recomendado.

Nenhum destes exige experimento. Todos exigem meia hora de leitura que eu não
fiz nesta fase, e prefiro registrar do que estimar.
