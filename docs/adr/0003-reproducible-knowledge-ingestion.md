# ADR-0003: Ingestão reproduzível e isolada de conhecimento ocupacional

**Status:** Accepted
**Date:** 2026-08-19
**Deciders:** AutoMatch Career maintainers

## Context

O matching lexical atual precisará evoluir para conhecimento estruturado de ESCO e
O*NET. Integrar downloads, parsing e expansão diretamente ao matcher tornaria resultados
irreproduzíveis e misturaria conhecimento global com perfis de candidatos. As fontes
possuem modelos e formatos diferentes: ESCO usa URIs e pilares de ocupações/skills;
O*NET usa O*NET-SOC, Content Model Element IDs e arquivos por categoria.

## Decision

Criar o bounded context `knowledge`, sem dependência do domínio de matching. Cada fonte
tem adapter explícito (`EscoImporter`, `OnetImporter`). Exports locais entram em snapshots
raw imutáveis e verificáveis por SHA-256. Normalização gera entities e relações JSONL
write-once, preservando a identidade oficial. Scopes são definidos por seeds oficiais e
expandidos com profundidade finita.

## Options Considered

### Loader genérico e matching imediato

| Dimension | Assessment |
|---|---|
| Complexidade inicial | Baixa |
| Fidelidade semântica | Baixa |
| Reprodutibilidade | Baixa |
| Acoplamento | Alto |

Rejeitado porque esconderia diferenças das fontes e impediria validar os dados antes do
uso no score.

### Banco/RDF como primeira representação

| Dimension | Assessment |
|---|---|
| Inspeção manual | Média |
| Poder semântico | Alto |
| Custo operacional inicial | Alto |
| Migração de schema | Média |

Adiado. O modelo canônico e JSONL permitem inspecionar proveniência antes de escolher a
serialização RDF e a infraestrutura de consulta.

### Adapters específicos + modelo canônico + JSONL

| Dimension | Assessment |
|---|---|
| Complexidade | Média |
| Fidelidade semântica | Alta |
| Reprodutibilidade | Alta |
| Evolução para RDF | Alta |

Escolhido.

## Consequences

- Labels não são identidade; deduplicação ocorre somente por identidade da fonte.
- Todo artefato normalizado pode ser rastreado ao manifesto raw.
- Os cinco subgrafos são pequenos, determinísticos e revisáveis.
- Atualizar uma fonte exige nova versão de snapshot e novo build de scopes.
- Download automático, mappings ESCO/O*NET, RDF/OWL/SPARQL e consumo pelo matcher são
  deliberadamente excluídos desta decisão.
- Examples O*NET de tecnologia/ferramenta permanecem associados ao código UNSPSC, pois
  a fonte não fornece identidade estável por label.

## Action Items

1. Validar os seeds com especialistas de cada uma das cinco áreas.
2. Executar o pipeline com os exports oficiais escolhidos e revisar os JSONL.
3. Definir o vocabulário RDF e URIs internas sem descartar as identidades externas.
4. Projetar uma interface de consulta antes de qualquer integração com o matcher.
