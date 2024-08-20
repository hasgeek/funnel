"""Test template strings in project crew membership notifications."""

from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models
from funnel.models.membership_mixin import MembershipRecordTypeEnum

from ....conftest import GetUserProtocol, scoped_session

scenarios('notifications/project_crew_notification.feature')


def role_columns(role: str) -> dict[str, bool]:
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
    user_vetinari: models.User,
    project_expo2010: models.Project,
) -> models.ProjectMembership:
    assert 'promoter' in project_expo2010.roles_for(user_vetinari)
    assert 'project_promoter' in project_expo2010.roles_for(user_vetinari)
    assert 'editor' in project_expo2010.roles_for(user_vetinari)
    assert 'project_editor' in project_expo2010.roles_for(user_vetinari)
    vetinari_member = project_expo2010.crew_memberships.first()
    assert vetinari_member is not None
    assert vetinari_member.member == user_vetinari
    return vetinari_member


@given(
    "Vimes is a promoter of the Ankh-Morpork 2010 project",
    target_fixture='vimes_member',
)
def given_vimes_promoter_project(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_vimes: models.User,
    project_expo2010: models.Project,
) -> models.ProjectMembership:
    vimes_member = models.ProjectMembership(
        parent=project_expo2010,
        member=user_vimes,
        is_promoter=True,
        granted_by=user_vetinari,
    )
    db_session.add(vimes_member)
    db_session.commit()
    assert 'promoter' in project_expo2010.roles_for(user_vimes)
    assert 'project_promoter' in project_expo2010.roles_for(user_vimes)
    return vimes_member


@when(
    parsers.parse(
        "Vetinari adds Ridcully with role {role} to the Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_vetinari_adds_ridcully(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    project_expo2010: models.Project,
    role: str,
) -> models.ProjectMembership:
    ridcully_member = models.ProjectMembership(
        parent=project_expo2010,
        member=user_ridcully,
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
    getuser: GetUserProtocol,
    recipient: str,
    actor: str,
    notification_string: str,
    ridcully_member: models.ProjectMembership,
) -> None:
    preview = models.PreviewNotification(
        models.ProjectCrewNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
        user=ridcully_member.granted_by,
    )
    notification_recipient = models.NotificationFor(preview, getuser(recipient))
    view = notification_recipient.views.render
    assert view.actor == getuser(actor)
    assert ridcully_member.granted_by is not None
    assert (
        view.activity_template().format(
            actor=ridcully_member.granted_by.fullname,
            project=ridcully_member.project.joined_title,
            user=ridcully_member.member.fullname,
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
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    project_expo2010: models.Project,
    role: str,
) -> models.ProjectMembership:
    ridcully_member = models.ProjectMembership(
        parent=project_expo2010,
        member=user_ridcully,
        granted_by=user_vetinari,
        record_type=MembershipRecordTypeEnum.INVITE,
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
    db_session: scoped_session,
    user_ridcully: models.User,
    ridcully_member: models.ProjectMembership,
) -> models.ProjectMembership:
    assert ridcully_member.record_type == MembershipRecordTypeEnum.INVITE
    assert ridcully_member.member == user_ridcully
    ridcully_member_accept = ridcully_member.accept(actor=user_ridcully)
    db_session.commit()
    return ridcully_member_accept


@given(
    "Ridcully is an existing crew member with roles editor, promoter and usher of the"
    " Ankh-Morpork 2010 project",
    target_fixture='ridcully_member',
)
def given_ridcully_is_existing_crew(
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    project_expo2010: models.Project,
) -> models.ProjectMembership:
    ridcully_member = models.ProjectMembership(
        parent=project_expo2010,
        member=user_ridcully,
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
    db_session: scoped_session,
    user_vetinari: models.User,
    ridcully_member: models.ProjectMembership,
    role: str,
) -> models.ProjectMembership:
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
    db_session: scoped_session,
    user_ridcully: models.User,
    ridcully_member: models.ProjectMembership,
    role: str,
) -> models.ProjectMembership:
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
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    org_ankhmorpork: models.Organization,
) -> models.AccountMembership:
    ridcully_admin = models.AccountMembership(
        member=user_ridcully,
        account=org_ankhmorpork,
        granted_by=user_vetinari,
        is_admin=True,
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
    db_session: scoped_session,
    user_vetinari: models.User,
    user_ridcully: models.User,
    project_expo2010: models.Project,
    role: str,
) -> models.ProjectMembership:
    existing_ridcully_member = models.ProjectMembership(
        parent=project_expo2010,
        member=user_ridcully,
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
    db_session: scoped_session,
    user_vetinari: models.User,
    ridcully_member: models.ProjectMembership,
) -> models.ProjectMembership:
    ridcully_member.revoke(actor=user_vetinari)
    db_session.commit()
    return ridcully_member


@when(
    "Ridcully resigns from the Ankh-Morpork 2010 project crew",
    target_fixture='ridcully_member',
)
def when_ridcully_resigns(
    db_session: scoped_session,
    user_ridcully: models.User,
    ridcully_member: models.ProjectMembership,
) -> models.ProjectMembership:
    ridcully_member.revoke(user_ridcully)
    db_session.commit()
    return ridcully_member


@then(
    parsers.parse(
        "{recipient} is notified of the removal with photo of {actor} and message {notification_string}"
    )
)
def then_notification_recipient_removal(
    getuser: GetUserProtocol,
    recipient: str,
    actor: str,
    notification_string: str,
    ridcully_member: models.ProjectMembership,
) -> None:
    preview = models.PreviewNotification(
        models.ProjectCrewRevokedNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
        user=ridcully_member.revoked_by,
    )
    notification_recipient = models.NotificationFor(preview, getuser(recipient))
    view = notification_recipient.views.render
    assert view.actor == getuser(actor)
    assert ridcully_member.revoked_by is not None
    assert (
        view.activity_template().format(
            project=ridcully_member.project.joined_title,
            user=ridcully_member.member.fullname,
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
    db_session: scoped_session,
    user_ridcully: models.User,
    project_expo2010: models.Project,
    role: str,
) -> models.ProjectMembership:
    ridcully_member = models.ProjectMembership(
        parent=project_expo2010,
        member=user_ridcully,
        granted_by=user_ridcully,
        **role_columns(role),
    )
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member
