"""Small value helpers shared by persistence implementations."""

import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


APPLICATION_EVENTS = {
    "applied", "rejected", "screening", "technical_test", "interview",
    "final_interview", "offer", "withdrawn", "ghosted",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize_title(title):
    normalized = unicodedata.normalize("NFKD", title or "")
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_title).strip()


def normalize_company(company):
    return re.sub(r"\s+", " ", (company or "").strip().lower())


def canonicalize_url(url):
    """Drop tracking query/fragment and normalize host/trailing slash."""
    value = (url or "").strip()
    if not value:
        return None
    parsed = urlsplit(value)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def job_identity(job):
    """Conservative identity: external id, URL, then source/company/title."""
    source = (job.get("platform") or job.get("source") or "unknown").strip().lower()
    external_id = str(job.get("external_id") or "").strip()
    if external_id:
        return "external_id", (source, external_id)
    url = canonicalize_url(job.get("url") or job.get("source_url"))
    if url:
        return "source_url", (source, url)
    company = normalize_company(job.get("company"))
    return "fallback", (source, company, normalize_title(job.get("title", "")))


def validate_event(event):
    if event not in APPLICATION_EVENTS:
        raise ValueError(f"Unsupported application event: {event}")
