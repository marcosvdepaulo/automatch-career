# config.py
"""
CONFIGURAÇÃO CENTRAL DO AUTOMATCH
Define perfil do usuário, pesos do algoritmo e settings
"""


class Config:
    # SEU PERFIL TECH — usado como padrão quando não há PDF de currículo
    # configurado (ver CV_PDF_PATH). Se houver PDF, este perfil é substituído
    # dinamicamente pelo que for extraído dele (ver cv_parser.py).
    MEU_PERFIL = {
        'skills': [
            'python', 'automation', 'selenium', 'apis', 'backend',
            'qa', 'pandas', 'aws', 'git', 'cicd'
        ],
        'keywords_vagas': [
            'python developer', 'backend developer', 'automation engineer',
            'qa automation', 'python backend', 'desenvolvedor python',
            'automação python', 'test automation', 'devops', 'analista de automação'
        ],
        'nivel_experiencia': 4,  # anos (CV real: 4+ anos em TI)
        'localizacao': 'remoto',
        'tipo_vaga': ['clt', 'pj']
    }

    # PESOS DO ALGORITMO DE MATCHING — usado como padrão quando não há PDF
    SKILL_WEIGHTS = {
        'python': 0.22, 'automation': 0.15, 'selenium': 0.12,
        'apis': 0.10, 'backend': 0.10, 'qa': 0.10,
        'pandas': 0.08, 'aws': 0.06, 'git': 0.04, 'cicd': 0.03
    }

    # VOCABULÁRIO MESTRE DE SKILLS + SINÔNIMOS
    # Fonte única usada tanto pelo matcher (pra achar skill no texto da vaga)
    # quanto pelo cv_parser (pra achar skill no texto do currículo em PDF).
    # Pode crescer sem quebrar nada — skills que não aparecerem nem na vaga
    # nem no currículo simplesmente não pontuam.
    SKILL_VARIATIONS = {
        'python': ['python', 'python3', 'python 3'],
        'javascript': ['javascript', 'js', 'ecmascript'],
        'typescript': ['typescript', 'ts'],
        'automation': ['automation', 'automação', 'automacao', 'rpa'],
        'selenium': ['selenium', 'webdriver', 'browser automation'],
        'playwright': ['playwright'],
        'apis': ['api', 'apis', 'rest api', 'restful', 'rest'],
        'backend': ['backend', 'back-end', 'back end'],
        'frontend': ['frontend', 'front-end', 'front end'],
        'qa': ['qa', 'quality assurance', 'test automation', 'testes automatizados',
               'software testing', 'uat', 'testes de software'],
        'pandas': ['pandas', 'etl', 'data pipeline', 'data engineering'],
        'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'banco de dados relacional'],
        'aws': ['aws', 'amazon web services', 's3', 'boto3'],
        'azure': ['azure', 'microsoft azure'],
        'git': ['git', 'github', 'gitlab'],
        'cicd': ['ci/cd', 'cicd', 'continuous integration', 'github actions', 'jenkins', 'devops'],
        'docker': ['docker', 'container', 'containerização'],
        'servicenow': ['servicenow', 'cmdb', 'itsm'],
        'itil': ['itil', 'change management', 'gestão de mudanças'],
        'agile': ['agile', 'scrum', 'kanban', 'ágil'],
    }

    # PDF de currículo — se o arquivo existir nesse caminho, o main.py
    # gera o perfil e os pesos dinamicamente a partir dele (ver cv_parser.py).
    # Pode ser sobrescrito via variável de ambiente CV_PDF_PATH no .env.
    import os as _os
    CV_PDF_PATH = _os.getenv('CV_PDF_PATH', 'curriculo.pdf')

    # CONFIG NOTION
    NOTION_DATABASE_NAME = "🎯 Vagas AutoMatch"

    # CONFIG SCRAPING
    # linkedin e github(jobs.github.com) foram removidos: o primeiro era mock,
    # o segundo é uma API descontinuada desde 2018. Ver ARQUITETURA_E_ROADMAP.md §4.
    PLATAFORMAS_VAGAS = ['remoteok', 'arbeitnow', 'nerdin', 'weworkremotely']