🎯 AutoMatch Career Platform

Sistema inteligente de descoberta de vagas tech com matching automático. Busca vagas baseadas no seu perfil e salva automaticamente no Notion.
🚀 Funcionalidades

    ✅ Busca Automática - Vagas de múltiplas plataformas (LinkedIn, GitHub Jobs)

    ✅ Matching Inteligente - Algoritmo de compatibilidade com seu perfil

    ✅ Notion Integration - Dashboard centralizado para gerenciar vagas

    ✅ Agendamento - Execução automática toda segunda-feira

    ✅ Filtro de Qualidade - Só salva vagas com bom match (>40%)

🛠️ Stack Tecnológica

    Python 3.11+ - Lógica principal

    Notion API - Database e interface

    GitHub Actions - Agendamento e execução

    Requests/BeautifulSoup - Scraping e APIs

⚡ Setup Rápido
1. Clone o repositório
bash

git clone https://github.com/perdidonasideia/automatch-career
cd automatch-career

2. Configure o ambiente Python
bash

python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

pip install -r requirements.txt

3. Configure o Notion
A. Crie uma Integration

    Acesse Notion Developers

    Clique em "+ New integration"

    Nome: "AutoMatch Career"

    Selecione o workspace

    Copie o Internal Integration Token

B. Crie o Database

    Crie uma nova página no Notion

    Adicione um bloco "/database - inline"

    Configure as colunas:

        Vaga (Title)

        Empresa (Text)

        Compatibilidade (Number)

        Status (Select)

        Data (Date)

        URL (URL)

        Skills (Text)

        Match (Text)

        Plataforma (Text)

C. Compartilhe o Database

    No database criado, clique em "Share"

    Convide sua integration "AutoMatch Career"

    Copie o Database ID da URL:
    https://www.notion.so/yourworkspace/{DATABASE_ID}?v=...

4. Configure as variáveis de ambiente
bash

cp .env.example .env
# Edite .env com suas credenciais:
NOTION_TOKEN=seu_token_aqui
NOTION_DATABASE_ID=seu_database_id_aqui

5. Teste localmente
bash

python main.py

6. Configure o GitHub Actions (Opcional)
A. Configure Secrets no GitHub

    No seu repositório: Settings → Secrets and variables → Actions

    Adicione:

        NOTION_TOKEN - seu token do Notion

        NOTION_DATABASE_ID - ID do seu database

B. O workflow rodará automaticamente toda segunda-feira às 9AM
🎯 Personalize Seu Perfil

Edite config.py para refletir seu perfil:
python

MEU_PERFIL = {
    'skills': ['python', 'ai', 'machine_learning', 'sql', 'apis', 'fastapi'],
    'keywords_vagas': ['prompt engineer', 'ai engineer', 'python developer'],
    'nivel_experiencia': 2,
    'localizacao': 'remoto'
}

SKILL_WEIGHTS = {
    'python': 0.18, 
    'ai': 0.15,
    'machine_learning': 0.12,
    # ... ajuste os pesos conforme sua preferência
}

📊 Estrutura do Projeto
text

automatch-career/
├── main.py                 # Pipeline principal
├── config.py               # Configurações e perfil
├── matcher.py              # Algoritmo de matching
├── scrapers.py             # Busca de vagas
├── notion_client.py        # Integração com Notion
├── requirements.txt        # Dependências
├── .github/workflows/      # GitHub Actions
└── README.md

🔄 Fluxo de Execução

    Busca - Coleta vagas das plataformas configuradas

    Matching - Calcula compatibilidade com seu perfil

    Filtro - Mantém apenas vagas com score > 40%

    Salvamento - Armazena no Notion com dados estruturados

    Relatório - Gera resumo da execução

🐛 Solução de Problemas
Erro de Autenticação Notion
bash

❌ Falha na conexão com Notion. Verifique NOTION_TOKEN e NOTION_DATABASE_ID

    Verifique se o token está correto

    Confirme se o database foi compartilhado com a integration

Nenhuma Vaga Encontrada

    Verifique suas keywords em config.py

    Teste manualmente a busca nas plataformas

Rate Limiting

    O sistema inclui delays entre requests

    GitHub Actions: máximo 1 execução por hora

🚧 Próximas Funcionalidades

    Scraping real do LinkedIn

    Mais plataformas (Programathor, Indeed)

    Notificações por email

    Dashboard de analytics

    Auto-aplicação para vagas

🤝 Contribuindo

    Fork o projeto

    Crie uma branch: git checkout -b feature/nova-funcionalidade

    Commit: git commit -m 'Add nova funcionalidade'

    Push: git push origin feature/nova-funcionalidade

    Abra um Pull Request

📄 Licença

MIT License - veja LICENSE para detalhes.

Desenvolvido por Marcos Vinicius
