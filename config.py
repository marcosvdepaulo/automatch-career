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
    #
    # ATUALIZAÇÃO: expandido com vocabulário moderno de DevOps/SRE/Cloud
    # depois de um teste real mostrar que vagas pedindo Kubernetes, Terraform,
    # observabilidade e FinOps zeravam nesses termos porque não existiam
    # aqui — mesmo currículos de DevOps sênior bem escritos ficavam com
    # score baixo, não por falta de fit real, mas por lacuna de dicionário.
    SKILL_VARIATIONS = {
        'python': ['python', 'python3', 'python 3'],
        'javascript': ['javascript', 'js', 'ecmascript'],
        'typescript': ['typescript', 'ts'],
        'go': ['golang', ' go ', 'go lang'],
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
        'gcp': ['gcp', 'google cloud', 'google cloud platform', 'bigquery'],
        'git': ['git', 'github', 'gitlab'],
        'cicd': ['ci/cd', 'cicd', 'continuous integration', 'github actions', 'jenkins', 'devops'],
        'docker': ['docker', 'container', 'containerização'],
        'kubernetes': ['kubernetes', 'k8s', 'kubectl'],
        'terraform': ['terraform', 'infrastructure as code', 'infraestrutura como código', 'iac'],
        'argocd': ['argocd', 'argo cd', 'gitops'],
        'helm': ['helm', 'helm chart', 'helm charts'],
        'observabilidade': ['observability', 'observabilidade', 'prometheus', 'grafana',
                             'datadog', 'monitoring', 'monitoramento'],
        'finops': ['finops', 'cost optimization', 'otimização de custo', 'cloud cost',
                    'cost management', 'chargeback', 'showback'],
        'sre': ['sre', 'site reliability', 'reliability engineering', 'slo', 'sla', 'on-call', 'oncall'],
        'servicenow': ['servicenow', 'cmdb', 'itsm'],
        'itil': ['itil', 'change management', 'gestão de mudanças'],
        'agile': ['agile', 'scrum', 'kanban', 'ágil'],
    }

    # PDF de currículo — se o arquivo existir nesse caminho, o main.py
    # gera o perfil e os pesos dinamicamente a partir dele (ver cv_parser.py).
    # Pode ser sobrescrito via variável de ambiente CV_PDF_PATH no .env.
    import os as _os
    CV_PDF_PATH = _os.getenv('CV_PDF_PATH', 'curriculo.pdf')
    CV_VERSION = _os.getenv('CV_VERSION')

    # CONFIG NOTION
    NOTION_DATABASE_NAME = "🎯 Vagas AutoMatch"

    # CONFIG SCRAPING
    PLATAFORMAS_VAGAS = ['remoteok', 'arbeitnow', 'weworkremotely']


# Structured profile data is preferred, while these class values remain the
# safe legacy fallback. Existing vocabulary entries are merged so CV parsing
# and callers that depend on the broader historical dictionary keep working.
from copy import deepcopy as _deepcopy
from profile_loader import load_profile_config as _load_profile_config

_LEGACY_CONFIG = {
    'MEU_PERFIL': _deepcopy(Config.MEU_PERFIL),
    'SKILL_WEIGHTS': _deepcopy(Config.SKILL_WEIGHTS),
    'SKILL_VARIATIONS': _deepcopy(Config.SKILL_VARIATIONS),
}
_PROFILE_CONFIG = _load_profile_config(fallback=_LEGACY_CONFIG)

if _PROFILE_CONFIG['loaded_from_files']:
    _merged_variations = _deepcopy(_LEGACY_CONFIG['SKILL_VARIATIONS'])
    _merged_variations.update(_PROFILE_CONFIG['SKILL_VARIATIONS'])
    Config.MEU_PERFIL = _PROFILE_CONFIG['MEU_PERFIL']
    Config.SKILL_WEIGHTS = _PROFILE_CONFIG['SKILL_WEIGHTS']
    Config.SKILL_VARIATIONS = _merged_variations
    Config.PROFESSIONAL_PROFILE = _PROFILE_CONFIG['PROFESSIONAL_PROFILE']
    Config.PROFILE_VERSION = _PROFILE_CONFIG['PROFESSIONAL_PROFILE'].get('profile_version', 'legacy-v1')
    Config.SKILLS_ONTOLOGY = _PROFILE_CONFIG['SKILLS_ONTOLOGY']
    Config.ROLE_FAMILIES = _PROFILE_CONFIG['ROLE_FAMILIES']
    Config.PROFILE_LOADED_FROM_FILES = True
else:
    Config.PROFILE_VERSION = 'legacy-v1'
    Config.PROFILE_LOADED_FROM_FILES = False
