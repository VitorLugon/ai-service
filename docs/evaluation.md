# Avaliação do classificador de chamados

## Objetivo

A avaliação mede a classificação de categoria e prioridade em chamados
sintéticos do HelpDeskLite. Ela ajuda a comparar estratégias de prompt e a
identificar regressões, mas não representa desempenho em produção.

## Dataset

O dataset está em:

```text
evaluation/tickets.json
```

Os casos são sintéticos, não contêm dados reais de clientes e ainda formam um
conjunto pequeno. Os resultados devem ser lidos como sinal de engenharia para
evolução do prompt, não como garantia estatística.

## Estratégias avaliadas

- `zero_shot`;
- `one_shot`;
- `few_shot`.

`one_shot` é o baseline configurado atualmente por
`OPENAI_PROMPT_STRATEGY=one_shot`.

## Métricas

- acurácia de categoria: proporção de categorias previstas corretamente;
- acurácia de prioridade: proporção de prioridades previstas corretamente;
- acurácia conjunta: proporção de casos em que categoria e prioridade estão
  corretas ao mesmo tempo.

## Resultados

Resultado real registrado em `reports/ticket-classification-evaluation.json`
com `gpt-5-mini`, 12 casos sintéticos e comparação das três estratégias.

| Estratégia | Categoria | Prioridade | Conjunta |
|---|---:|---:|---:|
| `zero_shot` | 11/12, 91,67% | 12/12, 100% | 11/12, 91,67% |
| `one_shot` | 11/12, 91,67% | 12/12, 100% | 11/12, 91,67% |
| `few_shot` | 11/12, 91,67% | 12/12, 100% | 11/12, 91,67% |

As três estratégias empataram nessa execução. `few_shot` não trouxe ganho
mensurável nesse dataset e tende a consumir mais tokens por incluir mais
exemplos.

## Casos divergentes

### `auth-mfa-question`

- categoria esperada: `acesso_e_autenticacao`;
- categoria prevista: `duvida_de_uso`;
- prioridade esperada: `baixa`;
- prioridade prevista: `baixa`.

Análise: o chamado pergunta como ativar autenticação em duas etapas. O modelo
tratou como dúvida de uso, o que é semanticamente plausível. A regra do projeto,
porém, determina que senha, login, MFA e permissões pertencem a
`acesso_e_autenticacao`.

## Casos ambíguos

### `auth-mfa-question`

É uma fronteira entre `duvida_de_uso` e `acesso_e_autenticacao`. A decisão de
negócio favorece `acesso_e_autenticacao` porque MFA é parte do domínio de
acesso, autenticação e permissões, mesmo quando o chamado é formulado como
pergunta.

### `billing-payment-suspended`

A categoria esperada é `cobranca` porque o problema nasce de um pagamento
confirmado que não liberou a conta. A prioridade esperada é `alta` porque uma
equipe está bloqueada, mas não há evidência explícita de impacto amplo, perda de
dados, risco de segurança ou indisponibilidade geral.

### `technical-system-wide-outage`

A categoria esperada é `erro_tecnico` e a prioridade esperada é `critica`,
porque o portal está fora do ar para todos os clientes. Há impacto amplo e
indisponibilidade geral.

### `auth-suspected-admin-compromise`

A categoria esperada é `acesso_e_autenticacao` e a prioridade esperada é
`critica`, porque há possível comprometimento de conta administrativa e risco de
segurança.

## Decisão

`one_shot` permanece como baseline atual. A decisão é provisória: nessa execução
as três estratégias empataram em acurácia de categoria, prioridade e conjunta.
Como `one_shot` já é o baseline configurado e `few_shot` não mostrou ganho, não
há evidência suficiente para trocar o padrão automaticamente.

A decisão deve ser revisada quando:

- o dataset for ampliado;
- o modelo for alterado;
- o prompt for alterado;
- surgirem dados reais anonimizados.

## Limitações

- o dataset é pequeno;
- os casos são sintéticos;
- avaliações com modelos podem variar entre execuções;
- não há dados de produção;
- resumo e tags são avaliados apenas qualitativamente;
- latência, tokens e custo ainda não são medidos pelo relatório.

## Próximos passos

- ampliar o dataset;
- adicionar mais casos limítrofes;
- avaliar resumo e tags;
- medir latência;
- medir tokens e custo;
- repetir avaliações após mudanças de prompt ou modelo.

## Retrospectiva da Semana 2

Na semana 2, o projeto consolidou:

- integração com a OpenAI;
- classificação estruturada com Pydantic;
- endpoint interno protegido;
- tratamento de erros do provedor;
- estratégias de prompt;
- avaliação quantitativa;
- baseline configurável;
- aprendizados sobre testes, prompts e ambiguidades.
