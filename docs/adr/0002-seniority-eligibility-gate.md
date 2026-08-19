# ADR-0002: Senioridade como gate de elegibilidade

**Status:** Accepted
**Date:** 2026-08-19
**Deciders:** AutoMatch Career maintainers

## Context

O parser já identificava alguns termos de senioridade, mas o matcher ignorava o campo. Uma penalização ponderada permitiria que technical fit alto compensasse uma incompatibilidade que o candidato considera eliminatória.

## Decision

Representar senioridade como escala ordinal e aplicar uma política de elegibilidade antes do ranking. O candidato declara seu nível e se aceita vagas um nível acima. Senioridade desconhecida permanece desconhecida e não causa exclusão silenciosa. `lead` e `manager` ficam fora da escala técnica nesta etapa.

## Options Considered

- Grafo por senioridade: rejeitado por duplicar a ontologia e introduzir complexidade sem benefício para uma relação ordenada.
- Apenas peso no score: rejeitado porque outras dimensões poderiam compensar uma incompatibilidade eliminatória.
- Escala ordinal + rubricas futuras por role family: escolhido por ser explícito, barato e extensível.

## Consequences

- Vagas incompatíveis não chegam ao Top 5.
- Uma vaga um nível acima exige opt-in explícito.
- Vagas sem senioridade continuam elegíveis, mas marcadas como `unknown`.
- `seniority_alignment` fica observável sem alterar os pesos gerais nesta etapa.
- Rubricas específicas por família profissional permanecem para a próxima evolução.
