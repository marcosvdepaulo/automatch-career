# matcher.py
"""
ALGORITMO DE MATCHING INTELIGENTE
Calcula compatibilidade entre vagas e seu perfil
"""


class CareerMatcher:
    def __init__(self, config):
        self.config = config
        self.skills_weights = config.SKILL_WEIGHTS

    def calculate_match(self, job_description, job_title):
        """Calcula score de compatibilidade 0-100%"""

        texto_vaga = f"{job_title} {job_description}".lower()
        meu_perfil = self.config.MEU_PERFIL

        score = 0
        matches_encontrados = []

        # VERIFICA SKILLS
        for skill, weight in self.skills_weights.items():
            if self._skill_present(skill, texto_vaga):
                score += weight
                matches_encontrados.append(skill)

        # BÔNUS POR KEYWORDS ESPECÍFICAS
        bonus_keywords = 0
        for keyword in meu_perfil['keywords_vagas']:
            if keyword in texto_vaga:
                bonus_keywords += 0.05

        score = min(score + bonus_keywords, 1.0)  # Limita a 100%

        return {
            'score': round(score * 100, 1),
            'matches': matches_encontrados,
            'level': self._classificar_nivel(score)
        }

    def _skill_present(self, skill, texto):
        """Verifica se skill está presente no texto da vaga"""
        variations = {
            'python': ['python', 'python3', 'python 3'],
            'automation': ['automation', 'automação', 'automacao', 'rpa'],
            'selenium': ['selenium', 'webdriver', 'browser automation'],
            'apis': ['api', 'apis', 'rest api', 'restful', 'rest'],
            'backend': ['backend', 'back-end', 'back end'],
            'qa': ['qa', 'quality assurance', 'test automation', 'testes automatizados',
                   'software testing', 'uat', 'testes de software'],
            'pandas': ['pandas', 'etl', 'data pipeline', 'data engineering'],
            'aws': ['aws', 'amazon web services', 's3', 'boto3', 'cloud'],
            'git': ['git', 'github', 'gitlab'],
            'cicd': ['ci/cd', 'cicd', 'continuous integration', 'github actions', 'jenkins', 'devops']
        }

        skill_variations = variations.get(skill, [skill])
        return any(var in texto for var in skill_variations)

    def _classificar_nivel(self, score):
        """Classifica o nível de compatibilidade"""
        if score >= 0.7:
            return "💚 Alta"
        elif score >= 0.4:
            return "💛 Média"
        else:
            return "💔 Baixa"