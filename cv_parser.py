"""CV infrastructure adapter; candidate semantics live in profiling.py."""
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
from profiling import CandidateProfileBuilder

def extrair_texto_pdf(caminho_pdf):
    if pdfplumber is None:
        raise ImportError("pdfplumber não está instalado")
    with pdfplumber.open(caminho_pdf) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def construir_perfil_do_cv(caminho_pdf, ontology, candidate_id=None, version="cv-v1"):
    return CandidateProfileBuilder().from_cv_text(extrair_texto_pdf(caminho_pdf), ontology, candidate_id, version)
