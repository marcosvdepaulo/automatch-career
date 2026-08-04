# main.py
"""
PIPELINE PRINCIPAL DO AUTOMATCH
Orquestra todo o fluxo: busca → matching → salvamento
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Carrega o .env local (não tem efeito no GitHub Actions, que injeta os
# secrets direto como variável de ambiente — mas é essencial pra rodar local)
load_dotenv()

# Adiciona o diretório atual ao path para imports
sys.path.append(os.path.dirname(__file__))

from config import Config
from scrapers import VagasScraper
from matcher import CareerMatcher
from notion_client import NotionDB


class AutoMatchPipeline:
    def __init__(self):
        self.config = Config()
        self.scraper = VagasScraper(self.config)
        self.matcher = CareerMatcher(self.config)
        self.notion = NotionDB()

    def executar_pipeline_completo(self):
        """
        EXECUTA O PIPELINE COMPLETO
        1. Busca vagas → 2. Calcula matches → 3. Salva no Notion
        """
        print("=" * 50)
        print("🚀 INICIANDO AUTOMATCH PIPELINE")
        print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("=" * 50)

        # PASSO 1: Testar conexão com Notion
        print("\n1. 🔌 Testando conexão com Notion...")
        if not self.notion.testar_conexao():
            print("❌ Falha na conexão com Notion. Verifique NOTION_TOKEN e NOTION_DATABASE_ID")
            return False
        print("✅ Conexão com Notion OK!")

        # PASSO 2: Buscar vagas
        print("\n2. 🔍 Buscando vagas nas plataformas...")
        vagas_encontradas = self.scraper.buscar_todas_vagas()

        if not vagas_encontradas:
            print("❌ Nenhuma vaga encontrada")
            return False

        # PASSO 3: Calcular matches
        print("\n3. 🎯 Calculando compatibilidade...")
        vagas_com_match = self._calcular_matches(vagas_encontradas)

        if not vagas_com_match:
            print("❌ Nenhuma vaga com bom match encontrada")
            return False

        # PASSO 4: Salvar no Notion
        print("\n4. 💾 Salvando vagas no Notion...")
        vagas_salvas = self.notion.salvar_lote_vagas(vagas_com_match)

        # PASSO 5: Relatório final
        self._gerar_relatorio(vagas_encontradas, vagas_com_match, vagas_salvas)

        return True

    def _calcular_matches(self, vagas):
        """
        CALCULA MATCHES PARA TODAS AS VAGAS
        Filtra apenas vagas com compatibilidade > 40%
        """
        vagas_com_match = []

        for vaga in vagas:
            resultado_match = self.matcher.calculate_match(
                vaga['description'],
                vaga['title']
            )

            # Só inclui vagas com match relevante (>40%)
            if resultado_match['score'] >= 40:
                vaga['match_score'] = resultado_match['score']
                vaga['match_details'] = resultado_match
                vagas_com_match.append(vaga)

                print(f"   ✅ {vaga['title'][:30]}... - {resultado_match['score']}%")
            else:
                print(f"   ❌ {vaga['title'][:30]}... - {resultado_match['score']}%")

        # Ordena por score (maior primeiro)
        vagas_com_match.sort(key=lambda x: x['match_score'], reverse=True)

        return vagas_com_match

    def _gerar_relatorio(self, total_vagas, vagas_match, vagas_salvas):
        """
        GERA RELATÓRIO FINAL DA EXECUÇÃO
        """
        print("\n" + "=" * 50)
        print("📊 RELATÓRIO FINAL")
        print("=" * 50)
        print(f"🔍 Vagas encontradas: {len(total_vagas)}")
        print(f"🎯 Vagas com bom match: {len(vagas_match)}")
        print(f"💾 Vagas salvas no Notion: {vagas_salvas}")

        if vagas_match:
            print(f"\n🏆 Top 3 vagas:")
            for i, vaga in enumerate(vagas_match[:3], 1):
                print(f"   {i}. {vaga['title']} - {vaga['match_score']}%")

        print(f"\n⏰ Pipeline concluído: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)


def main():
    """
    FUNÇÃO PRINCIPAL
    Ponto de entrada do sistema
    """
    try:
        pipeline = AutoMatchPipeline()
        sucesso = pipeline.executar_pipeline_completo()

        if sucesso:
            print("\n🎉 Pipeline executado com sucesso!")
            return 0
        else:
            print("\n💥 Pipeline encontrou problemas")
            return 1

    except Exception as e:
        print(f"\n❌ Erro crítico no pipeline: {e}")
        return 1


if __name__ == "__main__":
    # Executa o pipeline
    exit_code = main()
    sys.exit(exit_code)