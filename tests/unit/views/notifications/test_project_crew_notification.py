"""Test template strings in project crew membership notifications."""
# pylint: disable=too-many-arguments

from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models
from funnel.models.membership_mixin import MEMBERSHIP_RECORD_TYPE

scenarios("project_crew_notification.feature")


@given(
    "Rincewind and Twoflower are project crew in the project Expo 2010",
    target_fixture='rincewind_editor',
)
def add_and_check_project_crew_members(
    db_session,
    client,
    login,
    user_vetinari,
    user_rincewind,
    user_twoflower,
    project_expo2010,
) -> models.ProjectCrewMembership:
    rincewind_editor = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_rincewind,
        is_editor=True,
        granted_by=user_vetinari,
    )
    db_session.add(rincewind_editor)
    db_session.commit()
    assert 'editor' in project_expo2010.roles_for(user_rincewind)
    assert 'editor' in project_expo2010.roles_for(user_vetinari)
    return rincewind_editor


@when(
    parsers.parse("Vetinari adds twoflower with role {role}"),
    target_fixture='twoflower_member',
)
def add_twoflower_member(
    role,
    db_session,
    client,
    login,
    user_rincewind,
    user_twoflower,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'crew' in roles
    twoflower_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_twoflower,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    db_session.add(twoflower_member)
    db_session.commit()
    return twoflower_member


@then(parsers.parse("{user} gets notified {notification_string} about addition."))
@then(parsers.parse("{user} gets notified {notification_string} about invitation."))
@then(parsers.parse("{user} gets notified {notification_string} about acceptance."))
@then(parsers.parse("{user} gets notified {notification_string} about amendment."))
def user_notification_addition(
    user,
    notification_string,
    user_rincewind,
    user_twoflower,
    user_vetinari,
    project_expo2010,
    rincewind_editor,
    twoflower_member,
) -> None:
    user_dict = {
        "Twoflower": user_twoflower,
        "Rincewind": user_rincewind,
        "Vetinari": user_vetinari,
    }
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipNotification,
        document=twoflower_member.project,
        fragment=twoflower_member,
    )
    user_notification = models.NotificationFor(preview, user_dict[user])
    view = user_notification.views.render
    assert (
        view.activity_template().format(
            actor=twoflower_member.granted_by.fullname,
            project=twoflower_member.project.joined_title,
            user=twoflower_member.user.fullname,
        )
        == notification_string
    )


@when(
    parsers.parse("Vetinari invites Twoflower to the project with a role {role}"),
    target_fixture='twoflower_member',
)
def invite_twoflower_member(
    role,
    db_session,
    client,
    login,
    user_rincewind,
    user_twoflower,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'crew' in roles
    twoflower_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_twoflower,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    twoflower_member.record_type = MEMBERSHIP_RECORD_TYPE.INVITE
    db_session.add(twoflower_member)
    db_session.commit()
    return twoflower_member


@when(
    parsers.parse(
        "Twoflower accepts the invitation to be an editor of project Expo 2010 with a role {role}"
    ),
    target_fixture='twoflower_member',
)
def accept_twoflower_member(
    role,
    db_session,
    client,
    login,
    user_rincewind,
    user_twoflower,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'crew' in roles
    twoflower_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_twoflower,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    twoflower_member.record_type = MEMBERSHIP_RECORD_TYPE.ACCEPT
    db_session.add(twoflower_member)
    db_session.commit()
    return twoflower_member


@when(
    parsers.parse("Twoflower's role changes to {role}"),
    target_fixture='twoflower_member',
)
def amend_twoflower_member(
    role,
    db_session,
    client,
    login,
    user_rincewind,
    user_twoflower,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'crew' in roles
    twoflower_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_twoflower,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    twoflower_member.record_type = MEMBERSHIP_RECORD_TYPE.AMEND
    db_session.add(twoflower_member)
    db_session.commit()
    return twoflower_member
