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

            # Força UTF-8: sem isso, requests pode decodificar como Latin-1
            # quando o Content-Type da resposta não declara charset, corrompendo
            # títulos com emoji/acentos (ex: "AllatÃ¡" em vez do texto correto)
            response.encoding = "utf-8"
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

            response.encoding = "utf-8"
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

    def buscar_vagas_nerdin(self):
        """
        BUSCA VAGAS NO NERDIN
        Sem API pública — faz parsing do HTML. O Nerdin já tem páginas
        pré-filtradas por tecnologia (ex: /vagas-python.php), o que reduz
        volume e evita ter que paginar centenas de vagas irrelevantes.

        AVISO: scraping de HTML é mais frágil que API JSON — se o Nerdin
        mudar o layout do site, esse método pode parar de encontrar vagas
        (vai simplesmente retornar lista vazia, não vai quebrar o pipeline).
        """
        print("🔍 Buscando vagas no Nerdin...")

        paginas_filtradas = [
            "https://www.nerdin.com.br/vagas-python.php",
            "https://www.nerdin.com.br/vagas.php?Especialidade=automa%C3%A7%C3%A3o",
            "https://www.nerdin.com.br/vagas.php?Especialidade=back+end",
        ]

        vagas_formatadas = []
        vistas = set()

        for url in paginas_filtradas:
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    print(f"⚠️  Nerdin ({url}) respondeu {response.status_code}")
                    continue

                response.encoding = "utf-8"

                try:
                    from bs4 import BeautifulSoup
                except ImportError:
                    print("⚠️  beautifulsoup4 não instalado — rode: pip install -r requirements.txt")
                    return []

                soup = BeautifulSoup(response.text, "html.parser")

                # Cada vaga tem um link pra página de detalhe nesse padrão de URL,
                # é o sinal mais estável que encontramos na estrutura do site.
                links_vaga = soup.find_all("a", href=lambda h: h and "/vaga_emprego/vaga-" in h)

                for link in links_vaga:
                    href = link.get("href", "")
                    if href in vistas:
                        continue
                    vistas.add(href)

                    url_completa = href if href.startswith("http") else f"https://www.nerdin.com.br{href}"

                    # Sobe até um container pai razoável pra pegar título + contexto
                    # (empresa, local, tags) como um bloco de texto só.
                    container = link
                    for _ in range(4):
                        if container.parent:
                            container = container.parent
                        if container.get_text(strip=True) and len(container.get_text(strip=True)) > 40:
                            break

                    texto_bloco = container.get_text(separator=" ", strip=True)
                    titulo = link.get_text(strip=True) or texto_bloco[:80]

                    if not titulo:
                        continue

                    vagas_formatadas.append({
                        "title": titulo,
                        "company": "",  # não isolamos com confiança sem ver o HTML real
                        "description": texto_bloco,
                        "url": url_completa,
                        "platform": "nerdin",
                        "date_posted": "",
                        "tags": []
                    })

            except requests.exceptions.RequestException as e:
                print(f"⚠️  Erro de rede no Nerdin ({url}): {e}")
            except Exception as e:
                print(f"⚠️  Erro inesperado no Nerdin ({url}): {e}")

        print(f"✅ {len(vagas_formatadas)} vagas brutas do Nerdin")
        return vagas_formatadas

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
        time.sleep(0.5)
        todas_vagas.extend(self.buscar_vagas_nerdin())

        vagas_relevantes = self._filtrar_por_keywords(todas_vagas)

        print(f"📊 Total bruto: {len(todas_vagas)} | Após filtro de keywords: {len(vagas_relevantes)}")
        return vagas_relevantes