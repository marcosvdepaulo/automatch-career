"""Manual smoke scenarios for the domain matcher."""
from domain.models import CandidateCompetency, CandidateProfile, CareerInterest, Evidence
from matcher import CareerMatcher
from ontology import load_ontology
from opportunity_parser import OpportunityProfileParser

def main():
    ontology = load_ontology()
    candidate = CandidateProfile("scenario", (
        CandidateCompetency("python", (Evidence("fixture", "Production Python"),), "strong", .9, depth="deployed"),
        CandidateCompetency("apis", (Evidence("fixture", "REST services"),), "working", .8, depth="working_product"),
    ), (CareerInterest("applied_ai", 1.0),))
    matcher, parser = CareerMatcher(ontology), OpportunityProfileParser(ontology)
    for title, description in (("Applied AI Engineer", "Requirements: Python and APIs"),
                               ("Machine Learning Engineer", "Requirements: PyTorch, CUDA and MLOps")):
        print(title, matcher.assess(candidate, parser.parse(title, description, title)).to_dict())

if __name__ == "__main__":
    main()
