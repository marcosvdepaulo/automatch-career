# ADR-0001: Matching centrado em entidades de domínio

**Status:** Accepted
**Date:** 2026-08-19
**Deciders:** AutoMatch Career maintainers

## Context

O runtime mantinha um candidato global em `Config`, combinando preferências pessoais, ontologia e infraestrutura. Isso permitia vazamento de dados entre requisições e fallback silencioso para o perfil do autor.

## Decision

O monólito passa a usar `CandidateProfile`, `OpportunityProfile` e `FitAssessment` independentes de infraestrutura. O matcher recebe candidato e oportunidade explicitamente. `AppConfig` contém apenas settings operacionais. Ontologia contém somente conhecimento global. Ausência de candidato é erro de validação.

## Options Considered

- Manter adapters do perfil global: menor mudança imediata, mas preservaria o acoplamento e o risco multiusuário.
- Reescrever como microservices: isolamento forte, custo e complexidade desnecessários nesta etapa.
- Monólito modular com migração incremental: escolhido por corrigir fronteiras sem reescrever scraping e integrações.

## Consequences

- Perfis podem ser construídos e avaliados de forma independente.
- Novas fontes de evidência entram no builder sem alterar o matcher.
- Callers precisam fornecer um candidato válido; o perfil padrão deixa de existir.
- Calibração avançada do algoritmo permanece para uma etapa futura.
