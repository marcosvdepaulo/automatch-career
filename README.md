# AutoMatch Career

> **Estado: PROTÓTIPO FUNCIONAL · EM ESCAVAÇÃO**

O AutoMatch Career recebe um currículo em PDF, constrói um perfil identificado, coleta oportunidades e calcula o fit entre candidato e vaga em um monólito modular.

**Protótipo:** https://automatch-career.vercel.app/

O score é uma estimativa experimental baseada nas evidências extraídas e nas regras atuais. Ele não substitui avaliação humana nem garante aderência, contratação ou disponibilidade da vaga.

## Arquitetura

- `domain/`: candidato, competências/evidências, interesses, oportunidade e assessment.
- `ontology.py` e `profile/*.json`: conhecimento global, sem preferências pessoais.
- `profiling.py` e `cv_parser.py`: perfis independentes vindos de fontes explícitas.
- `opportunity_parser.py`: vagas coletadas para objetos de domínio.
- `matcher.py`: avalia exclusivamente `candidate + opportunity`.
- `config.py`: somente configuração operacional.
- `storage/` e `supabase/`: persistência identificada por candidato.
- `api/match.py` e `public/index.html`: contrato HTTP e interface do protótipo.
- `tests/`: domínio, isolamento entre candidatos, ontologia, storage e ciclo do perfil.

Não existe candidato global nem fallback compartilhado. A API exige `pdf_base64`; o CLI exige um PDF no caminho configurado por `CV_PDF_PATH`.

## Execução local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

## Testes

```powershell
python -m pytest -q
```

Veja [ADR-0001](docs/adr/0001-domain-centered-matching.md).

## Limites e direção

- fontes externas de vagas podem mudar ou falhar;
- extração de PDF depende da qualidade e da estrutura do currículo;
- a ontologia de competências e as famílias de função ainda evoluem;
- persistência histórica via Supabase é opcional e requer configuração;
- decisões arquiteturais e próximos passos estão em [`AUTOMATCH_ARQUITETURA_E_ROADMAP.md`](AUTOMATCH_ARQUITETURA_E_ROADMAP.md).
