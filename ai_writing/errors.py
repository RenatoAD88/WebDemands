from __future__ import annotations


class AIWritingError(RuntimeError):
    pass


class MissingAPIKeyError(AIWritingError):
    pass


class ModelNotFoundError(AIWritingError):
    pass


class RateLimitError(AIWritingError):
    pass


class AIRequestTimeoutError(AIWritingError):
    pass


class ProviderDependencyError(AIWritingError):
    pass


class UsageLimitReachedError(AIWritingError):
    pass
