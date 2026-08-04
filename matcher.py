# matcher.py
"""
ALGORITMO DE MATCHING INTELIGENTE
Calcula compatibilidade entre vagas e seu perfil

MUDANÇA (v2): título e descrição não têm mais o mesmo peso. Uma skill
aparecer no TÍTULO da vaga é sinal forte de que a vaga É sobre aquilo
(ex: "Solutions Architect" no título). Aparecer só na descrição é sinal
mais fraco (ex: vaga de "Data Analytics Engineer" que menciona Python
de passagem nos requisitos). Antes os dois pesavam igual, concatenados
no mesmo texto — o que fazia vagas de outra área subirem no ranking só
por compartilharem stack técnica genérica (Python, SQL, APIs) com o
perfil, mesmo sendo um cargo bem diferente.
"""


class CareerMatcher:
    def __init__(self, config):
        self.config = config
        self.skills_weights = config.SKILL_WEIGHTS

    def calculate_match(self, job_description, job_title):
        """Calcula score de compatibilidade 0-100%"""

        titulo = (job_title or "").lower()
        descricao = (job_description or "").lower()
        meu_perfil = self.config.MEU_PERFIL

        score = 0
        matches_encontrados = []

        # VERIFICA SKILLS — peso cheio se aparece no título, metade se só na descrição
        for skill, weight in self.skills_weights.items():
            no_titulo = self._skill_present(skill, titulo)
            na_descricao = self._skill_present(skill, descricao)

            if no_titulo:
                score += weight
                matches_encontrados.append(skill)
            elif na_descricao:
                score += weight * 0.5
                matches_encontrados.append(skill)

        # BÔNUS POR KEYWORDS ESPECÍFICAS — mesmo princípio: título > descrição
        bonus_keywords = 0
        for keyword in meu_perfil['keywords_vagas']:
            keyword = keyword.lower()
            if keyword in titulo:
                bonus_keywords += 0.08
            elif keyword in descricao:
                bonus_keywords += 0.03

        score = min(score + bonus_keywords, 1.0)  # Limita a 100%

        return {
            'score': round(score * 100, 1),
            'matches': matches_encontrados,
            'level': self._classificar_nivel(score)
        }

    def _skill_present(self, skill, texto):
        """Verifica se skill está presente no texto (título ou descrição)"""
        variations = self.config.SKILL_VARIATIONS.get(skill, [skill])
        return any(var in texto for var in variations)

    def _classificar_nivel(self, score):
        """Classifica o nível de compatibilidade"""
        if score >= 0.7:
            return "💚 Alta"
        elif score >= 0.4:
            return "💛 Média"
        else:
            return "💔 Baixa"