"""Exceptions for Python client for Solar-Log."""


class SolarLogError(Exception):
    """Generic exception."""

class SolarLogConnectionError(SolarLogError):
    """Analytics connection exception."""

class SolarLogUpdateError(SolarLogError):
    """Analytics connection exception."""
