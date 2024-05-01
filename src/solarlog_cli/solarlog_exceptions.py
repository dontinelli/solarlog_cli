"""Exceptions for Python client for FYTA."""


class SolarLogError(Exception):
    """Generic exception."""

class SolarLogConnectionError(SolarLogError):
    """Analytics connection exception."""
