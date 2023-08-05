"""Test email transport functions."""


import pytest
from flask_mailman.message import sanitize_address

from funnel.models import EmailAddress
from funnel.transports import TransportRecipientError
from funnel.transports.email import process_recipient, send_email


def test_process_recipient() -> None:
    """
    Test whether process_recipient produces output compatible with sanitize_address.

    `sanitize_address` behaves differently between Python versions, making
    testing tricky, so `process_recipient` tests its output against `sanitize_address`
    before returning it. It will always work in a given Python version, but this test
    can't assert the exact output. FIXME: Needs a consistent implementation and test.
    """
    assert bool(
        sanitize_address(
            process_recipient(
                (
                    "Neque porro quisquam est qui dolorem ipsum quia dolor sit amets"
                    " consectetur",
                    "example@example.com",
                )
            ),
            'utf-8',
        )
    )
    # `realname` output is quoted and `realname` is truncated accordingly
    assert bool(
        sanitize_address(
            process_recipient(
                (
                    "Neque porro quisquam est qui dolorem ipsum (quia dolor sit amets"
                    " consectetur",
                    "example@example.com",
                )
            ),
            'utf-8',
        )
    )
    # some regular cases
    assert bool(
        sanitize_address(
            process_recipient(("Neque porro quisquam", "example@example.com")),
            'utf-8',
        )
    )
    assert process_recipient(("", "example@example.com")) == 'example@example.com'


@pytest.mark.usefixtures('db_session')
def test_send_email_blocked() -> None:
    """Confirm that send_email will raise an exception on a blocked email address."""
    ea = EmailAddress.add('blocked@example.com')
    EmailAddress.mark_blocked(ea.email)
    with pytest.raises(
        TransportRecipientError, match='This email address has been blocked'
    ):
        send_email("Email subject", ['blocked@example.com'], "Email content")


@pytest.mark.usefixtures('db_session')
def test_send_email_hard_bouncing() -> None:
    """Confirm that send_email will raise an exception on a hard bouncing email."""
    ea = EmailAddress.add('hard-fail@example.com')
    ea.mark_hard_fail()
    with pytest.raises(TransportRecipientError, match='This email address is bouncing'):
        send_email("Email subject", ['hard-fail@example.com'], "Email content")


@pytest.mark.usefixtures('db_session')
def test_send_email_soft_bouncing() -> None:
    """Confirm that send_email will not fail on a soft bouncing email address."""
    ea = EmailAddress.add('soft-fail@example.com')
    ea.mark_soft_fail()
    assert isinstance(
        send_email("Email subject", ['soft-fail@example.com'], "Email content"), str
    )
