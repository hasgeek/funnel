from funnel.models import SiteMembership


def test_amend_siteadmin(db_session, user_vetinari, user_vimes):
    """Amend a membership record."""
    membership = SiteMembership(
        user=user_vimes,
        granted_by=user_vetinari,
        is_comment_moderator=True,
        is_user_moderator=False,
        is_site_editor=False,
    )
    db_session.add(membership)
    db_session.commit()

    assert membership.revoked_at is None
    assert membership.is_active is True
    assert membership.is_comment_moderator is True
    assert membership.is_user_moderator is False
    assert membership.is_site_editor is False

    with membership.amend_by(user_vetinari) as amendment:
        assert amendment.membership is membership
        assert amendment.is_comment_moderator is True
        amendment.is_comment_moderator = False
        amendment.is_user_moderator = True

    assert amendment.membership is not membership
    assert membership.revoked_at is not None
    assert membership.is_active is False  # type: ignore[unreachable]

    assert amendment.membership.revoked_at is None
    assert amendment.membership.is_active is True
    assert amendment.membership.is_comment_moderator is False
    assert amendment.membership.is_user_moderator is True
    assert amendment.membership.is_site_editor is False
