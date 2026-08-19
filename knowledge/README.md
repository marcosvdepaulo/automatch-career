# Knowledge layer

Camada independente para adquirir, versionar, normalizar e recortar exports oficiais de
ESCO e O*NET. Ela **não** é importada por `CandidateProfile`, `OpportunityProfile`,
`FitAssessment` ou pelo matcher.

## Estrutura

```text
knowledge/
  sources/                 adapters independentes ESCO e O*NET
  raw/<source>/<version>/  snapshots imutáveis + manifest.json
  normalized/<source>/<version>/
    concepts.jsonl
    occupations.jsonl
    relations.jsonl
    manifest.json
  scopes/occupational_scopes.json
  rdf/                     reservado para a próxima etapa
```

Os datasets grandes em `raw`, `normalized` e `rdf` não são versionados no Git. Seus
READMEs e a configuração de scopes são versionados.

## Modelo canônico

`CanonicalEntity` preserva `source`, o `source_uri` ESCO ou `source_id` O*NET,
`concept_type`, preferred/alternative labels, descrição e metadata original. Seu
`internal_id` é sempre derivado da identidade externa (`esco:<URI>` ou `onet:<ID>`),
nunca do label. Os tipos atuais incluem occupation, occupation group, skill, skill
group, knowledge, technology, tool e work activity.

`CanonicalRelation` usa `subject`, `predicate`, `object` e metadata explícitos. Não há
colunas achatadas como `related_skills`.

## Pipeline

1. Baixe manualmente o export oficial sem modificá-lo e coloque-o em uma pasta fora de
   `knowledge/raw`.
2. Adquira um snapshot imutável:

```powershell
python -m knowledge acquire --source esco --version 1.2.1 --input C:\datasets\esco-1.2.1
python -m knowledge acquire --source onet --version 30.3 --input C:\datasets\onet-30.3
```

Cada snapshot recebe checksums SHA-256. Uma versão existente não pode ser sobrescrita.

3. Normalize separadamente:

```powershell
python -m knowledge normalize --source esco --version 1.2.1
python -m knowledge normalize --source onet --version 30.3
```

4. Construa os cinco scopes a partir dos dois datasets:

```powershell
python -m knowledge build-scopes `
  --dataset knowledge/normalized/esco/1.2.1 `
  --dataset knowledge/normalized/onet/30.3 `
  --build-id esco-1.2.1_onet-30.3_depth-0
```

Os subgrafos ficam em `knowledge/normalized/scopes/<build-id>/<scope>/`. Use `--depth 1`
para incluir uma camada de ocupações relacionadas e seus conceitos. Não existe expansão
ilimitada.

## Edição dos scopes

Edite `scopes/occupational_scopes.json`. Cada scope contém arrays independentes `esco`
e `onet`, somente com URIs/códigos oficiais revisáveis. `seed_notes` ajuda a revisão
humana, mas não participa da identidade nem da seleção. Busca textual pode auxiliar a
descoberta fora do pipeline; não decide o scope persistido.

## Formatos suportados e limites atuais

- ESCO: exports tabulares de occupations, skills/skill groups e arquivos oficiais de
  relações. `skillType=knowledge` é preservado; os demais conceitos não são promovidos
  artificialmente a technology/tool.
- O*NET: Occupation Data, Skills (incluindo Essential/Transferable), Knowledge, Work
  Activities, Technology/Software Skills, Tools Used e Related Occupations em TXT/TSV,
  CSV ou JSON tabular.
- Technology/Tool examples do O*NET não possuem um ID próprio estável. O conceito usa o
  código oficial UNSPSC como identidade e preserva examples como labels alternativos e
  metadata, evitando inventar identidade a partir do texto.
- A aquisição nesta etapa importa exports locais. Download autenticado/interativo,
  mappings ESCO↔O*NET, RDF, OWL, SPARQL e integração ao matcher ficam para depois.

Veja [ADR-0003](../docs/adr/0003-reproducible-knowledge-ingestion.md).
