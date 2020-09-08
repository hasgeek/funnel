from flask_mailman.message import sanitize_address

from funnel.transports.email import process_recipient


def test_process_recipient():
    """
    Process recipient produces output that Flask-Mailman's sanitize_address won't raise
    ValueError on.
    """
    assert bool(
        sanitize_address(
            process_recipient(
                (
                    "Neque porro quisquam est qui dolorem ipsum quia dolor sit amets consectetur",
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
                    "Neque porro quisquam est qui dolorem ipsum (quia dolor sit amets consectetur",
                    "example@example.com",
                )
            ),
            'utf-8',
        )
    )
    # some regular cases
    assert bool(
        sanitize_address(
            process_recipient(("Neque porro quisquam", "example@example.com")), 'utf-8'
        )
    )
    assert process_recipient(("", "example@example.com")) == 'example@example.com'
