"""Test template strings in project crew membership notifications."""
# pylint: disable=too-many-arguments

from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models
from funnel.models.membership_mixin import MEMBERSHIP_RECORD_TYPE

scenarios("project_crew_notification.feature")


@given(
    "Vetinari is an owner of the Ankh-Morpork organization",
)
def given_vetinari_owner_org(
    user_vetinari,
    project_expo2010,
):
    assert 'editor' in project_expo2010.roles_for(user_vetinari)


@given("Vetinari is an editor and promoter of the Ankh-Morpork 2010 project")
def given_vetinari_editor_promoter_project(
    db_session,
    user_vetinari,
    project_expo2010,
):
    user_vetinari.is_promoter = True
    db_session.add(user_vetinari)
    db_session.commit()
    assert 'promoter' in project_expo2010.roles_for(user_vetinari)
    assert 'editor' in project_expo2010.roles_for(user_vetinari)


@given("Vimes is a promoter of Ankh-Morpork 2010", target_fixture='vimes_promoter')
def given_vimes_promoter_project(
    db_session,
    client,
    login,
    user_vetinari,
    user_vimes,
    user_ridcully,
    project_expo2010,
) -> models.ProjectCrewMembership:
    vimes_promoter = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_vimes,
        is_promoter=True,
        granted_by=user_vetinari,
    )
    db_session.add(vimes_promoter)
    db_session.commit()
    assert 'promoter' in project_expo2010.roles_for(user_vimes)
    return vimes_promoter


@when(
    parsers.parse(
        "Vetinari adds Ridcully with role {role} to Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_add_ridcully_member(
    role,
    db_session,
    client,
    login,
    user_vimes,
    user_ridcully,
    vimes_promoter,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'usher' in roles
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member


@then(parsers.parse("{user} gets notified {notification_string} about addition."))
@then(parsers.parse("{user} gets notified {notification_string} about invitation."))
@then(parsers.parse("{user} gets notified {notification_string} about acceptance."))
@then(parsers.parse("{user} gets notified {notification_string} about amendment."))
def then_user_notification_addition(
    user,
    notification_string,
    user_vimes,
    user_ridcully,
    user_vetinari,
    project_expo2010,
    vimes_promoter,
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
    )
    user_notification = models.NotificationFor(preview, user_dict[user])
    view = user_notification.views.render
    assert (
        view.activity_template().format(
            actor=ridcully_member.granted_by.fullname,
            project=ridcully_member.project.joined_title,
            user=ridcully_member.user.fullname,
        )
        == notification_string
    )


@when(
    parsers.parse(
        "Vetinari invites Ridcully with a role {role} to Ankh-Morpork 2010 project"
    ),
    target_fixture='ridcully_member',
)
def when_invite_ridcully_member(
    role,
    db_session,
    client,
    login,
    user_vimes,
    user_ridcully,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'usher' in roles
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    ridcully_member.record_type = MEMBERSHIP_RECORD_TYPE.INVITE
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member


@when(
    parsers.parse(
        "Ridcully accepts the invitation to be a member of Ankh-Morpork 2010 project with a role {role}"
    ),
    target_fixture='ridcully_member',
)
def when_accept_ridcully_member(
    role,
    db_session,
    client,
    login,
    user_vimes,
    user_ridcully,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'usher' in roles
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    ridcully_member.record_type = MEMBERSHIP_RECORD_TYPE.ACCEPT
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member


@when(
    parsers.parse("Ridcully's role changes to {role} in Ankh-Morpork 2010 project"),
    target_fixture='ridcully_member',
)
def when_amend_ridcully_member(
    role,
    db_session,
    client,
    login,
    user_vimes,
    user_ridcully,
    project_expo2010,
    user_vetinari,
) -> models.ProjectCrewMembership:
    roles = [_r.strip() for _r in role.split(',')]
    is_editor = 'editor' in roles
    is_promoter = 'promoter' in roles
    is_usher = 'usher' in roles
    ridcully_member = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        is_editor=is_editor,
        is_promoter=is_promoter,
        is_usher=is_usher,
        granted_by=user_vetinari,
    )
    ridcully_member.record_type = MEMBERSHIP_RECORD_TYPE.AMEND
    db_session.add(ridcully_member)
    db_session.commit()
    return ridcully_member


@given("Ridcully is a crew member of the project", target_fixture='ridcully_member')
def given_ridcully_crew(
    db_session,
    user_vetinari,
    user_vimes,
    user_ridcully,
    project_expo2010,
) -> models.ProjectCrewMembership:
    vimes_promoter = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_ridcully,
        is_promoter=True,
        granted_by=user_vetinari,
    )
    db_session.add(vimes_promoter)
    db_session.commit()
    assert 'promoter' in project_expo2010.roles_for(user_vimes)
    return vimes_promoter


@when("Ridcully is removed from the project by Vimes")
def when_ridcully_removed(
    db_session,
    user_vetinari,
    user_vimes,
    user_ridcully,
    project_expo2010,
    ridcully_member,
):
    ridcully_member.revoked_by = user_vimes
    db_session.add(ridcully_member)
    db_session.commit()


@then(
    "Ridcully gets a notification 'You were removed as crew member of Ankh-Morpork 2010 by Sam Vimes'"
)
def then_ridcully_notification(ridcully_member, user_ridcully):
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipRevokedNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
    )
    user_notification = models.NotificationFor(preview, user_ridcully)
    view = user_notification.views.render
    assert (
        view.activity_template().format(
            actor=ridcully_member.revoked_by.fullname,
            project=ridcully_member.project.joined_title,
            user=ridcully_member.user.fullname,
        )
        == 'You were removed as crew member of Ankh-Morpork 2010 by Sam Vimes'
    )


@then(
    "Crew members get a notification 'Mustrum Ridcully was removed as a crew member of Ankh-Morpork 2010 by Sam Vimes'"
)
def then_crew_notification(ridcully_member, user_ridcully, user_vetinari):
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipRevokedNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
    )
    user_notification = models.NotificationFor(preview, user_vetinari)
    view = user_notification.views.render
    assert (
        view.activity_template().format(
            actor=ridcully_member.revoked_by.fullname,
            project=ridcully_member.project.joined_title,
            user=ridcully_member.user.fullname,
        )
        == 'Mustrum Ridcully was removed as a crew member of Ankh-Morpork 2010 by Sam Vimes'
    )


@when("Ridcully removes himself from the project")
def when_ridcully_self_removed(
    db_session,
    user_vetinari,
    user_vimes,
    user_ridcully,
    project_expo2010,
    ridcully_member,
):
    ridcully_member.revoked_by = user_ridcully
    db_session.add(ridcully_member)
    db_session.commit()


@then(
    "Ridcully gets a notification 'You removed yourself as a crew member of Ankh-Morpork 2010'"
)
def then_ridcully_self_removal_notification(ridcully_member, user_ridcully):
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipRevokedNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
    )
    user_notification = models.NotificationFor(preview, user_ridcully)
    view = user_notification.views.render
    assert (
        view.activity_template(ridcully_member).format(
            project=ridcully_member.project.joined_title,
        )
        == 'You removed yourself as a crew member of Ankh-Morpork 2010'
    )


@then(
    "Crew members get a notification 'Mustrum Ridcully was removed as a crew member of Ankh-Morpork 2010 by Mustrum Ridcully'"
)
def then_crew_ridcully_self_removal_notification(
    ridcully_member, user_ridcully, user_vetinari
):
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipRevokedNotification,
        document=ridcully_member.project,
        fragment=ridcully_member,
    )
    user_notification = models.NotificationFor(preview, user_vetinari)
    view = user_notification.views.render
    assert (
        view.activity_template().format(
            project=ridcully_member.project.joined_title,
            user=ridcully_member.user.fullname,
            actor=ridcully_member.revoked_by.fullname,
        )
        == 'Mustrum Ridcully was removed as a crew member of Ankh-Morpork 2010 by Mustrum Ridcully'
    )
