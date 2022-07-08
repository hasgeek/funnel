"""Transport exceptions."""


from __future__ import annotations


class TransportError(Exception):
    """Base class for transport exceptions."""


class TransportConnectionError(TransportError):
    """Transport engine was unavailable."""


class TransportRecipientError(TransportError):
    """Transport engine did not accept the recipient."""


class TransportTransactionError(TransportError):
    """Transport engine did not accept payload."""
