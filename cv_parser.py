# cv_parser.py
"""
GERADOR DE PERFIL A PARTIR DE CURRÍCULO EM PDF
Lê um PDF, identifica quais skills do vocabulário mestre (config.py)
aparecem no texto, e gera um MEU_PERFIL + SKILL_WEIGHTS dinamicamente —
sem precisar editar config.py à mão toda vez que o currículo mudar.

Estratégia de pesos: cada skill encontrada recebe peso igual, dividindo
100% entre todas. É simples e transparente — um currículo mais enxuto
(menos skills) gera pesos mais concentrados; um currículo mais amplo
espalha o peso. Ajuste manual em SKILL_WEIGHTS ainda é possível depois,
se quiser priorizar alguma skill específica.
"""

import re

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# Frases naturais de vaga por skill, usadas pra gerar keywords_vagas
# automaticamente a partir das skills encontradas no currículo.
FRASES_POR_SKILL = {
    'python': 'python developer',
    'javascript': 'javascript developer',
    'typescript': 'typescript developer',
    'automation': 'automation engineer',
    'selenium': 'qa automation',
    'playwright': 'test automation',
    'apis': 'backend developer',
    'backend': 'backend developer',
    'frontend': 'frontend developer',
    'qa': 'qa engineer',
    'pandas': 'data engineer',
    'sql': 'sql developer',
    'aws': 'cloud engineer',
    'azure': 'cloud engineer',
    'git': 'software developer',
    'cicd': 'devops engineer',
    'docker': 'devops engineer',
    'servicenow': 'itsm analyst',
    'itil': 'it support analyst',
    'agile': 'scrum',
}


def extrair_texto_pdf(caminho_pdf):
    """Extrai todo o texto de um PDF, página por página."""
    if pdfplumber is None:
        raise ImportError(
            "pdfplumber não está instalado. Rode: pip install -r requirements.txt"
        )

    texto_completo = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text() or ""
            texto_completo.append(texto_pagina)

    return "\n".join(texto_completo)


def identificar_skills(texto, skill_variations):
    """
    Verifica quais skills do vocabulário mestre aparecem no texto.
    Retorna lista de skill_keys encontrados (ex: ['python', 'aws', 'git']).
    """
    texto_lower = texto.lower()
    skills_encontradas = []

    for skill_key, variacoes in skill_variations.items():
        if any(variacao in texto_lower for variacao in variacoes):
            skills_encontradas.append(skill_key)

    return skills_encontradas


def extrair_anos_experiencia(texto):
    """
    Tenta achar um padrão tipo '4 anos', '4+ anos', '4 years' no texto.
    Best-effort: se não achar nada confiável, retorna None (quem chama
    decide o fallback).
    """
    padroes = [
        r'(\d{1,2})\+?\s*anos',
        r'(\d{1,2})\+?\s*years',
    ]
    for padrao in padroes:
        match = re.search(padrao, texto.lower())
        if match:
            return int(match.group(1))
    return None


def gerar_perfil_do_cv(caminho_pdf, config):
    """
    Função principal: lê o PDF e devolve (meu_perfil, skill_weights)
    prontos pra substituir os valores estáticos do Config.

    Se o PDF não puder ser lido ou nenhuma skill for encontrada, levanta
    exceção — quem chama (main.py) decide se cai pro perfil padrão do
    config.py ou aborta.
    """
    texto = extrair_texto_pdf(caminho_pdf)

    if not texto.strip():
        raise ValueError(
            f"Não foi possível extrair texto de '{caminho_pdf}'. "
            "O PDF pode ser uma imagem escaneada (sem texto selecionável)."
        )

    skills_encontradas = identificar_skills(texto, config.SKILL_VARIATIONS)

    if not skills_encontradas:
        raise ValueError(
            f"Nenhuma skill do vocabulário conhecido foi encontrada em '{caminho_pdf}'. "
            "Verifique se o PDF tem texto selecionável, ou adicione as skills "
            "que faltam em Config.SKILL_VARIATIONS."
        )

    # Peso igual pra cada skill encontrada, somando 1.0
    peso_por_skill = round(1.0 / len(skills_encontradas), 4)
    skill_weights = {skill: peso_por_skill for skill in skills_encontradas}

    # Keywords de vaga: frase natural por skill encontrada (sem duplicar)
    keywords_vagas = list(dict.fromkeys(
        FRASES_POR_SKILL.get(skill, skill) for skill in skills_encontradas
    ))

    anos = extrair_anos_experiencia(texto)

    meu_perfil = {
        'skills': skills_encontradas,
        'keywords_vagas': keywords_vagas,
        'nivel_experiencia': anos if anos is not None else config.MEU_PERFIL['nivel_experiencia'],
        'localizacao': config.MEU_PERFIL['localizacao'],
        'tipo_vaga': config.MEU_PERFIL['tipo_vaga'],
    }

    return meu_perfil, skill_weights