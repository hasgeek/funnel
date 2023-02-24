"""Test template strings in project crew membership notifications."""
# pylint: disable=too-many-arguments

from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models
from funnel.models.membership_mixin import MEMBERSHIP_RECORD_TYPE

scenarios('notifications/project_crew_notification.feature')


def role_columns(role):
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'usher' in roles
    return {'is_editor': is_editor, 'is_promoter': is_promoter, 'is_usher': is_usher}


@given(
    "Vetinari is an editor and promoter of the Ankh-Morpork 2010 project",
    target_fixture='vetinari_member',
)
def given_vetinari_editor_promoter_project(
    user_vetinari,
    project_expo2010,
) -> models.ProjectCrewMembership:
    assert 'promoter' in project_expo2010.roles_for(user_vetinari)
    assert 'editor' in project_expo2010.roles_for(user_vetinari)
    vetinari_member = project_expo2010.crew_memberships[0]
    assert vetinari_member.user == user_vetinari
    return vetinari_member


@given(
    "Vimes is a promoter of the Ankh-Morpork 2010 project",
    target_fixture='vimes_member',
)
def given_vimes_promoter_project(
    db_session,
    user_vetinari,
    user_vimes,
    project_expo2010,
) -> models.ProjectCrewMembership:
    vimes_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_vimes,
        is_promoter=True,
        granted_by=user_vetinari,
    )
    db_session.add(vimes_member)
    db_session.commit()
    assert 'promoter' in project_expo2010.roles_for(user_vimes)
    return vimes_member


@when(
    parsers.parse(
        "Vetinari adds Ridcully with role {role} to the Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_vetinari_adds_ridcully(
    role,
    db_session,
    user_ridcully,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        granted_by=user_vetinari,
        **role_columns(role),
    )
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member


@then(
    parsers.parse(
        "{recipient} gets notified with photo of {actor} and message {notification_string} about the invitation"
    )
)
@then(
    parsers.parse(
        "{recipient} gets notified with photo of {actor} and message {notification_string} about the addition"
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
    recipient,
    notification_string,
    actor,
    user_vimes,
    user_ridcully,
    user_vetinari,
    ridcully_member,
) -> None:
    user_dict = {
        "Ridcully": user_ridcully,
        "Vimes": user_vimes,
        "Vetinari": user_vetinari,
    }
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
        user=ridcully_member.granted_by,
    )
    user_notification = models.NotificationFor(preview, user_dict[recipient])
    view = user_notification.views.render
    assert view.actor.uuid == user_dict[actor].uuid
    assert (
        view.activity_template().format(
            actor=ridcully_member.granted_by.fullname,
            project=ridcully_member.project.joined_title,
            user=ridcully_member.user.fullname,
        )
        == notification_string
    )


@given(
    parsers.parse(
        "Vetinari invited Ridcully with role {role} to the Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
@when(
    parsers.parse(
        "Vetinari invites Ridcully with role {role} to the Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_vetinari_invites_ridcully(
    role,
    db_session,
    user_ridcully,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        granted_by=user_vetinari,
        record_type=MEMBERSHIP_RECORD_TYPE.INVITE,
        **role_columns(role),
    )
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member


@when(
    "Ridcully accepts the invitation to be a crew member of the Ankh-Morpork 2010"
    " project",
    target_fixture='ridcully_member',
)
def when_ridcully_accepts_invite(
    db_session,
    ridcully_member,
    user_ridcully,
) -> models.ProjectCrewMembership:
    assert ridcully_member.record_type == MEMBERSHIP_RECORD_TYPE.INVITE
    assert ridcully_member.user == user_ridcully
    ridcully_member_accept = ridcully_member.accept(actor=user_ridcully)
    db_session.commit()
    return ridcully_member_accept


@given(
    "Ridcully is an existing crew member with roles editor, promoter and usher of the"
    " Ankh-Morpork 2010 project",
    target_fixture='ridcully_member',
)
def given_ridcully_is_existing_crew(
    db_session,
    user_vetinari,
    user_ridcully,
    project_expo2010,
) -> models.ProjectCrewMembership:
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        is_usher=True,
        is_promoter=True,
        is_editor=True,
        granted_by=user_vetinari,
    )
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member


@when(
    parsers.parse(
        "Vetinari changes Ridcully's role to {role} in the Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_vetinari_amends_ridcully_role(
    role,
    db_session,
    user_vetinari,
    ridcully_member,
) -> models.ProjectCrewMembership:
    ridcully_member_amend = ridcully_member.replace(
        actor=user_vetinari,
        **role_columns(role),
    )
    db_session.commit()
    return ridcully_member_amend


@when(
    parsers.parse(
        "Ridcully changes their role to {role} in the Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_ridcully_changes_role(
    role,
    db_session,
    user_ridcully,
    ridcully_member,
) -> models.ProjectCrewMembership:
    ridcully_member_amend = ridcully_member.replace(
        actor=user_ridcully,
        **role_columns(role),
    )
    db_session.commit()
    return ridcully_member_amend


@given(
    "Vetinari made Ridcully an admin of Ankh-Morpork", target_fixture='ridcully_admin'
)
def given_vetinari_made_ridcully_admin_of_org(
    db_session,
    user_ridcully,
    org_ankhmorpork,
    user_vetinari,
) -> models.OrganizationMembership:
    ridcully_admin = models.OrganizationMembership(
        user=user_ridcully, organization=org_ankhmorpork, granted_by=user_vetinari
    )
    db_session.add(ridcully_admin)
    db_session.commit()
    return ridcully_admin


@given(
    parsers.parse(
        "Ridcully is an existing crew member of the Ankh-Morpork 2010 project with role"
        " {role}"
    ),
    target_fixture='ridcully_member',
)
def given_ridcully_is_existing_member(
    role,
    db_session,
    user_ridcully,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    existing_ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        granted_by=user_vetinari,
        **role_columns(role),
    )
    db_session.add(existing_ridcully_member)
    db_session.commit()
    return existing_ridcully_member


@when(
    "Vetinari removes Ridcully from the Ankh-Morpork 2010 project crew",
    target_fixture='ridcully_member',
)
def when_vetinari_removes_ridcully(
    db_session,
    user_vetinari,
    ridcully_member,
) -> models.ProjectCrewMembership:
    ridcully_member.revoke(actor=user_vetinari)
    db_session.commit()
    return ridcully_member


@when(
    "Ridcully resigns from the Ankh-Morpork 2010 project crew",
    target_fixture='ridcully_member',
)
def when_ridcully_resigns(
    db_session,
    user_ridcully,
    ridcully_member,
) -> models.ProjectCrewMembership:
    ridcully_member.revoke(user_ridcully)
    db_session.commit()
    return ridcully_member


@then(
    parsers.parse(
        "{recipient} is notified of the removal with photo of {actor} and message {notification_string}"
    )
)
def then_user_notification_removal(
    recipient,
    notification_string,
    ridcully_member,
    vetinari_member,
    vimes_member,
    actor,
) -> None:
    user_dict = {
        "Ridcully": ridcully_member.user,
        "Vimes": vimes_member.user,
        "Vetinari": vetinari_member.user,
    }
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipRevokedNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
        user=ridcully_member.revoked_by,
    )
    user_notification = models.NotificationFor(preview, user_dict[recipient])
    view = user_notification.views.render
    assert view.actor.uuid == user_dict[actor].uuid
    assert (
        view.activity_template().format(
            project=ridcully_member.project.joined_title,
            user=ridcully_member.user.fullname,
            actor=ridcully_member.revoked_by.fullname,
        )
        == notification_string
    )


@when(
    parsers.parse(
        "Ridcully adds themself with role {role} to the Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_ridcully_adds_themself(
    role,
    db_session,
    user_ridcully,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        granted_by=user_ridcully,
        **role_columns(role),
    )
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member
