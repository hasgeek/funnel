from funnel.transports.email import process_recipient


def test_process_recipient():
    # if the `realname` portion has no special character, `realname` output is not quoted
    assert (
        process_recipient(
            (
                "Neque porro quisquam est qui dolorem ipsum quia dolor sit amets consectetur",
                "example@example.com",
            )
        )
        == 'Neque porro quisquam est qui dolorem ipsum quia dolor sit amets co <example@example.com>'
    )
    # `realname` output is quoted and `realname` is truncated accordingly
    assert (
        process_recipient(
            (
                "Neque porro quisquam est qui dolorem ipsum (quia dolor sit amets consectetur",
                "example@example.com",
            )
        )
        == '"Neque porro quisquam est qui dolorem ipsum (quia dolor sit amets" <example@example.com>'
    )
    # some regular cases
    assert (
        process_recipient(("Neque porro quisquam", "example@example.com",))
        == 'Neque porro quisquam <example@example.com>'
    )
    assert process_recipient(("", "example@example.com",)) == 'example@example.com'
