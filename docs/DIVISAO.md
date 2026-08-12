# A divisão dos documentos — dado do sujeito vs. instrumento

**2026-08-12.** Este repo já separava **código** por essa linha desde a FASE
B2: `bancada/` é agnóstica de sujeito (e proibida de importar `edp.*`,
invariante travada em `tests/test_fronteira.py`), `sujeitos/edp/` é
específica. Para **documento** a separação não existia — todos os `.md`
viviam juntos em `docs/`. Este arquivo cria a divisão e declara o critério.

---

## O critério

| categoria | pergunta que decide | onde vive |
|---|---|---|
| **instrumento** | outro pesquisador, medindo outro sujeito, usaria isto? | `docs/instrumentos/` |
| **dado do sujeito** | isto é um achado sobre **este** EDP? | `docs/sujeito_edp/` |
| **meta do lab** | isto descreve o próprio laboratório? | `docs/` (raiz) |

A pergunta do instrumento é deliberadamente "outro **sujeito**", não "outro
projeto". Um documento que só faz sentido se o sujeito for o EDP é dado,
mesmo que seja genérico em estilo.

## Por que a divisão importa (e não é arrumação)

O `NORTE.md §8` do `edp_v5` afirma que **o método é o ativo** — foi ele que
tirou 9 numa auditoria onde o código tirou de 4 a 7, e é "a única coisa
aqui que um concorrente não copia lendo o repositório".

Se isso é verdade, então o método precisa estar **separável** do sujeito
para poder ser mostrado, publicado ou vendido sem expor os dados do EDP.
Enquanto instrumento e dado moram no mesmo arquivo, o ativo não é
destacável. `docs/instrumentos/` é o ativo; `docs/sujeito_edp/` é o
prontuário do paciente.

## Consequência de método: o mesmo documento pode ser os dois

`AUDITORIA_CONSTANTES_NAO_CALIBRADAS.md` é os dois ao mesmo tempo — o
esquema de tiers D/C/B/A serve para qualquer base de código; o censo de ~90
constantes é só do EDP. A divisão não foi feita duplicando o arquivo: o
**método foi extraído** para `instrumentos/TIERS_DE_JUSTIFICATIVA.md`,
reescrito sem o sujeito, e o documento original ficou em `sujeito_edp/`
como o censo que é.

Essa é a operação padrão daqui pra frente: quando um achado carrega método
reusável, o método sai para `instrumentos/` **reescrito**, não copiado.
Copiar traria o sujeito junto e a separação seria só de pasta.

---

## Estado atual

### `docs/instrumentos/` — servem a outro pesquisador

| arquivo | o que é |
|---|---|
| `TIERS_DE_JUSTIFICATIVA.md` | 4 tiers (medido/argumentado/anedótico/nu) para auditar constante de ajuste em qualquer código, com as 3 regras que evitam absolver comentário simpático |
| `PROTOCOLO_TELEMETRIA_DE_TOKENS.md` | 7 decisões para coletar `(chars, tokens reais)` em qualquer sistema que chame LLM cobrado por token, e a ordem de fases que não é negociável |
| `TEMPLATE_PREREGISTRO.md` *(fica na raiz por ora — ver pendência)* | estrutura de pré-registro derivada por comparação de 4 pré-registros reais |

### `docs/sujeito_edp/` — achados sobre este EDP

Migrados do `edp_v5` em 2026-08-12 (commits `93cfbf5`/`6b7a0fc` lá):

| arquivo | achado principal |
|---|---|
| `AUDITORIA_CONSTANTES_NAO_CALIBRADAS.md` | ~90 constantes tier A contra 6 mecanismos tier D; `score=0.65` em 4 call sites desconectados do parâmetro nomeado; 5 limiares de similaridade espalhados; `SESSION_GAP_THRESHOLD_SEC` definido duas vezes |
| `AUDITORIA_ANCORA_DE_TAREFA.md` | o defeito que o próprio projeto registrou em 07/08 (`consolidated` sem teto) segue aberto; a peça 2.6f não o fechou, mudou o que ele mede; o teste dedicado nunca exercita esse caminho |
| `ANALISE_TOKENIZER_MEMORIA.md` | três aproximações desalinhadas de "token" e nenhuma medida real; o token real já chega em toda chamada e é descartado |
| `CRUZAMENTO_MEMORIA_INFERENCIAL_x_TOKENS.md` | a memória inferencial é em boa parte ligar o que já existe e está desligado; a instrumentação é pré-requisito dela, não tarefa paralela |
| `AUDITORIA_FASE1_TOKENS.md` | spec congelada da Fase 1 + auditoria de 4 repositórios externos (2 números citados por uma análise de terceiro não existem nos repos) + nota de execução |

### `docs/` (raiz) — classificação dos que já estavam aqui

Classificados, **não movidos** — mover quebraria links em documentos já
commitados. A tabela existe para a decisão ser auditável; a mudança física
é decisão do Daniel.

| arquivo | categoria |
|---|---|
| `TEMPLATE_PREREGISTRO.md` | **instrumento** — moveria |
| `ACERVO_EXPERIMENTOS.md` | meta do lab — fica |
| `PROVENIENCIA_LAB.md` | meta do lab — fica |
| `preregistro_experimento_e7.md`, `preregistro_experimento_018.md`, `plano_experimento_e8.md` | dado do sujeito |
| `RELATORIO_E7_HARNESS.md`, `RELATORIO_EXP018_HARNESS.md`, `RELATORIO_EXP018_T1.md` | dado do sujeito (harness é do experimento, que é do EDP) |
| `VEREDITO_E7.md`, `VEREDITO_EXP018.md`, `VALIDACAO_FIX_TOXIC_GUARDS.md` | dado do sujeito |
| `ACHADO_FLAG_UNICA_TOXICIDADE.md`, `ACHADO_PREMISSAS_RETRIEVAL.md` | dado do sujeito |
| `docs_edp_v5/` (pasta inteira) | dado do sujeito, herdado — não editar (regra pré-existente) |

---

## O que NÃO foi migrado, e por quê

**A frente do Gap Event ficou no `edp_v5`** — `scripts/medir_gap_score*.py`,
`scripts/medir_alcance_wiki.py`, `scripts/lint_wiki.py`,
`tests/test_medicao_wiki.py`, `tests/test_lint_wiki.py`, e os pré-registros
correspondentes. Pelo critério deste arquivo, todos são material de lab.
Não foram movidos por dois motivos que se somam:

1. `edp_v5/docs/AVISO_INSTANCIA_LIMPA.md` (Regra 1) lista esses caminhos
   como desqualificantes para leitura. Movê-los invalida a lista: uma
   instância limpa procuraria em `edp_v5/scripts/`, não acharia, e poderia
   ler a cópia do lab achando que é segura. A migração exigiria reescrever
   a Regra 1 **junto**, na mesma operação.
2. Decidir como registrar esses experimentos no `ACERVO_EXPERIMENTOS.md` —
   que nome, que descrição, que categoria — **é um julgamento sobre o
   gabarito**, exatamente o que o AVISO diz que a instância contaminada não
   pode fazer. Quem escreveu esta migração é essa instância.

Registrado aqui para não virar achado perdido. É trabalho para uma sessão
com o AVISO na mão, não para esta.

**`MAPA_FUNCIONALIDADES_CLIENTE.md` ficou no `edp_v5`** — é catálogo de
capacidade para público externo (o funil comercial do `NORTE.md §2`), não
medição sobre o sujeito. É o caso mais de fronteira da rodada: ele *é*
cruzamento de dados dos três repositórios. Ficou fora porque o critério é o
destinatário — quem lê é cliente, não pesquisador.
