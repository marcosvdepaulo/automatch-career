"""Human-readable comparison of the five deterministic Matcher v3 scenarios."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config
from matcher import CareerMatcher


SCENARIOS = [
    ("Applied AI Engineer", "Python, APIs, LLM and RAG."),
    ("Senior DevOps Engineer", "Python, AWS, Git, CI/CD, Kubernetes and Terraform."),
    ("Machine Learning Engineer", "Requirements: Python, PyTorch, model training, CUDA and MLOps."),
    ("AI Gameplay Engineer", "LLMs, agents, game systems and interactive experiences."),
    ("Python Developer", "Build services with Python and APIs."),
]


def main():
    matcher = CareerMatcher(Config())
    headers = ("TITLE", "ROLE FAMILY", "ROLE FIT", "SKILL FIT", "EVIDENCE", "INTEREST", "GAP PENALTY", "FINAL SCORE")
    rows = []
    for title, description in SCENARIOS:
        result = matcher.calculate_match(description, title)
        rows.append((title, result["role_family"], f'{result["role_fit"]:.3f}', f'{result["skill_fit"]:.3f}', f'{result["evidence_strength"]:.3f}', f'{result["interest_alignment"]:.3f}', f'{result["hard_gap_penalty"]:.3f}', f'{result["score"]:.1f}'))
    widths = [max(len(str(value)) for value in column) for column in zip(headers, *rows)]
    print(" | ".join(str(value).ljust(width) for value, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(str(value).ljust(width) for value, width in zip(row, widths)))


if __name__ == "__main__":
    main()
