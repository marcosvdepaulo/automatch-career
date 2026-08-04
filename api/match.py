# api/match.py
"""
ENDPOINT SERVERLESS (Vercel) — MVP do AutoMatch Web

POST /api/match
Body (JSON): { "pdf_base64": "<currículo em PDF, base64>" }
  - pdf_base64 é opcional: se omitido, usa o MEU_PERFIL estático do config.py.

Resposta (JSON):
{
  "perfil_usado": {...},
  "total_vagas_encontradas": int,
  "total_apos_filtro": int,
  "top_vagas": [ {title, company, url, platform, match_score, match_level, matched_skills}, ... ]
}

Reaproveita config.py / matcher.py / scrapers.py / cv_parser.py do pipeline
cron existente — mesma lógica de matching, só trocando "ler PDF de disco"
por "ler PDF do corpo da requisição" e "salvar no Notion" por "responder
direto pro usuário".
"""

import sys
import os
import io
import json
import base64
from http.server import BaseHTTPRequestHandler

# Permite importar config.py, matcher.py, scrapers.py, cv_parser.py
# que ficam na raiz do repositório (um nível acima de /api).
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from config import Config
from matcher import CareerMatcher
from scrapers import VagasScraper
import cv_parser


def _gerar_perfil(pdf_bytes, config):
    """
    Se houver PDF, extrai o perfil dele (mesma função usada no pipeline
    cron). Se não houver, ou a extração falhar, cai pro perfil estático
    do config.py — nunca quebra por causa do CV.
    """
    if not pdf_bytes:
        return config, None

    try:
        # cv_parser.gerar_perfil_do_cv espera um "caminho_pdf", mas internamente
        # só repassa pro pdfplumber.open(), que aceita tanto path quanto
        # file-like object — por isso dá pra passar um BytesIO direto,
        # sem precisar escrever em disco nem tocar em cv_parser.py.
        meu_perfil, skill_weights = cv_parser.gerar_perfil_do_cv(io.BytesIO(pdf_bytes), config)
        config.MEU_PERFIL = meu_perfil
        config.SKILL_WEIGHTS = skill_weights
        return config, None
    except Exception as e:
        return config, str(e)


def processar_requisicao(pdf_bytes):
    config = Config()
    config, aviso_cv = _gerar_perfil(pdf_bytes, config)

    scraper = VagasScraper(config)
    matcher = CareerMatcher(config)

    vagas_encontradas = scraper.buscar_todas_vagas()

    resultados = []
    for vaga in vagas_encontradas:
        match = matcher.calculate_match(vaga["description"], vaga["title"])
        vaga["match_score"] = match["score"]
        vaga["match_level"] = match["level"]
        vaga["matched_skills"] = match["matches"]
        resultados.append(vaga)

    # Ranking puro: top 5 por score, mesmo que nenhuma passe de um threshold.
    # Diferente do pipeline cron (que corta em >40%), aqui a premissa é
    # "sempre entregar 5", sinalizando quando o fit geral foi baixo.
    resultados.sort(key=lambda x: x["match_score"], reverse=True)
    top5 = resultados[:5]

    return {
        "perfil_usado": {
            "skills": config.MEU_PERFIL["skills"],
            "keywords_vagas": config.MEU_PERFIL["keywords_vagas"],
        },
        "aviso_cv": aviso_cv,
        "total_vagas_encontradas": len(vagas_encontradas),
        "fit_baixo": bool(top5) and top5[0]["match_score"] < 40,
        "top_vagas": top5,
    }


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            payload = json.loads(raw.decode("utf-8")) if raw else {}

            pdf_b64 = payload.get("pdf_base64")
            pdf_bytes = base64.b64decode(pdf_b64) if pdf_b64 else None

            resultado = processar_requisicao(pdf_bytes)
            self._send_json(200, resultado)

        except Exception as e:
            self._send_json(500, {"erro": f"Falha ao processar: {e}"})

    def do_GET(self):
        # Health check simples
        self._send_json(200, {"status": "ok", "servico": "automatch-career /api/match"})