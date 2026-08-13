"""Optional persistence layer for recommendation and application history."""

from .database import create_repository
from .repository import InMemoryRepository, NullRepository, SupabaseRepository

__all__ = ["create_repository", "InMemoryRepository", "NullRepository", "SupabaseRepository"]
