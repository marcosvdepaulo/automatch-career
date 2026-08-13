"""Inspect the current Matcher v3 ranking with live scraper results.

This diagnostic is intentionally read-only: it does not initialize Notion or
persist jobs. Individual scraper failures are logged by ``VagasScraper`` and
the remaining sources continue normally.
"""

from collections import Counter
from pathlib import Path
import queue
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import Config
from matcher import CareerMatcher
from scrapers import VagasScraper


CATEGORIES = ("primary", "secondary", "special_interest", "low_priority", "unknown")
SOURCE_TIMEOUT_SECONDS = 25
COLUMNS = (
    ("RANK", 4),
    ("TITLE", 42),
    ("COMPANY", 22),
    ("SOURCE", 15),
    ("ROLE FAMILY", 30),
    ("PRIORITY / INTEREST", 22),
    ("ROLE FIT", 8),
    ("SKILL FIT", 9),
    ("MATCHED EVIDENCE", 16),
    ("GAP", 6),
    ("SCORE", 6),
    ("STRONG MATCHES", 34),
    ("PARTIAL MATCHES", 34),
    ("HARD GAPS", 34),
)


def _clean(value):
    return " ".join(str(value or "").split())


def _clip(value, width):
    value = _clean(value)
    return value if len(value) <= width else value[: width - 1] + "…"


def _row(job, rank):
    match = job["match"]
    return (
        rank,
        job.get("title", ""),
        job.get("company", ""),
        job.get("platform", ""),
        match["role_family"],
        f'{match["role_priority"]} / {match["interest_alignment"]:.3f}',
        f'{match["role_fit"]:.3f}',
        f'{match["skill_fit"]:.3f}',
        f'{match["evidence_strength"]:.3f}',
        f'{match["hard_gap_penalty"]:.3f}',
        f'{match["score"]:.1f}',
        ", ".join(match["strong_matches"]) or "-",
        ", ".join(match["partial_matches"]) or "-",
        ", ".join(match["hard_gaps"]) or "-",
    )


def _print_table(title, jobs):
    print(f"\n{title}")
    header = " | ".join(name.ljust(width) for name, width in COLUMNS)
    separator = "-+-".join("-" * width for _, width in COLUMNS)
    print(header)
    print(separator)
    if not jobs:
        print("(no jobs)")
        return
    for rank, job in enumerate(jobs, 1):
        values = _row(job, rank)
        print(" | ".join(_clip(value, width).ljust(width) for value, (_, width) in zip(values, COLUMNS)))


def _fetch_jobs(scraper):
    """Run sources independently so a stuck source cannot hide other results."""
    sources = {
        "remoteok": scraper.buscar_vagas_remoteok,
        "arbeitnow": scraper.buscar_vagas_arbeitnow,
        "weworkremotely": scraper.buscar_vagas_weworkremotely,
    }
    results = queue.Queue()

    def run_source(name, function):
        try:
            results.put((name, function(), None))
        except Exception as error:
            results.put((name, [], str(error)))

    threads = {}
    for name, function in sources.items():
        thread = threading.Thread(target=run_source, args=(name, function), daemon=True)
        threads[name] = thread
        thread.start()

    deadline = time.monotonic() + SOURCE_TIMEOUT_SECONDS
    completed = {}
    while len(completed) < len(sources):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            name, jobs, error = results.get(timeout=remaining)
            completed[name] = jobs
            if error:
                print(f"SCRAPER ERROR [{name}]: {error}")
        except queue.Empty:
            break

    for name in sources:
        if name not in completed:
            print(f"SCRAPER ERROR [{name}]: timed out after {SOURCE_TIMEOUT_SECONDS}s")
    raw_jobs = [job for jobs in completed.values() for job in jobs]
    filtered_jobs = scraper._filtrar_por_keywords(raw_jobs)
    print(f"TOTAL RAW FROM COMPLETED SOURCES: {len(raw_jobs)}")
    print(f"TOTAL AFTER CURRENT KEYWORD FILTER: {len(filtered_jobs)}")
    return filtered_jobs


def main():
    config = Config()
    scraper = VagasScraper(config)
    matcher = CareerMatcher(config)

    jobs = _fetch_jobs(scraper)
    scored = []
    for job in jobs:
        item = dict(job)
        item["match"] = matcher.calculate_match(job.get("description", ""), job.get("title", ""))
        scored.append(item)
    scored.sort(key=lambda job: job["match"]["score"], reverse=True)

    top10 = scored[:10]
    target = [job for job in scored if job["match"]["role_priority"] in {"primary", "secondary"}][:5]
    off_target = [job for job in scored if job["match"]["role_priority"] in {"low_priority", "unknown"}][:5]

    _print_table("TOP 10 OVERALL", top10)
    _print_table("TOP 5 PRIMARY / SECONDARY", target)
    _print_table("TOP 5 LOW_PRIORITY / UNKNOWN", off_target)

    all_counts = Counter(job["match"]["role_priority"] for job in scored)
    top_counts = Counter(job["match"]["role_priority"] for job in top10)
    print("\nSUMMARY")
    print(f"TOTAL JOBS FETCHED: {len(jobs)}")
    print(f"TOTAL JOBS SCORED: {len(scored)}")
    print("\nCATEGORY COUNTS (ALL / TOP 10)")
    for category in CATEGORIES:
        print(f"{category}: {all_counts[category]} / {top_counts[category]}")


if __name__ == "__main__":
    main()
