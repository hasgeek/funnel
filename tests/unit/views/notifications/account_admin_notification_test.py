"""Test template strings in project crew membership notifications."""

from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models
from funnel.models.membership_mixin import MembershipRecordTypeEnum

from ....conftest import GetUserProtocol, scoped_session

scenarios('notifications/account_admin_notification.feature')


@given(
    "Vimes is an admin of the Ankh-Morpork organization",
    target_fixture='vimes_admin',
)
def given_vimes_admin(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_vimes: models.User,
    org_ankhmorpork: models.Organization,
) -> models.AccountMembership:
    vimes_admin = models.AccountMembership(
        member=user_vimes,
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        is_admin=True,
    )
    db_session.add(vimes_admin)
    assert 'admin' in org_ankhmorpork.roles_for(user_vimes)
    return vimes_admin


@when(
    parsers.parse("Vetinari adds Ridcully as {role}"),
    target_fixture='ridcully_admin',
)
@given(
    parsers.parse("Ridcully is currently {role}"),
    target_fixture='ridcully_admin',
)
def when_vetinari_adds_ridcully(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    org_ankhmorpork: models.Organization,
    role: str,
) -> models.AccountMembership:
    is_owner = role == 'owner'
    ridcully_admin = models.AccountMembership(
        member=user_ridcully,
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        is_owner=is_owner,
        is_admin=True,
    )
    db_session.add(ridcully_admin)
    db_session.commit()
    return ridcully_admin


@then(
    parsers.parse(
        "{recipient} gets notified with a photo of {actor} and message {notification_string} about the addition"
    )
)
@then(
    parsers.parse(
        "{recipient} gets notified with photo of {actor} and message {notification_string} about the invitation"
    )
)
@then(
    parsers.parse(
        "{recipient} gets notified with photo of {actor} and message {notification_string} about the acceptance"
    )
)
@then(
    parsers.parse(
        "{recipient} gets notified with photo of {actor} and message {notification_string} about the change"
    )
)
def then_user_gets_notification(
    getuser: GetUserProtocol,
    recipient: str,
    actor: str,
    notification_string: str,
    ridcully_admin: models.AccountMembership,
) -> None:
    preview = models.PreviewNotification(
        models.AccountAdminNotification,
        document=ridcully_admin.account,
        fragment=ridcully_admin,
        user=ridcully_admin.granted_by,
    )
    notification_recipient = models.NotificationFor(preview, getuser(recipient))
    view = notification_recipient.views.render
    assert view.actor == getuser(actor)
    assert ridcully_admin.granted_by is not None
    assert (
        view.activity_template().format(
            actor=ridcully_admin.granted_by.fullname,
            organization=ridcully_admin.account.title,
            user=ridcully_admin.member.fullname,
        )
        == notification_string
    )


@given(
    parsers.parse("Vetinari invites Ridcully as {role}"),
    target_fixture='ridcully_admin',
)
@when(
    parsers.parse("Vetinari invites Ridcully as {role}"),
    target_fixture='ridcully_admin',
)
def when_vetinari_invites_ridcully(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    org_ankhmorpork: models.Organization,
    role: str,
) -> models.AccountMembership:
    is_owner = role == 'owner'
    ridcully_admin = models.AccountMembership(
        member=user_ridcully,
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        is_owner=is_owner,
        is_admin=True,
        record_type=MembershipRecordTypeEnum.INVITE,
    )
    db_session.add(ridcully_admin)
    db_session.commit()
    return ridcully_admin


@when(
    "Ridcully accepts the invitation to be admin",
    target_fixture='ridcully_admin',
)
def when_ridcully_accepts_invite(
    db_session: scoped_session,
    user_ridcully: models.User,
    ridcully_admin: models.AccountMembership,
) -> models.AccountMembership:
    assert ridcully_admin.record_type == MembershipRecordTypeEnum.INVITE
    assert ridcully_admin.member == user_ridcully
    ridcully_admin_accept = ridcully_admin.accept(actor=user_ridcully)
    db_session.commit()
    return ridcully_admin_accept


@given(
    parsers.parse("Ridcully is currently {role}"),
    target_fixture='ridcully_admin',
)
def given_riduclly_admin(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    org_ankhmorpork: models.Organization,
    role: str,
) -> models.AccountMembership:
    is_owner = role == 'owner'
    ridcully_admin = models.AccountMembership(
        member=user_ridcully,
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        is_owner=is_owner,
        is_admin=True,
    )
    db_session.add(ridcully_admin)
    db_session.commit()
    return ridcully_admin


@when(
    parsers.parse("Vetinari changes Ridcully to {new_role}"),
    target_fixture='ridcully_admin',
)
def when_vetinari_amends_ridcully_role(
    db_session: scoped_session,
    user_vetinari: models.User,
    ridcully_admin: models.AccountMembership,
    new_role: str,
) -> models.AccountMembership:
    is_owner = new_role == 'owner'
    ridcully_admin_amend = ridcully_admin.replace(
        actor=user_vetinari, is_owner=is_owner
    )
    db_session.commit()
    return ridcully_admin_amend


@when(
    "Vetinari removes Ridcully",
    target_fixture='ridcully_admin',
)
def when_vetinari_removes_ridcully(
    db_session: scoped_session,
    user_vetinari: models.User,
    ridcully_admin: models.AccountMembership,
) -> models.AccountMembership:
    ridcully_admin.revoke(actor=user_vetinari)
    db_session.commit()
    return ridcully_admin


@then(
    parsers.parse(
        "{recipient} gets notified with photo of {actor} and message {notification_string} about the removal"
    )
)
def then_notification_recipient_removal(
    getuser: GetUserProtocol,
    recipient: str,
    notification_string: str,
    actor: str,
    ridcully_admin: models.AccountMembership,
) -> None:
    preview = models.PreviewNotification(
        models.AccountAdminRevokedNotification,
        document=ridcully_admin.account,
        fragment=ridcully_admin,
        user=ridcully_admin.revoked_by,
    )
    notification_recipient = models.NotificationFor(preview, getuser(recipient))
    view = notification_recipient.views.render
    assert view.actor == getuser(actor)
    assert ridcully_admin.granted_by is not None
    assert (
        view.activity_template().format(
            actor=ridcully_admin.granted_by.fullname,
            organization=ridcully_admin.account.title,
            user=ridcully_admin.member.fullname,
        )
        == notification_string
    )
