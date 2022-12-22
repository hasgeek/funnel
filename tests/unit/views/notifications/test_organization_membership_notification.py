"""Test template strings in project crew membership notifications."""
# pylint: disable=too-many-arguments

from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models
from funnel.models.membership_mixin import MEMBERSHIP_RECORD_TYPE

scenarios('organization_membership_notification.feature')


@given(
    "Vimes is an admin of the Ankh-Morpork organization", target_fixture='vimes_admin'
)
def given_vimes_admin(db_session, user_vimes, org_ankhmorpork, user_vetinari):
    vimes_admin = models.OrganizationMembership(
        user=user_vimes,
        organization=org_ankhmorpork,
        granted_by=user_vetinari,
        is_owner=False,
    )
    db_session.add(vimes_admin)
    assert 'admin' in org_ankhmorpork.roles_for(user_vimes)
    return vimes_admin


@when(
    parsers.parse("Vetinari adds Ridcully as {owner_or_admin}"),
    target_fixture='ridcully_admin',
)
@given(
    parsers.parse(
        "Ridcully is currently {owner_or_admin} of the Ankh-Morpork organization"
    ),
    target_fixture='ridcully_admin',
)
def when_vetinari_adds_ridcully(
    db_session,
    user_vetinari,
    user_ridcully,
    org_ankhmorpork,
    owner_or_admin,
):
    is_owner = True if owner_or_admin == 'owner' else False
    ridcully_admin = models.OrganizationMembership(
        user=user_ridcully,
        organization=org_ankhmorpork,
        granted_by=user_vetinari,
        is_owner=is_owner,
    )
    db_session.add(ridcully_admin)
    db_session.commit()
    return ridcully_admin


@then(
    parsers.parse("{user} gets notified with {notification_string} about the addition")
)
@then(
    parsers.parse(
        "{user} gets notified with {notification_string} about the invitation"
    )
)
@then(
    parsers.parse(
        "{user} gets notified with {notification_string} about the acceptance"
    )
)
@then(parsers.parse("{user} gets notified with {notification_string} about the change"))
def then_user_gets_notification(
    user, notification_string, ridcully_admin, vimes_admin, vetinari_admin
) -> None:
    user_dict = {
        "Ridcully": ridcully_admin.user,
        "Vimes": vimes_admin.user,
        "Vetinari": vetinari_admin.user,
    }
    preview = models.PreviewNotification(
        models.OrganizationAdminMembershipNotification,
        document=ridcully_admin.organization,
        fragment=ridcully_admin,
    )
    user_notification = models.NotificationFor(preview, user_dict[user])
    view = user_notification.views.render
    assert (
        view.activity_template().format(
            actor=ridcully_admin.granted_by.fullname,
            organization=ridcully_admin.organization.title,
            user=ridcully_admin.user.fullname,
        )
        == notification_string
    )


@given(
    parsers.parse("Vetinari invites Ridcully as {owner_or_admin}"),
    target_fixture='ridcully_admin',
)
@when(
    parsers.parse(
        "Vetinari invites Ridcully as {owner_or_admin} of the Ankh-Morpork organization"
    ),
    target_fixture='ridcully_admin',
)
def when_vetinari_invites_ridcully(
    db_session, user_vetinari, user_ridcully, org_ankhmorpork, owner_or_admin
):
    is_owner = True if owner_or_admin == 'owner' else False
    ridcully_admin = models.OrganizationMembership(
        user=user_ridcully,
        organization=org_ankhmorpork,
        granted_by=user_vetinari,
        is_owner=is_owner,
        record_type=MEMBERSHIP_RECORD_TYPE.INVITE,
    )
    db_session.add(ridcully_admin)
    db_session.commit()
    return ridcully_admin


@when(
    "Ridcully accepts the invitation to be admin member of the Ankh-Morpork organization",
    target_fixture='ridcully_admin',
)
def when_ridcully_accepts_invite(
    db_session,
    ridcully_admin,
    user_ridcully,
) -> models.ProjectCrewMembership:
    assert ridcully_admin.record_type == MEMBERSHIP_RECORD_TYPE.INVITE
    assert ridcully_admin.user == user_ridcully
    ridcully_admin_accept = ridcully_admin.accept(actor=user_ridcully)
    db_session.commit()
    return ridcully_admin_accept


@given(
    parsers.parse(
        "Ridcully is currently {owner_or_admin} of the Ankh-Morpork organization"
    ),
    target_fixture='ridcully_admin',
)
def given_riduclly_admin(
    db_session, user_ridcully, org_ankhmorpork, user_vetinari, owner_or_admin
):
    is_owner = True if owner_or_admin == 'owner' else False
    ridcully_admin = models.OrganizationMembership(
        user=user_ridcully,
        organization=org_ankhmorpork,
        granted_by=user_vetinari,
        is_owner=is_owner,
    )
    db_session.add(ridcully_admin)
    db_session.commit()
    return ridcully_admin


@when(
    parsers.parse(
        "Vetinari changes Ridcully to {new_role} in the Ankh-Morpork organization"
    ),
    target_fixture='ridcully_admin',
)
def when_vetinari_amends_ridcully_role(
    db_session, user_vetinari, ridcully_admin, new_role, org_ankhmorpork, user_ridcully
) -> models.ProjectCrewMembership:
    is_owner = True if new_role == 'owner' else False
    ridcully_admin_amend = ridcully_admin.replace(
        actor=user_vetinari, is_owner=is_owner
    )
    db_session.commit()
    return ridcully_admin_amend


@when(
    "Vetinari removes Ridcully from the Ankh-Morpork organization",
    target_fixture='ridcully_admin',
)
def when_vetinari_removes_ridcully(
    db_session,
    user_vetinari,
    ridcully_admin,
) -> models.ProjectCrewMembership:
    ridcully_admin.revoke(actor=user_vetinari)
    db_session.commit()
    return ridcully_admin


@then(
    parsers.parse("{user} gets notified with {notification_string} about the removal")
)
def then_user_notification_removal(
    user,
    notification_string,
    vimes_admin,
    ridcully_admin,
    vetinari_admin,
) -> None:
    user_dict = {
        "Ridcully": ridcully_admin.user,
        "Vimes": vimes_admin.user,
        "Vetinari": vetinari_admin.user,
    }
    preview = models.PreviewNotification(
        models.OrganizationAdminMembershipRevokedNotification,
        document=ridcully_admin.organization,
        fragment=ridcully_admin,
    )
    user_notification = models.NotificationFor(preview, user_dict[user])
    view = user_notification.views.render
    assert (
        view.activity_template().format(
            actor=ridcully_admin.granted_by.fullname,
            organization=ridcully_admin.organization.title,
            user=ridcully_admin.user.fullname,
        )
        == notification_string
    )
