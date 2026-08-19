"""Inspect live ranking using an explicitly supplied CV path."""
import argparse
import cv_parser
from matcher import CareerMatcher
from ontology import load_ontology
from opportunity_parser import OpportunityProfileParser
from scrapers import VagasScraper

def main():
    arguments = argparse.ArgumentParser(); arguments.add_argument("cv", help="Caminho do currículo PDF")
    args = arguments.parse_args(); ontology = load_ontology()
    candidate = cv_parser.construir_perfil_do_cv(args.cv, ontology)
    matcher, parser, scored = CareerMatcher(ontology), OpportunityProfileParser(ontology), []
    for index, job in enumerate(VagasScraper(candidate.search_terms).buscar_todas_vagas()):
        opportunity = parser.parse(job.get("title"), job.get("description"), job.get("url") or index)
        scored.append((matcher.assess(candidate, opportunity).overall_score, job.get("title")))
    for score, title in sorted(scored, reverse=True)[:10]: print(f"{score:5.1f}  {title}")
if __name__ == "__main__": main()
