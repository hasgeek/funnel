from enum import Enum, IntFlag
from typing import Dict, List
import base64
import re

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA1
import requests


class Type(Enum):
    """ Notification Type. Could only be one of the below """

    SubscriptionConfirmation = 'SubscriptionConfirmation'
    Notification = 'Notification'
    UnsubscribeConfirmation = 'UnsubscribeConfirmation'


class ValidatorException(Exception):
    """ Base Exception for SES Message Validator. """


class TopicException(ValidatorException):
    """ Topic is not what we expect it to be. """


class SignatureVersionException(ValidatorException):
    """ Signature Version does not match """


class CertURLException(ValidatorException):
    """ Certificate URL does not match the one from AWS. """


class MessageTypeException(ValidatorException):
    """ Does not belong to known Message Types """


class SignatureFailureException(ValidatorException):
    """ Signature does not match with what we computed """


class ValidatorChecks(IntFlag):
    """ List of Checks that is done by the Validator. """

    NONE = 0
    TOPIC = 1
    SIGNATURE_VERSION = 2
    CERTIFICATE_URL = 4
    SIGNATURE = 8
    ALL = 15


class Validator:
    """
    Validator for SNS Notifications.

    Attributes:
        CERT_URL_REGEX      Regular expression for Certificate URL
        SIGNATURE_VERSION   Signature Version
    """

    CERT_URL_REGEX: str = r'^https://sns\.[-a-z0-9]+\.amazonaws\.com/'
    SIGNATURE_VERSION: str = '1'

    def __init__(
        self,
        topics: List[str] = (),
        cert_regex: str = CERT_URL_REGEX,
        sig_version: str = SIGNATURE_VERSION,
    ):
        """
        Constructor
        :param cert_regex: Certificate URL Regex
        :param sig_version: Signature Version
        """
        self.topics = topics
        self.cert_regex = cert_regex
        self.sig_version = sig_version
        self.public_keys = {}

    def _check_topics(self, message: Dict[str, str]):
        topic = message.get('TopicArn')
        if not topic:
            raise TopicException('No Topic')
        if topic not in self.topics:
            raise TopicException('Given Topic is not in our List of Interest.')

    def _check_signature_version(self, message: Dict[str, str]) -> None:
        if message.get('SignatureVersion') != self.sig_version:
            raise SignatureVersionException('Signature version is invalid.')

    def _check_cert_url(self, message: Dict[str, str]) -> None:
        cert_url = message.get('SigningCertURL')
        if not cert_url:
            raise CertURLException('Missing SigningCertURL field in message.')
        if not re.search(self.cert_regex, cert_url):
            raise CertURLException('Invalid URL.')

    @staticmethod
    def _get_text_to_sign(message: Dict[str, str]) -> str:
        """
        Extract the Plain Text that was used for Signing to compare
        Signatures. This is done based on the Message Type.
        See this URL for more information:
        https://docs.aws.amazon.com/sns/latest/dg/sns-example-code-endpoint-java-servlet.html

        :param message: SNS Message
        :return: Plain Text for Creating the Signature on the client side.
        """
        keys = ()
        m_type = message.get('Type')
        if m_type in (
            Type.SubscriptionConfirmation.value,
            Type.UnsubscribeConfirmation.value,
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
        elif m_type == Type.Notification.value:
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
        Every message has a Signing URL which has a PEM file. We need to get
        the Public Key of the PEM. To avoid getting it for every message,
        we can cache it internally.
        :param message:  SNS Message
        :return:  Public Key
        """
        url = message.get('SigningCertURL')
        public_key = self.public_keys.get(url)
        if not public_key:
            try:
                pem = requests.get(url).content
                cert = x509.load_pem_x509_certificate(pem, default_backend())
                public_key = cert.public_key()
                self.public_keys[url] = public_key
            except Exception:
                raise SignatureFailureException('Failed to fetch cert file.')
        return public_key

    def _check_signature(self, message: Dict[str, str]):
        """
        Checks Signature by comparing the message with the Signature
        :param message:  Message
        :return: None if Signature matches, throws if Mismatch
        """
        public_key = self._get_public_key(message)
        plaintext = self._get_text_to_sign(message).encode()
        signature = base64.b64decode(message.get('Signature'))
        try:
            public_key.verify(
                signature, plaintext, PKCS1v15(), SHA1(),  # nosec
            )
        except InvalidSignature:
            raise SignatureFailureException('Signature mismatch.')

    def check(
        self, message: Dict[str, str], checks: ValidatorChecks = ValidatorChecks.ALL
    ) -> None:
        """
        Checks the given message against
        :param message: Given Message
        :param checks:  List of Checks to apply
        :return: None if checks pass or else throws exceptions
        """
        if ValidatorChecks.TOPIC in checks:
            self._check_topics(message)
        if ValidatorChecks.SIGNATURE_VERSION in checks:
            self._check_signature_version(message)
        if ValidatorChecks.CERTIFICATE_URL in checks:
            self._check_cert_url(message)
        if ValidatorChecks.SIGNATURE in checks:
            self._check_signature(message)
