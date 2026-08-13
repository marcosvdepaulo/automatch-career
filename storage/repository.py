"""Repositories for immutable recommendation history and application events."""

from copy import deepcopy
from uuid import uuid4

import requests

from .models import canonicalize_url, job_identity, normalize_company, normalize_title, utc_now, validate_event


class NullRepository:
    enabled = False

    def persist_recommendations(self, *args, **kwargs):
        return None


class InMemoryRepository:
    """Deterministic fake with the same domain operations as Supabase."""

    enabled = True

    def __init__(self):
        self.jobs = {}
        self.runs = {}
        self.items = {}
        self.applications = {}
        self.events = []
        self._job_ids = {}

    @staticmethod
    def _id():
        return str(uuid4())

    def upsert_job(self, job):
        identity = job_identity(job)
        existing_id = self._job_ids.get(identity)
        if existing_id:
            return deepcopy(self.jobs[existing_id])
        job_id = self._id()
        record = {
            "id": job_id, "external_id": job.get("external_id"),
            "company": job.get("company", ""), "title": job.get("title", ""),
            "normalized_company": normalize_company(job.get("company", "")),
            "normalized_title": normalize_title(job.get("title", "")),
            "description_snapshot": job.get("description", ""),
            "source": job.get("platform") or job.get("source") or "unknown",
            "source_url": canonicalize_url(job.get("url") or job.get("source_url")),
            "detected_at": job.get("detected_at") or utc_now(), "created_at": utc_now(),
        }
        self.jobs[job_id] = record
        self._job_ids[identity] = job_id
        return deepcopy(record)

    def create_recommendation_run(self, matcher_version, profile_version, cv_version=None,
                                  source_context=None, total_jobs_found=None, total_jobs_scored=None):
        run_id = self._id()
        record = {"id": run_id, "created_at": utc_now(), "matcher_version": matcher_version,
                  "profile_version": profile_version, "cv_version": cv_version,
                  "source_context": source_context, "total_jobs_found": total_jobs_found,
                  "total_jobs_scored": total_jobs_scored}
        self.runs[run_id] = record
        return deepcopy(record)

    def save_recommendation_item(self, run_id, job_id, rank, match, description_snapshot=""):
        item_id = self._id()
        record = _recommendation_record(item_id, run_id, job_id, rank, match, description_snapshot)
        self.items[item_id] = record
        return deepcopy(record)

    def create_application(self, job_id, recommendation_item_id=None, application_source=None,
                           cv_version=None, status="applied", notes=None, applied_at=None):
        validate_event(status)
        application_id = self._id()
        now = utc_now()
        record = {"id": application_id, "job_id": job_id,
                  "recommendation_item_id": recommendation_item_id,
                  "applied_at": applied_at or now, "application_source": application_source,
                  "cv_version": cv_version, "status": status, "notes": notes,
                  "created_at": now, "updated_at": now}
        self.applications[application_id] = record
        self.add_application_event(application_id, status, occurred_at=record["applied_at"], notes=notes)
        return deepcopy(record)

    def add_application_event(self, application_id, event, occurred_at=None, notes=None, metadata=None):
        validate_event(event)
        record = {"id": self._id(), "application_id": application_id, "event": event,
                  "occurred_at": occurred_at or utc_now(), "notes": notes,
                  "metadata": deepcopy(metadata), "created_at": utc_now()}
        self.events.append(record)
        return deepcopy(record)

    def update_application_status(self, application_id, status, occurred_at=None, notes=None, metadata=None):
        validate_event(status)
        application = self.applications[application_id]
        application["status"] = status
        application["updated_at"] = utc_now()
        self.add_application_event(application_id, status, occurred_at, notes, metadata)
        return deepcopy(application)

    def get_application_history(self, application_id):
        return [deepcopy(event) for event in self.events if event["application_id"] == application_id]

    def persist_recommendations(self, recommendations, matcher_version, profile_version,
                                cv_version=None, source_context=None, total_jobs_found=None,
                                total_jobs_scored=None, all_jobs=None):
        run = self.create_recommendation_run(matcher_version, profile_version, cv_version,
                                             source_context, total_jobs_found, total_jobs_scored)
        persisted_jobs = {
            job_identity(candidate): self.upsert_job(candidate)
            for candidate in (all_jobs if all_jobs is not None else recommendations)
        }
        items = []
        for rank, recommendation in enumerate(recommendations, 1):
            job = persisted_jobs.get(job_identity(recommendation)) or self.upsert_job(recommendation)
            items.append(self.save_recommendation_item(
                run["id"], job["id"], rank, recommendation["match_details"],
                recommendation.get("description", ""),
            ))
        return {"run": run, "items": items}


class SupabaseRepository:
    """Thin PostgREST adapter; matcher and pipeline remain database-agnostic."""

    enabled = True

    def __init__(self, url, key, session=None, timeout=10):
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.timeout = timeout
        self.session = session or requests.Session()
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json", "Prefer": "return=representation"}

    def _request(self, method, table, params=None, json=None):
        response = self.session.request(method, f"{self.base_url}/{table}", headers=self.headers,
                                        params=params, json=json, timeout=self.timeout)
        response.raise_for_status()
        data = response.json() if response.content else []
        return data

    def upsert_job(self, job):
        kind, identity = job_identity(job)
        source = identity[0]
        params = {"source": f"eq.{source}", "select": "*", "limit": "1"}
        if kind == "external_id":
            params["external_id"] = f"eq.{identity[1]}"
        elif kind == "source_url":
            params["source_url"] = f"eq.{identity[1]}"
        else:
            params.update({"normalized_company": f"eq.{identity[1]}", "normalized_title": f"eq.{identity[2]}"})
        existing = self._request("GET", "jobs", params=params)
        if existing:
            return existing[0]
        payload = {"external_id": job.get("external_id"), "company": job.get("company", ""),
                   "normalized_company": normalize_company(job.get("company", "")),
                   "title": job.get("title", ""), "normalized_title": normalize_title(job.get("title", "")),
                   "description_snapshot": job.get("description", ""),
                   "source": source, "source_url": canonicalize_url(job.get("url") or job.get("source_url")),
                   "detected_at": job.get("detected_at") or utc_now()}
        return self._request("POST", "jobs", json=payload)[0]

    def create_recommendation_run(self, matcher_version, profile_version, cv_version=None,
                                  source_context=None, total_jobs_found=None, total_jobs_scored=None):
        payload = {"matcher_version": matcher_version, "profile_version": profile_version,
                   "cv_version": cv_version, "source_context": source_context,
                   "total_jobs_found": total_jobs_found, "total_jobs_scored": total_jobs_scored}
        return self._request("POST", "recommendation_runs", json=payload)[0]

    def save_recommendation_item(self, run_id, job_id, rank, match, description_snapshot=""):
        return self._request("POST", "recommendation_items",
                             json=_recommendation_record(None, run_id, job_id, rank, match, description_snapshot, include_id=False))[0]

    def create_application(self, job_id, recommendation_item_id=None, application_source=None,
                           cv_version=None, status="applied", notes=None, applied_at=None):
        validate_event(status)
        payload = {"job_id": job_id, "recommendation_item_id": recommendation_item_id,
                   "application_source": application_source, "cv_version": cv_version,
                   "status": status, "notes": notes}
        if applied_at:
            payload["applied_at"] = applied_at
        application = self._request("POST", "applications", json=payload)[0]
        self.add_application_event(application["id"], status, application.get("applied_at"), notes)
        return application

    def add_application_event(self, application_id, event, occurred_at=None, notes=None, metadata=None):
        validate_event(event)
        payload = {"application_id": application_id, "event": event, "notes": notes, "metadata": metadata}
        if occurred_at:
            payload["occurred_at"] = occurred_at
        return self._request("POST", "application_events", json=payload)[0]

    def update_application_status(self, application_id, status, occurred_at=None, notes=None, metadata=None):
        validate_event(status)
        application = self._request("PATCH", "applications", params={"id": f"eq.{application_id}"},
                                    json={"status": status})[0]
        self.add_application_event(application_id, status, occurred_at, notes, metadata)
        return application

    def get_application_history(self, application_id):
        return self._request("GET", "application_events",
                             params={"application_id": f"eq.{application_id}",
                                     "select": "*", "order": "occurred_at.asc,created_at.asc"})

    persist_recommendations = InMemoryRepository.persist_recommendations


def _recommendation_record(item_id, run_id, job_id, rank, match, description_snapshot, include_id=True):
    record = {"run_id": run_id, "job_id": job_id, "rank": rank, "fit_score": match["score"],
              "role_family": match.get("role_family", "unknown"), "role_fit": match.get("role_fit", 0),
              "skill_fit": match.get("skill_fit", 0),
              "matched_evidence_strength": match.get("matched_evidence_strength", match.get("evidence_strength", 0)),
              "interest_alignment": match.get("interest_alignment", 0),
              "hard_gap_penalty": match.get("hard_gap_penalty", 0),
              "reasons": deepcopy(match.get("reasons", [])),
              "strong_matches": deepcopy(match.get("strong_matches", [])),
              "partial_matches": deepcopy(match.get("partial_matches", [])),
              "hard_gaps": deepcopy(match.get("hard_gaps", [])),
              "job_description_snapshot": description_snapshot, "recommended_at": utc_now()}
    if include_id:
        record["id"] = item_id
    return record
