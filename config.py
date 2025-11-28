# config.py
"""
CONFIGURAÇÃO CENTRAL DO AUTOMATCH
Define perfil do usuário, pesos do algoritmo e settings
"""

class Config:
    # SEU PERFIL TECH (customize aqui)
    MEU_PERFIL = {
        'skills': [
            'python', 'ai', 'machine_learning', 'sql', 'apis', 
            'fastapi', 'llms', 'rag', 'vector_databases', 'prompt_engineering',
            'langchain', 'openai', 'git', 'docker'
        ],
        'keywords_vagas': [
            'prompt engineer', 'ai engineer', 'python developer',
            'machine learning', 'llm', 'generative ai', 'ai developer',
            'python backend', 'fastapi', 'langchain'
        ],
        'nivel_experiencia': 2,  # anos
        'localizacao': 'remoto',
        'tipo_vaga': ['clt', 'pj']
    }
    
    # PESOS DO ALGORITMO DE MATCHING
    SKILL_WEIGHTS = {
        'python': 0.18, 'ai': 0.15, 'machine_learning': 0.12,
        'llm': 0.12, 'prompt_engineering': 0.10, 'generative_ai': 0.10,
        'sql': 0.08, 'apis': 0.07, 'fastapi': 0.05,
        'langchain': 0.03
    }
    
    # CONFIG NOTION
    NOTION_DATABASE_NAME = "🎯 Vagas AutoMatch"
    
    # CONFIG SCRAPING
    PLATAFORMAS_VAGAS = ['linkedin', 'github', 'programathor']
