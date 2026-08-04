# config.py
"""
CONFIGURAÇÃO CENTRAL DO AUTOMATCH
Define perfil do usuário, pesos do algoritmo e settings
"""


class Config:
    # SEU PERFIL TECH (baseado no CV real — automação, backend, QA/suporte)
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

    # PESOS DO ALGORITMO DE MATCHING
    SKILL_WEIGHTS = {
        'python': 0.22, 'automation': 0.15, 'selenium': 0.12,
        'apis': 0.10, 'backend': 0.10, 'qa': 0.10,
        'pandas': 0.08, 'aws': 0.06, 'git': 0.04, 'cicd': 0.03
    }

    # CONFIG NOTION
    NOTION_DATABASE_NAME = "🎯 Vagas AutoMatch"

    # CONFIG SCRAPING
    # linkedin e github(jobs.github.com) foram removidos: o primeiro era mock,
    # o segundo é uma API descontinuada desde 2018. Ver ARQUITETURA_E_ROADMAP.md §4.
    PLATAFORMAS_VAGAS = ['remoteok', 'arbeitnow', 'nerdin']