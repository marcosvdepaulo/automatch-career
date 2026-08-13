import unittest

from storage.database import create_repository
from storage.models import job_identity
from storage.repository import InMemoryRepository, NullRepository


def sample_job(**overrides):
    job = {
        "external_id": "job-123", "company": "Example Co", "title": "Applied AI Engineer",
        "description": "Python, APIs, LLM and RAG", "platform": "remoteok",
        "url": "https://example.test/jobs/123",
    }
    job.update(overrides)
    return job


def sample_match(score=88.3):
    return {
        "score": score, "matcher_version": "3.1-heuristic", "role_family": "applied_ai",
        "role_fit": 0.897, "skill_fit": 0.838, "matched_evidence_strength": 0.838,
        "interest_alignment": 1.0, "hard_gap_penalty": 0.0,
        "reasons": ["Strong alignment"], "strong_matches": ["python", "apis"],
        "partial_matches": ["rag"], "hard_gaps": [],
    }


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryRepository()

    def test_creates_recommendation_run_with_versions(self):
        run = self.repository.create_recommendation_run(
            "3.1-heuristic", "applied-ai-v1", cv_version="cv-2026-01",
            total_jobs_found=20, total_jobs_scored=20,
        )
        self.assertEqual(run["matcher_version"], "3.1-heuristic")
        self.assertEqual(run["profile_version"], "applied-ai-v1")
        self.assertEqual(run["cv_version"], "cv-2026-01")

    def test_job_deduplication_precedence(self):
        first = self.repository.upsert_job(sample_job())
        same_external = self.repository.upsert_job(sample_job(title="Changed title", url="https://other.test"))
        self.assertEqual(first["id"], same_external["id"])

        url_job = sample_job(external_id=None)
        same_url = sample_job(external_id=None, title="Another title", url="https://example.test/jobs/123/?utm_source=test")
        self.assertEqual(self.repository.upsert_job(url_job)["id"], self.repository.upsert_job(same_url)["id"])

        fallback_a = sample_job(external_id=None, url=None, title="Senior  AI Engineer")
        fallback_b = sample_job(external_id=None, url=None, title="senior-ai engineer")
        self.assertEqual(self.repository.upsert_job(fallback_a)["id"], self.repository.upsert_job(fallback_b)["id"])

        different_role = sample_job(external_id=None, url=None, title="AI Product Engineer")
        self.assertNotEqual(self.repository.upsert_job(fallback_a)["id"], self.repository.upsert_job(different_role)["id"])

    def test_recommendation_item_preserves_score_and_description_snapshot(self):
        job = sample_job()
        job["match_details"] = sample_match(88.3)
        persisted = self.repository.persist_recommendations(
            [job], "3.1-heuristic", "applied-ai-v1", total_jobs_found=1, total_jobs_scored=1,
        )
        item = persisted["items"][0]
        job["match_details"]["score"] = 10
        job["description"] = "New description"
        self.assertEqual(item["fit_score"], 88.3)
        self.assertEqual(item["job_description_snapshot"], "Python, APIs, LLM and RAG")

    def test_all_scored_jobs_are_stored_but_only_recommendations_become_items(self):
        recommended = sample_job()
        recommended["match_details"] = sample_match()
        other = sample_job(external_id="job-456", url="https://example.test/jobs/456", title="Python Developer")
        persisted = self.repository.persist_recommendations(
            [recommended], "3.1-heuristic", "applied-ai-v1", all_jobs=[recommended, other]
        )
        self.assertEqual(len(self.repository.jobs), 2)
        self.assertEqual(len(persisted["items"]), 1)

    def test_application_events_accumulate_and_status_updates(self):
        job = self.repository.upsert_job(sample_job())
        application = self.repository.create_application(job["id"], status="applied")
        self.repository.update_application_status(application["id"], "screening")
        self.repository.update_application_status(application["id"], "interview")
        current = self.repository.update_application_status(application["id"], "rejected")
        history = self.repository.get_application_history(application["id"])
        self.assertEqual(current["status"], "rejected")
        self.assertEqual([event["event"] for event in history], ["applied", "screening", "interview", "rejected"])

    def test_missing_supabase_configuration_is_safe(self):
        warnings = []
        repository = create_repository({}, warnings.append)
        self.assertIsInstance(repository, NullRepository)
        self.assertFalse(repository.enabled)
        self.assertIn("disabled", warnings[0])
        self.assertIsNone(repository.persist_recommendations([]))

    def test_identity_does_not_merge_distinct_company_roles(self):
        first = job_identity(sample_job(external_id=None, url=None, title="AI Engineer"))
        second = job_identity(sample_job(external_id=None, url=None, title="ML Engineer"))
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
