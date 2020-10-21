"""Encryption serializers."""

import itsdangerous

from coaster.app import KeyRotationWrapper

from . import app


# Lastuser cookie serializer
def lastuser_serializer() -> KeyRotationWrapper:
    return KeyRotationWrapper(
        itsdangerous.JSONWebSignatureSerializer, app.config['LASTUSER_SECRET_KEYS']
    )


# Talkfunnel login support
def talkfunnel_serializer() -> KeyRotationWrapper:
    return KeyRotationWrapper(
        itsdangerous.URLSafeTimedSerializer, app.config['LASTUSER_SECRET_KEYS']
    )


# Signed tokens in email with TTL
def token_serializer() -> KeyRotationWrapper:
    return KeyRotationWrapper(
        itsdangerous.URLSafeTimedSerializer, app.config['SECRET_KEYS']
    )
