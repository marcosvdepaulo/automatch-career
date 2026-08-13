# scrapers.py
"""
SISTEMA DE BUSCA DE VAGAS
Coleta vagas reais de plataformas com API pública, sem necessidade de chave.

Fontes ativas:
- RemoteOK (https://remoteok.com/api) — vagas remotas, JSON público
- Arbeitnow (https://arbeitnow.com/api/job-board-api) — vagas remotas/EU, JSON público
- We Work Remotely (RSS) — vagas remotas, XML padronizado

Fontes removidas:
- Nerdin: scraping de HTML puro, sem API. Frágil e lento demais pro
  caminho de resposta ao vivo do endpoint web. Ver AUTOMATCH_ARQUITETURA_E_ROADMAP.md.
- LinkedIn "simplificado" era um mock hardcoded, não busca real.
- GitHub Jobs (jobs.github.com) foi descontinuado pelo GitHub em 2018.

Mudança em relação à versão do pipeline cron: as buscas rodam em PARALELO
(ThreadPoolExecutor) e sem time.sleep() entre chamadas. Isso é essencial
pro uso em função serverless (Vercel), que tem orçamento de tempo apertado
e responde a um usuário esperando na tela — não faz sentido ser "gentil"
com delay sequencial num request síncrono. Pra uso no cron semanal
(main.py) o comportamento é idêntico, só mais rápido.
"""

import concurrent.futures
import re

import requests


class VagasScraper:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "User-Agent": "AutoMatchCareer/1.0 (+https://github.com/marcosvdepaulo/automatch-career)"
        }
        # Timeout curto por fonte — numa função serverless o orçamento de
        # tempo total é o que importa, não vale a pena deixar uma fonte
        # lenta seguntar as outras.
        self.timeout = 8

    def buscar_vagas_remoteok(self):
        """BUSCA VAGAS NO REMOTEOK — API pública, sem autenticação."""
        try:
            response = requests.get(
                "https://remoteok.com/api",
                headers=self.headers,
                timeout=self.timeout
            )
            if response.status_code != 200:
                print(f"⚠️ RemoteOK respondeu {response.status_code}")
                return []

            response.encoding = "utf-8"
            dados = response.json()

            # O primeiro item da resposta é sempre um aviso legal da API
            vagas_raw = [item for item in dados if item.get("id")]

            vagas_formatadas = []
            for vaga in vagas_raw:
                vagas_formatadas.append({
                    "external_id": str(vaga.get("id")) if vaga.get("id") is not None else None,
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
            print(f"⚠️ Erro de rede no RemoteOK: {e}")
        except ValueError as e:
            print(f"⚠️ Erro ao decodificar resposta do RemoteOK: {e}")
        return []

    def buscar_vagas_arbeitnow(self):
        """BUSCA VAGAS NO ARBEITNOW — API pública, sem autenticação, paginada."""
        try:
            response = requests.get(
                "https://arbeitnow.com/api/job-board-api",
                headers=self.headers,
                timeout=self.timeout
            )
            if response.status_code != 200:
                print(f"⚠️ Arbeitnow respondeu {response.status_code}")
                return []

            response.encoding = "utf-8"
            dados = response.json()
            vagas_raw = dados.get("data", [])

            vagas_formatadas = []
            for vaga in vagas_raw:
                vagas_formatadas.append({
                    "external_id": str(vaga.get("slug")) if vaga.get("slug") else None,
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
            print(f"⚠️ Erro de rede no Arbeitnow: {e}")
        except ValueError as e:
            print(f"⚠️ Erro ao decodificar resposta do Arbeitnow: {e}")
        return []

    def buscar_vagas_weworkremotely(self):
        """BUSCA VAGAS NO WE WORK REMOTELY (via RSS) — formato XML padronizado."""
        feeds = [
            "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        ]

        vagas_formatadas = []
        for feed_url in feeds:
            try:
                response = requests.get(feed_url, headers=self.headers, timeout=self.timeout)
                if response.status_code != 200:
                    print(f"⚠️ We Work Remotely ({feed_url}) respondeu {response.status_code}")
                    continue

                response.encoding = "utf-8"
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)

                for item in root.findall(".//item"):
                    titulo = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    descricao_raw = item.findtext("description") or ""
                    data_pub = (item.findtext("pubDate") or "").strip()
                    external_id = (item.findtext("guid") or "").strip() or None

                    descricao_limpa = re.sub(r"<[^>]+>", " ", descricao_raw)
                    descricao_limpa = re.sub(r"\s+", " ", descricao_limpa).strip()

                    if not titulo:
                        continue

                    empresa, cargo = self._separar_titulo_wwr(titulo)
                    descricao_limpa = self._remover_mencoes_da_empresa(descricao_limpa, empresa)

                    vagas_formatadas.append({
                        "external_id": external_id,
                        "title": cargo,
                        "company": empresa,
                        "description": descricao_limpa[:2000],
                        "url": link,
                        "platform": "weworkremotely",
                        "date_posted": data_pub,
                        "tags": []
                    })

            except requests.exceptions.RequestException as e:
                print(f"⚠️ Erro de rede no We Work Remotely ({feed_url}): {e}")
            except ET.ParseError as e:
                print(f"⚠️ Erro ao interpretar XML do We Work Remotely ({feed_url}): {e}")

        print(f"✅ {len(vagas_formatadas)} vagas brutas do We Work Remotely")
        return vagas_formatadas

    @staticmethod
    def _separar_titulo_wwr(titulo):
        """Normalize WWR's ``Company: Job title`` feed representation."""
        if ":" not in titulo:
            return "", titulo.strip()
        empresa, cargo = titulo.split(":", 1)
        return empresa.strip(), cargo.strip()

    @staticmethod
    def _remover_mencoes_da_empresa(descricao, empresa):
        """Prevent WWR company branding/metadata from becoming skill evidence."""
        if not empresa:
            return descricao
        pattern = r"(?<!\w)" + re.escape(empresa) + r"(?!\w)"
        return re.sub(pattern, " ", descricao, flags=re.IGNORECASE)

    def _filtrar_por_keywords(self, vagas):
        """
        FILTRO INICIAL POR KEYWORDS DO PERFIL
        Reduz o volume antes de passar pro matcher, que faz o scoring fino.
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
        EXECUTA TODOS OS SCRAPERS EM PARALELO
        Retorna lista consolidada e pré-filtrada de vagas.
        """
        print("🚀 Iniciando busca por vagas (paralelo)...")

        fontes = [
            self.buscar_vagas_remoteok,
            self.buscar_vagas_arbeitnow,
            self.buscar_vagas_weworkremotely,
        ]

        todas_vagas = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(fontes)) as executor:
            futuros = [executor.submit(fonte) for fonte in fontes]
            for futuro in concurrent.futures.as_completed(futuros, timeout=self.timeout + 5):
                try:
                    todas_vagas.extend(futuro.result())
                except Exception as e:
                    print(f"⚠️ Uma fonte falhou: {e}")

        vagas_relevantes = self._filtrar_por_keywords(todas_vagas)
        print(f"📊 Total bruto: {len(todas_vagas)} | Após filtro de keywords: {len(vagas_relevantes)}")
        return vagas_relevantes
