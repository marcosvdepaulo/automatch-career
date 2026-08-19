# Debug report: convergência de scores em 46,6%

## Reprodução

Quatro textos radicalmente diferentes foram processados pelo caminho real
`CV text -> CandidateProfileBuilder -> CandidateProfile -> CareerMatcher`, contra
a mesma oportunidade (`Python API Engineer`, skills obrigatórias `python` e
`apis`, família `applied_ai`).

### Antes da correção

| Candidato | Conteúdo relevante do CV | CandidateProfile usado pelo matcher | role_fit | skill_fit | evidence | interest | transfer | penalty | final |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| experienced | 8 anos, experiência prática, produção | python/apis; proficiency, confidence, years, context e depth = unknown; 1 evidência lexical genérica | 1.000 | 0.262 | 0.262 | 0.350 | 0 | 0 | 46.6 |
| beginner | aprendendo, explicitamente sem experiência | idêntico ao experienced | 1.000 | 0.262 | 0.262 | 0.350 | 0 | 0 | 46.6 |
| manager | skills aparecem apenas em vagas que recruta | idêntico ao experienced | 1.000 | 0.262 | 0.262 | 0.350 | 0 | 0 | 46.6 |
| keywords | somente `Python APIs` | idêntico ao experienced | 1.000 | 0.262 | 0.262 | 0.350 | 0 | 0 | 46.6 |

O resultado deixa de variar no `CandidateProfileBuilder`: ele descartava todo o
contexto e criava exatamente a mesma evidência para qualquer ocorrência lexical.
O `OpportunityProfile` permaneceu corretamente idêntico, pois a vaga era a mesma.

O matcher amplificava a convergência:

- `proficiency=None` virava `0.45`;
- `confidence=None` virava `0.50`;
- `depth=None` virava `0.50`;
- uma evidência genérica produzia fator `0.75`;
- todas as competências resultavam em força `0.2615625`;
- `role_fit=1.0` dependia somente de a oportunidade possuir role family;
- interesse desconhecido virava `0.35`.

Com os pesos existentes, sem qualquer dado discriminante:
`0.30 + 0.262*0.30 + 0.262*0.20 + 0.35*0.10 = 0.466`, ou 46,6%.

## Campos auditados

Antes, o matcher utilizava `skill_id`, `proficiency`, `confidence`, `depth`,
quantidade de evidências e prioridade de interesse. Ignorava
`CandidateCompetency.experience_years`, `context`, conteúdo/proveniência/metadados
de `Evidence`, além de `CandidateProfile.experience_years`, localização e tipos de
contratação. `role_fit` era derivado apenas da oportunidade.

Localização e contratação continuam fora do score porque ainda não há requisitos
equivalentes confiáveis na vaga. Texto bruto e título da oportunidade também não
entram diretamente no matcher: são responsabilidade do parser. Isso é intencional.

Não foi encontrado estado global de candidato. Builders usam coleções locais e os
modelos usam tuplas/frozen dataclasses. Foi adicionada cópia defensiva de
`Evidence.metadata` para impedir compartilhamento indireto de dicionários mutáveis.

## Causa raiz

Perda estrutural de informação na construção do perfil, seguida por defaults
numéricos que transformavam desconhecido em competência média. Em paralelo,
`role_fit` media apenas a classificação da vaga, não a relação com o candidato.

## Correção

- O builder preserva o trecho, alias, afirmação explícita e anos explicitamente
  declarados por skill. Não infere proficiency, confidence, senioridade ou depth.
- Afirmações são classificadas como `practical`, `learning`, `mention` ou
  `negative`; o texto de origem permanece no objeto de evidência.
- O matcher usa somente sinais explícitos; unknown não recebe mais valores médios.
- `role_fit` passou a comparar competências do candidato com os sinais fortes da
  família da oportunidade.
- `technical_fit` tornou-se dimensão explícita; `skill_fit` permanece como alias de
  compatibilidade.
- A composição final manteve os mesmos pesos de dimensões.

### Depois da correção

| Candidato | Dados discriminantes preservados | role_fit | technical | evidence | interest | transfer | penalty | base | final |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| experienced | assertion=practical, experience_years=8 | 0.500 | 1.000 | 1.000 | 0 | 0 | 0 | 0.650 | 65.0 |
| beginner | assertion=negative, experiência unknown | 0 | 0 | 0 | 0 | 0 | 0.220 | 0 | 0.0 |
| manager | assertion=negative, contexto de recrutamento | 0 | 0 | 0 | 0 | 0 | 0.220 | 0 | 0.0 |
| keywords | assertion=mention, sem experiência declarada | 0.075 | 0.150 | 0.250 | 0 | 0 | 0 | 0.117 | 11.8 |

Beginner e manager permanecem iguais porque ambos apresentam evidência explícita
negativa para as competências exigidas; isso é igualdade semântica em relação à
vaga, não vazamento de perfil.

## Prevenção

O teste de regressão constrói dois CVs opostos que mencionam as mesmas skills e
exige diferença mínima de `0.5` em `technical_fit` e 15 pontos no score final.
