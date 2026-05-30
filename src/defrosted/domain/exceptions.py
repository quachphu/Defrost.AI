"""
Domain-specific exceptions.

These are raised by services and repositories to signal business-rule failures.
Each one says exactly WHY it failed (Karpathy rule 7). The API layer maps these
to HTTP status codes; nothing else should leak out of the domain.
"""
from __future__ import annotations

import uuid


class DomainError(Exception):
    """Base class for all domain errors. Never raised directly."""


class SearchNotFoundError(DomainError):
    def __init__(self, search_id: uuid.UUID) -> None:
        super().__init__(f"RentalSearch {search_id} does not exist.")
        self.search_id = search_id


class InvalidStatusTransitionError(DomainError):
    """Raised when a state machine transition is not allowed."""

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(
            f"Cannot transition rental search from '{current}' to '{requested}'. "
            "See RentalSearch.can_transition_to for the allowed paths."
        )
        self.current = current
        self.requested = requested


class TooManyActiveSearchesError(DomainError):
    """Raised when a user exceeds the concurrent active-search limit."""

    def __init__(self, user_id: uuid.UUID, limit: int) -> None:
        super().__init__(
            f"User {user_id} already has {limit} active searches, which is the maximum."
        )
        self.user_id = user_id
        self.limit = limit


class ApprovalRequiredError(DomainError):
    """
    Raised when an offer or lease action is attempted without a recorded
    HumanApproval. The agent must never act past an approval gate autonomously.
    """

    def __init__(self, action: str, search_id: uuid.UUID) -> None:
        super().__init__(
            f"Action '{action}' on search {search_id} requires a HumanApproval record "
            "that does not exist. Refusing to proceed."
        )
        self.action = action
        self.search_id = search_id
