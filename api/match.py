"""POST /api/match requires a CV and never falls back to a shared candidate."""
import base64
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import cv_parser
from matcher import CareerMatcher
from ontology import load_ontology
from opportunity_parser import OpportunityProfileParser
from scrapers import VagasScraper
from storage import create_repository

def processar_requisicao(pdf_bytes, candidate_id=None):
    if not pdf_bytes:
        raise ValueError("pdf_base64 é obrigatório; perfil padrão não existe")
    ontology = load_ontology()
    candidate = cv_parser.construir_perfil_do_cv(io.BytesIO(pdf_bytes), ontology, candidate_id)
    scraper, parser, matcher = VagasScraper(candidate.search_terms), OpportunityProfileParser(ontology), CareerMatcher(ontology)
    jobs = scraper.buscar_todas_vagas()
    results = []
    for index, job in enumerate(jobs):
        opportunity = parser.parse(job.get("title"), job.get("description"), job.get("external_id") or job.get("url") or index,
                                   location=job.get("location"), employment_type=job.get("employment_type"))
        assessment = matcher.assess(candidate, opportunity)
        result = dict(job)
        result.update({"match_score": assessment.overall_score, "match_level": assessment.level,
                       "matched_skills": list(assessment.strengths + assessment.partial_matches),
                       "match_details": assessment.to_dict()})
        results.append(result)
    results.sort(key=lambda item: item["match_score"], reverse=True)
    top5 = results[:5]
    storage = create_repository()
    if storage.enabled and top5:
        storage.persist_recommendations(top5, matcher_version=top5[0]["match_details"]["matcher_version"],
            profile_version=candidate.version, candidate_id=candidate.candidate_id, source_context="api_top5",
            total_jobs_found=len(jobs), total_jobs_scored=len(results), all_jobs=results)
    for item in top5: item.pop("match_details", None)
    return {"candidate_id": candidate.candidate_id, "perfil_usado": {"skills": list(candidate.competency_map)},
            "total_vagas_encontradas": len(jobs), "fit_baixo": bool(top5) and top5[0]["match_score"] < 40,
            "top_vagas": top5}

class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS"); self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0)); raw = self.rfile.read(length) if length else b""
            payload = json.loads(raw.decode()) if raw else {}; encoded = payload.get("pdf_base64")
            if not encoded: self._send_json(422, {"erro": "pdf_base64 é obrigatório"}); return
            self._send_json(200, processar_requisicao(base64.b64decode(encoded, validate=True), payload.get("candidate_id")))
        except (ValueError, TypeError) as error: self._send_json(422, {"erro": str(error)})
        except Exception as error: self._send_json(500, {"erro": f"Falha ao processar: {error}"})
    def do_GET(self): self._send_json(200, {"status": "ok", "servico": "automatch-career /api/match"})
