# scrapers.py
"""
SISTEMA DE BUSCA DE VAGAS
Coleta vagas de múltiplas plataformas usando APIs e scraping
"""

import requests
import time
from datetime import datetime

class VagasScraper:
    def __init__(self, config):
        self.config = config
        
    def buscar_vagas_linkedin_simplificado(self):
        """
        BUSCA SIMPLIFICADA NO LINKEDIN
        Versão inicial usando busca por keywords
        Retorna vagas de exemplo para MVP
        """
        
        print("🔍 Buscando vagas no LinkedIn...")
        
        # VAGAS EXEMPLO BASEADAS NO SEU PERFIL (MVP)
        vagas_exemplo = [
            {
                'title': 'Prompt Engineer',
                'company': 'Tech AI Startup',
                'description': 'Busca-se engenheiro de prompt com experiência em Python, LLMs, OpenAI e LangChain. Conhecimento em RAG e vector databases.',
                'url': 'https://linkedin.com/jobs/view/123',
                'platform': 'linkedin',
                'date_posted': datetime.now().strftime('%Y-%m-%d')
            },
            {
                'title': 'AI Developer', 
                'company': 'Data Science Corp',
                'description': 'Vaga para desenvolvedor AI com Python, machine learning, APIs e SQL. Experiência em modelos generativos.',
                'url': 'https://linkedin.com/jobs/view/124',
                'platform': 'linkedin',
                'date_posted': datetime.now().strftime('%Y-%m-%d')
            },
            {
                'title': 'Python Backend Engineer',
                'company': 'API Company',
                'description': 'Desenvolvedor Python com FastAPI, Docker, AWS. Conhecimento em LLMs e integrações é um plus.',
                'url': 'https://linkedin.com/jobs/view/125',
                'platform': 'linkedin', 
                'date_posted': datetime.now().strftime('%Y-%m-%d')
            },
            {
                'title': 'Machine Learning Engineer',
                'company': 'AI Research Lab',
                'description': 'Engenheiro de machine learning com Python, TensorFlow, PyTorch. Experiência em NLP e LLMs.',
                'url': 'https://linkedin.com/jobs/view/126',
                'platform': 'linkedin',
                'date_posted': datetime.now().strftime('%Y-%m-%d')
            }
        ]
        
        # FILTRAR POR KEYWORDS DO SEU PERFIL
        keywords = self.config.MEU_PERFIL['keywords_vagas']
        vagas_filtradas = []
        
        for vaga in vagas_exemplo:
            texto_vaga = f"{vaga['title']} {vaga['description']}".lower()
            if any(keyword in texto_vaga for keyword in keywords):
                vagas_filtradas.append(vaga)
        
        print(f"✅ Encontradas {len(vagas_filtradas)} vagas relevantes")
        return vagas_filtradas
    
    def buscar_vagas_github(self):
        """
        BUSCA VAGAS NO GITHUB JOBS
        Usa API pública do GitHub Jobs
        """
        print("🔍 Buscando vagas no GitHub Jobs...")
        
        try:
            response = requests.get(
                'https://jobs.github.com/positions.json',
                params={
                    'description': 'python',
                    'location': 'remote'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                vagas = response.json()
                vagas_formatadas = []
                
                for vaga in vagas[:5]:  # Limita a 5 vagas
                    vagas_formatadas.append({
                        'title': vaga.get('title', ''),
                        'company': vaga.get('company', ''),
                        'description': vaga.get('description', ''),
                        'url': vaga.get('url', ''),
                        'platform': 'github',
                        'date_posted': vaga.get('created_at', '')
                    })
                
                print(f"✅ {len(vagas_formatadas)} vagas do GitHub")
                return vagas_formatadas
                
        except Exception as e:
            print(f"⚠️  Erro no GitHub Jobs: {e}")
        
        return []
    
    def buscar_todas_vagas(self):
        """
        EXECUTA TODOS OS SCRAPERS
        Retorna lista consolidada de vagas
        """
        print("🚀 Iniciando busca por vagas...")
        
        todas_vagas = []
        
        # LinkedIn (MVP com dados exemplo)
        vagas_linkedin = self.buscar_vagas_linkedin_simplificado()
        todas_vagas.extend(vagas_linkedin)
        
        # GitHub Jobs
        vagas_github = self.buscar_vagas_github() 
        todas_vagas.extend(vagas_github)
        
        print(f"📊 Total: {len(todas_vagas)} vagas encontradas")
        return todas_vagas
