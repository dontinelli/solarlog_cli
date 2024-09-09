"""Exceptions for Python client for Solar-Log."""


class SolarLogError(Exception):
    """Generic SolarLog exception."""

class SolarLogConnectionError(SolarLogError):
    """SolarLog connection exception."""

class SolarLogAuthenticationError(SolarLogError):
    """Exception in login data."""

class SolarLogUpdateError(SolarLogError):
    """Exception in updating data."""
