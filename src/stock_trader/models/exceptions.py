"""Exceptions for stock trader models."""


class JobNotFoundError(Exception):
    """Exception raised when a backtest job is not found in the database."""

    pass


class JobAlreadyRunningError(Exception):
    """Exception raised when attempting to dispatch a job that is already running."""

    pass


class RangeValidationError(Exception):
    """Exception raised when a market-data request fails validation.

    Covers the symbol and the date range (empty symbol, start after end, span
    over the per-interval cap). A plain ``Exception`` (not a ``ValueError``
    subclass) so it maps to its own 400 handler and stays distinct from other
    ``ValueError`` semantics.
    """

    pass
