# AutoMatch Career

O AutoMatch Career descobre oportunidades e calcula fit por candidato em um monólito modular.

## Arquitetura

- `domain/`: candidato, competências/evidências, interesses, oportunidade e assessment.
- `ontology.py` e `profile/*.json`: conhecimento global, sem preferências pessoais.
- `profiling.py` e `cv_parser.py`: perfis independentes vindos de fontes explícitas.
- `opportunity_parser.py`: vagas coletadas para objetos de domínio.
- `matcher.py`: avalia exclusivamente `candidate + opportunity`.
- `config.py`: somente configuração operacional.
- `storage/` e `supabase/`: persistência identificada por candidato.

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
