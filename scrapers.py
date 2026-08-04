# scrapers.py
"""
SISTEMA DE BUSCA DE VAGAS
Coleta vagas reais de plataformas com API pública, sem necessidade de chave.

Fontes ativas:
- RemoteOK (https://remoteok.com/api) — vagas remotas, JSON público
- Arbeitnow (https://arbeitnow.com/api/job-board-api) — vagas remotas/EU, JSON público

Fontes removidas nesta versão (ver ARQUITETURA_E_ROADMAP.md §4):
- LinkedIn "simplificado" era um mock hardcoded, não busca real.
- GitHub Jobs (jobs.github.com) foi descontinuado pelo GitHub em 2018;
  o endpoint não existe mais.
"""

import requests
import time


class VagasScraper:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "User-Agent": "AutoMatchCareer/1.0 (+https://github.com/perdidonasideia/automatch-career)"
        }

    def buscar_vagas_remoteok(self):
        """
        BUSCA VAGAS NO REMOTEOK
        API pública, sem autenticação. Retorna as vagas mais recentes;
        o filtro por relevância acontece depois, no matcher.
        """
        print("🔍 Buscando vagas no RemoteOK...")

        try:
            response = requests.get(
                "https://remoteok.com/api",
                headers=self.headers,
                timeout=15
            )

            if response.status_code != 200:
                print(f"⚠️  RemoteOK respondeu {response.status_code}")
                return []

            dados = response.json()

            # O primeiro item da resposta é sempre um aviso legal da API, não uma vaga
            vagas_raw = [item for item in dados if item.get("id")]

            vagas_formatadas = []
            for vaga in vagas_raw:
                vagas_formatadas.append({
                    "title": vaga.get("position", ""),
                    "company": vaga.get("company", ""),
                    "description": vaga.get("description", "") or vaga.get("position", ""),
                    "url": vaga.get("url", "") or vaga.get("apply_url", ""),
                    "platform": "remoteok",
                    "date_posted": vaga.get("date", ""),
                    "tags": vaga.get("tags", [])
                })

            print(f"✅ {len(vagas_formatadas)} vagas brutas do RemoteOK")
            return vagas_formatadas

        except requests.exceptions.RequestException as e:
            print(f"⚠️  Erro de rede no RemoteOK: {e}")
        except ValueError as e:
            print(f"⚠️  Erro ao decodificar resposta do RemoteOK: {e}")

        return []

    def buscar_vagas_arbeitnow(self):
        """
        BUSCA VAGAS NO ARBEITNOW
        API pública, sem autenticação, paginada. Busca só a primeira página
        (suficiente para o volume semanal do pipeline).
        """
        print("🔍 Buscando vagas no Arbeitnow...")

        try:
            response = requests.get(
                "https://arbeitnow.com/api/job-board-api",
                headers=self.headers,
                timeout=15
            )

            if response.status_code != 200:
                print(f"⚠️  Arbeitnow respondeu {response.status_code}")
                return []

            dados = response.json()
            vagas_raw = dados.get("data", [])

            vagas_formatadas = []
            for vaga in vagas_raw:
                vagas_formatadas.append({
                    "title": vaga.get("title", ""),
                    "company": vaga.get("company_name", ""),
                    "description": vaga.get("description", ""),
                    "url": vaga.get("url", ""),
                    "platform": "arbeitnow",
                    "date_posted": str(vaga.get("created_at", "")),
                    "tags": vaga.get("tags", [])
                })

            print(f"✅ {len(vagas_formatadas)} vagas brutas do Arbeitnow")
            return vagas_formatadas

        except requests.exceptions.RequestException as e:
            print(f"⚠️  Erro de rede no Arbeitnow: {e}")
        except ValueError as e:
            print(f"⚠️  Erro ao decodificar resposta do Arbeitnow: {e}")

        return []

    def _filtrar_por_keywords(self, vagas):
        """
        FILTRO INICIAL POR KEYWORDS DO PERFIL
        Reduz o volume antes de passar pro matcher, que faz o scoring fino.
        Evita processar centenas de vagas irrelevantes (ex: limpeza, vendas)
        que as APIs devolvem misturadas com vagas tech.
        """
        keywords = self.config.MEU_PERFIL["keywords_vagas"]
        skills = self.config.MEU_PERFIL["skills"]
        termos = [k.lower() for k in keywords] + [s.lower().replace("_", " ") for s in skills]

        vagas_filtradas = []
        for vaga in vagas:
            texto = f"{vaga['title']} {vaga['description']} {' '.join(vaga.get('tags', []))}".lower()
            if any(termo in texto for termo in termos):
                vagas_filtradas.append(vaga)

        return vagas_filtradas

    def buscar_todas_vagas(self):
        """
        EXECUTA TODOS OS SCRAPERS
        Retorna lista consolidada e pré-filtrada de vagas.
        """
        print("🚀 Iniciando busca por vagas...")

        todas_vagas = []

        todas_vagas.extend(self.buscar_vagas_remoteok())
        time.sleep(0.5)  # gentileza com as APIs públicas, evita rate limit
        todas_vagas.extend(self.buscar_vagas_arbeitnow())

        vagas_relevantes = self._filtrar_por_keywords(todas_vagas)

        print(f"📊 Total bruto: {len(todas_vagas)} | Após filtro de keywords: {len(vagas_relevantes)}")
        return vagas_relevantes