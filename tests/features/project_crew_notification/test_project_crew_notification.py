from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models

scenarios("project_crew_notification.feature")


@given(
    "Rincewind and Twoflower are project crew in the project Expo 2010",
    target_fixture="add_and_check_project_crew_members",
)
def add_and_check_project_crew_members(
    db_session,
    client,
    login,
    user_vetinari,
    user_rincewind,
    user_twoflower,
    project_expo2010,
):
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
    "Vetinari adds twoflower as an editor",
    target_fixture="add_twoflower_editor",
)
def add_twoflower_editor(
    db_session,
    client,
    login,
    user_rincewind,
    user_twoflower,
    project_expo2010,
    user_vetinari,
):
    twoflower_editor = models.ProjectCrewMembership(
        parent=project_expo2010,
        user=user_twoflower,
        is_editor=True,
        granted_by=user_vetinari,
    )
    db_session.add(twoflower_editor)
    db_session.commit()
    assert 'editor' in project_expo2010.roles_for(user_twoflower)
    return twoflower_editor


@then(parsers.parse("{user} gets notified {notification_string}."))
def twoflower_notification(
    user,
    add_twoflower_editor,
    db_session,
    notification_string,
    user_rincewind,
    add_and_check_project_crew_members,
    project_expo2010,
):
    user_dict = {
        'Twoflower': add_twoflower_editor,
        'Rincewind': add_and_check_project_crew_members,
    }
    preview = models.PreviewNotification(
        models.ProjectCrewMembershipNotification,
        document=add_twoflower_editor.project,
        fragment=add_twoflower_editor,
    )
    notification = models.NotificationFor(preview, user_dict[user].user)
    view = models.Notification.renderers[
        models.ProjectCrewMembershipNotification.cls_type
    ](notification)
    assert (
        view.activity_template().format(
            actor=add_twoflower_editor.granted_by.fullname,
            project=add_twoflower_editor.project.joined_title,
            user=add_twoflower_editor.user.fullname,
        )
        == notification_string
    )
