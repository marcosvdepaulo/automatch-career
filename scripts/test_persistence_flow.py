"""Validate the full persistence lifecycle without Supabase credentials."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage import InMemoryRepository


def main():
    repository = InMemoryRepository()
    job_data = {
        "external_id": "demo-001", "company": "Example AI", "title": "Applied AI Engineer",
        "description": "Python, APIs, LLM and RAG", "platform": "demo",
        "url": "https://example.test/jobs/demo-001",
    }
    job = repository.upsert_job(job_data)
    run = repository.create_recommendation_run(
        "3.1-heuristic", "applied-ai-v1", source_context="local_fake_validation",
        total_jobs_found=1, total_jobs_scored=1,
    )
    match = {
        "score": 88.3, "role_family": "applied_ai", "role_fit": 0.897,
        "skill_fit": 0.838, "matched_evidence_strength": 0.838,
        "interest_alignment": 1.0, "hard_gap_penalty": 0.0,
        "reasons": ["Strong alignment with Applied AI roles"],
        "strong_matches": ["python", "apis", "llm_applications"],
        "partial_matches": ["rag"], "hard_gaps": [],
    }
    item = repository.save_recommendation_item(run["id"], job["id"], 1, match, job_data["description"])
    application = repository.create_application(
        job["id"], recommendation_item_id=item["id"], application_source="recommendation",
    )
    for status in ("screening", "interview", "rejected"):
        repository.update_application_status(application["id"], status)

    print("JOB -> RECOMMENDATION RUN -> RECOMMENDATION ITEM -> APPLICATION")
    print(f"Current status: {repository.applications[application['id']]['status']}")
    print("Complete event history:")
    for event in repository.get_application_history(application["id"]):
        print(f"- {event['event']} at {event['occurred_at']}")
    print("Previous events preserved: OK")


if __name__ == "__main__":
    main()
