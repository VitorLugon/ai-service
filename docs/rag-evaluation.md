# RAG Evaluation

## Objetivos

A avaliação RAG mede separadamente recuperação, preservação de fontes,
cobertura simples da resposta e comportamento quando não há evidência
relevante. Ela cria um baseline determinístico antes de introduzir julgadores
subjetivos ou métricas semânticas mais caras.

## Dataset

O dataset versionado fica em:

```text
evaluation/rag_cases.json
```

Ele usa apenas a base sintética `knowledge/articles.json` e não contém dados
reais de clientes.

Composição atual:

- 16 casos no total;
- 12 casos com resposta esperada;
- 4 casos sem evidência;
- 2 casos com múltiplas fontes relevantes.

## Tipos de Casos

`expected_behavior="answer"` indica que a base possui evidência para responder.
Esses casos devem ter ao menos um `relevant_article_id` e ao menos uma keyword
esperada.

`expected_behavior="insufficient_evidence"` indica pergunta fora da base. Esses
casos não possuem artigos relevantes e podem ter lista vazia de keywords.

## Métricas

### Retrieval Hit

Para casos com resposta esperada, mede se ao menos um artigo relevante apareceu
na lista de artigos recuperados.

### Source Hit

Para casos com resposta esperada, mede se ao menos um artigo relevante apareceu
em `RagAnswer.sources`.

### Keyword Coverage

Mede a fração de keywords esperadas encontradas no texto final da resposta, com
normalização de maiúsculas, acentos e espaços. A métrica retorna `N/A` quando
não há keywords esperadas.

### Correct Refusal

Para casos sem evidência, mede se a resposta parece recusar por falta de
informação suficiente.

### False Refusal

Para casos com resposta esperada, mede se a resposta parece recusar apesar de
haver evidência esperada no dataset.

### Unsupported Answer

Para casos sem evidência, marca resposta substantiva quando `source_count=0` e
o texto não parece uma recusa por falta de informação.

## Interpretação Por Camada

`retrieval_hit=False` sugere problema de retrieval.

`retrieval_hit=True` e `source_hit=False` sugere perda na montagem de contexto,
orçamento ou composição das fontes.

`source_hit=True` e `false_refusal=True` sugere problema na geração ou no prompt,
pois a evidência chegou ao contrato final.

Esses diagnósticos são sinais de engenharia, não conclusões infalíveis.

## Limitações

- keyword coverage não mede factual correctness;
- refusal detection é heurística;
- source_hit não prova que a resposta usou a fonte;
- sources representam contexto fornecido à geração;
- não há claim-level verification;
- não há entailment checking;
- não há semantic answer similarity;
- não há LLM-as-a-judge;
- o dataset é pequeno e sintético;
- métricas devem ser interpretadas em conjunto.

## Execução Offline

```powershell
python -m scripts.evaluate_rag_offline
```

Esse comando usa o dataset real e um pipeline fake determinístico. Ele não
acessa OpenAI, não consulta Chroma real, não lê `.env` e não consome créditos.

## Execução Real

```powershell
python -m scripts.evaluate_rag --max-cases 3
```

Esse comando usa o pipeline real com OpenAI e Chroma persistente. Antes de
executar, a coleção precisa estar indexada e a chave da OpenAI configurada. O
script imprime contagens e modelos, mas não imprime chaves, embeddings, headers
ou objetos brutos do provider.

Use `--max-cases` para controlar custo. Também é possível executar um caso
específico com `--case-id`.

## Baseline

Baseline offline determinístico: 16 casos executados com fake pipeline,
retrieval hit rate 1,0000, source hit rate 1,0000, mean keyword coverage 1,0000,
correct refusal rate 1,0000, false refusal rate 0,0000 e unsupported answer rate
0,0000.

Baseline real parcial: executado em 2026-08-18 com `gpt-5-mini`,
`text-embedding-3-small`, Chroma persistente, coleção
`helpdesklite-knowledge-v1`, 12 artigos indexados e 3 de 16 casos avaliados.

Resultado da amostra:

- retrieval hit rate: 1,0000;
- source hit rate: 1,0000;
- mean keyword coverage: 0,8889;
- correct refusal rate: N/A;
- false refusal rate: 0,0000;
- unsupported answer rate: N/A.

Casos executados:

- `rag-recover-access`;
- `rag-configure-mfa`;
- `rag-empty-pdf`.

O baseline real completo permanece pendente.
