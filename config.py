"""Operational application configuration. Candidate data is never loaded here."""
import os

class AppConfig:
    CV_PDF_PATH = os.getenv("CV_PDF_PATH", "curriculo.pdf")
    CV_VERSION = os.getenv("CV_VERSION")
    NOTION_DATABASE_NAME = "🎯 Vagas AutoMatch"
    PLATAFORMAS_VAGAS = ("remoteok", "arbeitnow", "weworkremotely")
    MIN_MATCH_SCORE = float(os.getenv("MIN_MATCH_SCORE", "40"))
    MAX_VAGAS_POR_PLATAFORMA = int(os.getenv("MAX_VAGAS_POR_PLATAFORMA", "20"))

Config = AppConfig
