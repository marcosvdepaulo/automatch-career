# notion_client.py
"""
CLIENTE NOTION COMO DATABASE
Gerencia todo o CRUD das vagas no Notion
"""

import requests
import os
from datetime import datetime

class NotionDB:
    def __init__(self):
        self.token = os.getenv('NOTION_TOKEN')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
    
    def testar_conexao(self):
        """Testa se a conexão com Notion está funcionando"""
        try:
            response = requests.get(
                f'https://api.notion.com/v1/databases/{self.database_id}',
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Erro de conexão Notion: {e}")
            return False
    
    def vaga_ja_existe(self, vaga_title, vaga_company):
        """Verifica se vaga já está salva para evitar duplicatas"""
        try:
            response = requests.post(
                f'https://api.notion.com/v1/databases/{self.database_id}/query',
                headers=self.headers,
                json={
                    "filter": {
                        "and": [
                            {"property": "Vaga", "title": {"equals": vaga_title}},
                            {"property": "Empresa", "rich_text": {"equals": vaga_company}}
                        ]
                    }
                }
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                return len(results) > 0
                
        except Exception as e:
            print(f"⚠️  Erro ao verificar vaga existente: {e}")
        
        return False
    
    def salvar_vaga(self, vaga_data):
        """Salva uma vaga no database do Notion"""
        
        # Verificar duplicata
        if self.vaga_ja_existe(vaga_data['title'], vaga_data['company']):
            print(f"⏭️  Vaga já existe: {vaga_data['title']} - {vaga_data['company']}")
            return False
        
        # Preparar propriedades
        properties = {
            "Vaga": {
                "title": [
                    {
                        "text": {
                            "content": vaga_data['title'][:100]  # Limite do Notion
                        }
                    }
                ]
            },
            "Empresa": {
                "rich_text": [
                    {
                        "text": {
                            "content": vaga_data['company'][:200]
                        }
                    }
                ]
            },
            "Compatibilidade": {
                "number": vaga_data['match_score']
            },
            "Status": {
                "select": {
                    "name": "💚 Para Aplicar"  # Status inicial
                }
            },
            "Data": {
                "date": {
                    "start": datetime.now().isoformat()
                }
            },
            "URL": {
                "url": vaga_data.get('url', '')
            },
            "Skills": {
                "rich_text": [
                    {
                        "text": {
                            "content": ", ".join(vaga_data.get('match_details', {}).get('matches', []))
                        }
                    }
                ]
            },
            "Match": {
                "rich_text": [
                    {
                        "text": {
                            "content": vaga_data.get('match_details', {}).get('level', '')
                        }
                    }
                ]
            },
            "Plataforma": {
                "rich_text": [
                    {
                        "text": {
                            "content": vaga_data.get('platform', '')
                        }
                    }
                ]
            }
        }
        
        try:
            response = requests.post(
                'https://api.notion.com/v1/pages',
                headers=self.headers,
                json={
                    'parent': {'database_id': self.database_id},
                    'properties': properties
                }
            )
            
            if response.status_code == 200:
                print(f"✅ Vaga salva: {vaga_data['title']} - {vaga_data['match_score']}%")
                return True
            else:
                print(f"❌ Erro ao salvar vaga: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return False
    
    def salvar_lote_vagas(self, vagas):
        """Salva múltiplas vagas no Notion"""
        print(f"💾 Salvando {len(vagas)} vagas no Notion...")
        
        salvas_com_sucesso = 0
        for vaga in vagas:
            if self.salvar_vaga(vaga):
                salvas_com_sucesso += 1
            time.sleep(0.5)  # Rate limiting
        
        print(f"🎉 {salvas_com_sucesso}/{len(vagas)} vagas salvas com sucesso")
        return salvas_com_sucesso
