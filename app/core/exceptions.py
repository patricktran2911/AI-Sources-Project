"""Application-level exceptions.

All custom exceptions extend ``AppError``.  The global exception handler in
``main.py`` converts them to structured JSON responses automatically, so
route handlers should raise these instead of ``HTTPException`` wherever
possible.
"""


class AppError(Exception):
    """Base application error — maps to a structured JSON HTTP response."""

    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ContextNotFoundError(AppError):
    def __init__(self, context_name: str):
        super().__init__(f"Context '{context_name}' not found", status_code=404)


class FeatureNotFoundError(AppError):
    def __init__(self, feature_name: str):
        super().__init__(f"Feature '{feature_name}' not found", status_code=404)


class ProviderError(AppError):
    def __init__(self, provider: str, detail: str = ""):
        msg = f"LLM provider '{provider}' error"
        if detail:
            msg += f": {detail}"
        super().__init__(msg, status_code=502)


class RetrievalError(AppError):
    def __init__(self, detail: str = ""):
        super().__init__(f"Retrieval failed: {detail}", status_code=500)


class ValidationGateError(AppError):
    """Raised when retrieved data is not relevant enough to answer."""

    def __init__(self, detail: str = "Insufficient supporting data to answer"):
        super().__init__(detail, status_code=422)


class RateLimitError(AppError):
    def __init__(self):
        super().__init__("Rate limit exceeded. Please wait before sending more requests.", status_code=429)
