from __future__ import annotations

from enum import Enum, IntFlag
from typing import Dict, Pattern, Sequence, cast
import base64
import re

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA1
import requests

__all__ = [
    'SnsNotificationType',
    'SnsValidator',
    'SnsValidatorChecks',
    'SnsValidatorError',
]


class SnsNotificationType(Enum):
    """SNS notification type."""

    SubscriptionConfirmation = 'SubscriptionConfirmation'
    Notification = 'Notification'
    UnsubscribeConfirmation = 'UnsubscribeConfirmation'


class SnsValidatorError(Exception):
    """Base exception for SNS message validator."""


class SnsTopicError(SnsValidatorError):
    """Topic is not what we expect it to be."""


class SnsSignatureVersionError(SnsValidatorError):
    """Signature Version does not match."""


class SnsCertURLError(SnsValidatorError):
    """Certificate URL does not match the one from AWS."""


class SnsMessageTypeError(SnsValidatorError):
    """Does not belong to known message types."""


class SnsSignatureFailureError(SnsValidatorError):
    """Signature does not match with what we computed."""


class SnsValidatorChecks(IntFlag):
    """List of checks performed by SnsValidator."""

    NONE = 0
    TOPIC = 1
    SIGNATURE_VERSION = 2
    CERTIFICATE_URL = 4
    SIGNATURE = 8
    ALL = 15


class SnsValidator:
    """
    Validator for SNS notifications.

    :param cert_regex: Certificate URL compiled regex
    :param sig_version: Signature version (default: 1)
    """

    #: Regular expression for certificate URL
    CERT_URL_REGEX: Pattern[str] = re.compile(
        r'^https://sns\.[-a-z0-9]+\.amazonaws\.com/'
    )
    #: Signature version
    SIGNATURE_VERSION: str = '1'

    def __init__(
        self,
        topics: Sequence[str] = (),
        cert_regex: Pattern[str] = CERT_URL_REGEX,
        sig_version: str = SIGNATURE_VERSION,
    ) -> None:
        self.topics = topics
        self.cert_regex = cert_regex
        self.sig_version = sig_version
        #: Cache of public keys (per Python process)
        self.public_keys: Dict[str, RSAPublicKey] = {}

    def _check_topics(self, message: Dict[str, str]) -> None:
        topic = message.get('TopicArn')
        if not topic:
            raise SnsTopicError("No Topic")
        if topic not in self.topics:
            raise SnsTopicError("Received topic is not in the list of interest")

    def _check_signature_version(self, message: Dict[str, str]) -> None:
        if message.get('SignatureVersion') != self.sig_version:
            raise SnsSignatureVersionError("Signature version is invalid")

    def _check_cert_url(self, message: Dict[str, str]) -> None:
        cert_url = message.get('SigningCertURL')
        if not cert_url:
            raise SnsCertURLError("Missing SigningCertURL field in message")
        if not self.cert_regex.search(cert_url):
            raise SnsCertURLError("Invalid certificate URL")

    @staticmethod
    def _get_text_to_sign(message: Dict[str, str]) -> str:
        """
        Extract the plain text that was used for signing to compare signatures.

        This is done based on the message type. See this URL for more information:
        https://docs.aws.amazon.com/sns/latest/dg/sns-example-code-endpoint-java-servlet.html

        :param message: SNS Message
        :return: Plain text for creating the signature on the client side
        """
        keys: Sequence[str] = ()
        m_type = message.get('Type')
        if m_type in (
            SnsNotificationType.SubscriptionConfirmation.value,
            SnsNotificationType.UnsubscribeConfirmation.value,
        ):
            keys = (
                'Message',
                'MessageId',
                'SubscribeURL',
                'Timestamp',
                'Token',
                'TopicArn',
                'Type',
            )
        elif m_type == SnsNotificationType.Notification.value:
            if message.get('Subject'):
                keys = (
                    'Message',
                    'MessageId',
                    'Subject',
                    'Timestamp',
                    'TopicArn',
                    'Type',
                )
            else:
                keys = (
                    'Message',
                    'MessageId',
                    'Timestamp',
                    'TopicArn',
                    'Type',
                )
        pairs = [f'{key}\n{message.get(key)}' for key in keys]
        return '\n'.join(pairs) + '\n'

    def _get_public_key(self, message: Dict[str, str]) -> RSAPublicKey:
        """
        Get the public key using an internal per-process cache.

        Every message has a signing URL which has a PEM file. We need to get the public
        key of the PEM. To avoid getting it for every message, we can cache it
        internally.

        :param message: SNS Message
        :return: Public Key
        """
        url = message['SigningCertURL']
        public_key = self.public_keys.get(url)
        if not public_key:
            try:
                pem = requests.get(url, timeout=30).content
                cert = x509.load_pem_x509_certificate(pem, default_backend())
                public_key = cast(RSAPublicKey, cert.public_key())
                self.public_keys[url] = public_key
            except requests.exceptions.RequestException as exc:
                raise SnsSignatureFailureError(exc)
        return public_key

    def _check_signature(self, message: Dict[str, str]) -> None:
        """
        Check Signature by comparing the message with the Signature.

        :param message:  Message
        :return: None if Signature matches, throws if Mismatch
        """
        public_key = self._get_public_key(message)
        plaintext = self._get_text_to_sign(message).encode()
        signature = base64.b64decode(message.get('Signature', ''))
        try:
            public_key.verify(  # nosec
                signature,
                plaintext,
                PKCS1v15(),
                SHA1(),  # skipcq: PTC-W1003
            )
        except InvalidSignature:
            raise SnsSignatureFailureError("Signature mismatch")

    def check(
        self,
        message: Dict[str, str],
        checks: SnsValidatorChecks = SnsValidatorChecks.ALL,
    ) -> None:
        """
        Check the given message against specified checks.

        :param message: Given Message
        :param checks:  List of Checks to apply
        :return: None if checks pass or else throws exceptions
        """
        if SnsValidatorChecks.TOPIC in checks:
            self._check_topics(message)
        if SnsValidatorChecks.SIGNATURE_VERSION in checks:
            self._check_signature_version(message)
        if SnsValidatorChecks.CERTIFICATE_URL in checks:
            self._check_cert_url(message)
        if SnsValidatorChecks.SIGNATURE in checks:
            self._check_signature(message)
