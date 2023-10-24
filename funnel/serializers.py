"""Encryption serializers."""

from __future__ import annotations

from itsdangerous import URLSafeTimedSerializer

from coaster.app import KeyRotationWrapper

from . import app


# Lastuser cookie serializer
def lastuser_serializer() -> KeyRotationWrapper:
    return KeyRotationWrapper(
        URLSafeTimedSerializer, app.config['LASTUSER_SECRET_KEYS']
    )


# Future Hasjob login support
def crossapp_serializer() -> KeyRotationWrapper:
    return KeyRotationWrapper(
        URLSafeTimedSerializer, app.config['LASTUSER_SECRET_KEYS']
    )


# Signed tokens in email with TTL
def token_serializer() -> KeyRotationWrapper:
    return KeyRotationWrapper(URLSafeTimedSerializer, app.config['SECRET_KEYS'])
