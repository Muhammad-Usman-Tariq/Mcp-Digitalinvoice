"""Typed exceptions for Digital Invoicing Software adapter."""


class AdapterError(Exception):
    """Base exception for all adapter errors."""
    pass


class UpstreamContractError(AdapterError):
    """Raised when third-party response schema changes or is missing mandatory keys."""
    pass


class AuthenticationError(AdapterError):
    """Raised when login or cookie authentication fails with third-party service."""
    pass


class UpstreamServerError(AdapterError):
    """Raised when third-party returns a 5xx server error."""
    pass


class RateLimitError(AdapterError):
    """Raised when rate limit is exceeded on third-party login/API calls."""
    pass


class UnknownSaleTypeError(AdapterError):
    """Raised when sale type mapping is missing from reference data."""
    pass


class UnknownProvinceError(AdapterError):
    """Raised when province mapping is missing from reference data."""
    pass


class AmbiguousRateError(AdapterError):
    """Raised when multiple valid tax rates exist for a sale type and province."""
    pass


class MissingSellerProfileError(AdapterError):
    """Raised when required seller profile data is missing from session/login context."""
    pass


class ConnectionBrokenError(AdapterError):
    """Raised when tenant stored credentials fail to authenticate repeatedly."""
    pass
