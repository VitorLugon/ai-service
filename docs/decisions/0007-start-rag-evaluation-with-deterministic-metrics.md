# ADR 0007 — Iniciar avaliação RAG com métricas determinísticas

## Status

Aceita.

## Contexto

O pipeline RAG já separa recuperação, montagem de contexto, prompt, geração e
composição da resposta fundamentada. Para evoluir esse pipeline com segurança,
é necessário medir retrieval, sources e resposta sem depender imediatamente de
um segundo modelo julgador.

LLM-as-a-judge pode ser útil no futuro, mas introduz custo, variação,
dependência externa e o risco de usar um modelo semelhante para gerar e julgar
a própria resposta.

## Decisão

A avaliação RAG começa com métricas determinísticas:

- retrieval hit;
- source hit;
- keyword coverage;
- correct refusal;
- false refusal;
- unsupported answer;
- Hit Rate@k, Recall@k e MRR para casos com resposta esperada.

O evaluator recebe um pipeline injetável. Testes e avaliação offline usam fakes
determinísticos, sem OpenAI e sem Chroma real. A avaliação real fica restrita a
script explícito com controle por `--max-cases`.

## Motivos

- reproduzível;
- barato;
- fácil de testar;
- sem dependência de segundo LLM;
- bom baseline inicial;
- permite diagnosticar falhas por camada.

## Limitações

As métricas iniciais não medem:

- fluência;
- qualidade estilística;
- correção factual profunda;
- entailment;
- similaridade semântica de resposta;
- citações verificadas por claim.

Keyword coverage mede apenas presença de termos esperados. A detecção de recusa
por falta de evidência é heurística. Source hit indica que uma fonte relevante
chegou à resposta final, não que cada afirmação foi sustentada por ela.

## Futuro

Considerar:

- LLM-as-a-judge;
- semantic answer similarity;
- claim verification;
- human evaluation;
- métricas de groundedness mais robustas;
- comparação entre modelos e prompts.
