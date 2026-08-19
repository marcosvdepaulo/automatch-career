"""CLI pipeline with an explicit candidate profile."""
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import cv_parser
from config import AppConfig
from matcher import CareerMatcher
from notion_client import NotionDB
from ontology import load_ontology
from opportunity_parser import OpportunityProfileParser
from scrapers import VagasScraper
from storage import create_repository

class AutoMatchPipeline:
    def __init__(self, candidate):
        candidate.validate_for_matching()
        self.candidate = candidate
        self.config = AppConfig()
        self.ontology = load_ontology()
        self.scraper = VagasScraper(candidate.search_terms)
        self.matcher = CareerMatcher(self.ontology)
        self.parser = OpportunityProfileParser(self.ontology)
        self.notion, self.storage = NotionDB(), create_repository()
    def executar_pipeline_completo(self):
        if not self.notion.testar_conexao(): return False
        jobs = self.scraper.buscar_todas_vagas()
        recommendations = []
        for index, job in enumerate(jobs):
            opportunity = self.parser.parse(job.get("title"), job.get("description"), job.get("external_id") or job.get("url") or index)
            assessment = self.matcher.assess(self.candidate, opportunity)
            if assessment.eligible and assessment.overall_score >= self.config.MIN_MATCH_SCORE:
                job["match_score"], job["match_details"] = assessment.overall_score, assessment.to_dict()
                recommendations.append(job)
        recommendations.sort(key=lambda item: item["match_score"], reverse=True)
        if self.storage.enabled and recommendations:
            self.storage.persist_recommendations(recommendations[:5], matcher_version=recommendations[0]["match_details"]["matcher_version"],
                profile_version=self.candidate.version, candidate_id=self.candidate.candidate_id, cv_version=self.config.CV_VERSION,
                source_context="main_pipeline_top5", total_jobs_found=len(jobs), total_jobs_scored=len(jobs), all_jobs=jobs)
        self.notion.salvar_lote_vagas(recommendations)
        return True

def main():
    path = AppConfig.CV_PDF_PATH
    if not os.path.exists(path):
        print(f"Perfil incompleto: forneça um currículo em '{path}'. Não existe perfil padrão.")
        return 2
    ontology = load_ontology()
    try: candidate = cv_parser.construir_perfil_do_cv(path, ontology, version=AppConfig.CV_VERSION or "cv-v1")
    except (ValueError, OSError) as error:
        print(f"Perfil incompleto: {error}"); return 2
    print(f"Iniciando AutoMatch para {candidate.candidate_id} em {datetime.now():%d/%m/%Y %H:%M}")
    return 0 if AutoMatchPipeline(candidate).executar_pipeline_completo() else 1

if __name__ == "__main__": raise SystemExit(main())
