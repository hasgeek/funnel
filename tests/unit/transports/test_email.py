"""Test email transport functions."""
# pylint: disable=import-outside-toplevel


def test_process_recipient() -> None:
    """
    Test whether process_recipient produces output compatible with sanitize_address.

    `sanitize_address` behaves differently between Python versions, making
    testing tricky, so `process_recipient` tests its output against `sanitize_address`
    before returning it. It will always work in a given Python version, but this test
    can't assert the exact output. FIXME: Needs a consistent implementation and test.
    """
    from flask_mailman.message import sanitize_address

    from funnel.transports.email import process_recipient

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
