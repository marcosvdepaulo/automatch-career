"""Persistence factory; missing credentials deliberately disable storage."""

import os

from .repository import NullRepository, SupabaseRepository


def create_repository(environ=None, warn=print):
    environ = environ if environ is not None else os.environ
    url, key = environ.get("SUPABASE_URL"), environ.get("SUPABASE_KEY")
    if not url or not key:
        warn("⚠️ Supabase persistence disabled: SUPABASE_URL/SUPABASE_KEY not configured.")
        return NullRepository()
    return SupabaseRepository(url, key)
