from pytest_bdd import given, scenario, then, when

from funnel import models


@scenario(
    "project_crew_notification.feature", "Twoflower is added as an editor to a project"
)
def test_project_crew_notification():
    pass


@given("Rincewind and Twoflower are project crew in the project Expo 2010")
def check_project_crew_members(
    db_session,
    client,
    login,
    user_vetinari,
    user_rincewind,
    user_twoflower,
    project_expo2010,
):
    rincewind_editor = models.ProjectCrewMembership(
        parent=project_expo2010, user=user_rincewind, is_editor=True
    )
    db_session.add(rincewind_editor)
    db_session.commit()
    assert 'editor' in project_expo2010.roles_for(user_rincewind)
    assert 'editor' in project_expo2010.roles_for(user_vetinari)


@when(
    "Vetinari adds twoflower as an editor",
    target_fixture="add_twoflower_editor",
)
def add_twoflower_editor(
    db_session, client, login, user_rincewind, user_twoflower, project_expo2010
):
    twoflower_editor = models.ProjectCrewMembership(
        parent=project_expo2010, user=user_twoflower, is_editor=True
    )
    db_session.add(twoflower_editor)
    db_session.commit()
    assert 'editor' in project_expo2010.roles_for(user_twoflower)
    return twoflower_editor


@then(
    "Twoflower gets notified 'You were made an editor of Expo 2010 by Vetinari'",
)
def twoflower_notification(add_twoflower_editor, db_session):
    # notification = models.ProjectCrewMembershipNotification(add_twoflower_editor)
    # print(notification)
    # db_session.add()
    # db_session.commit()
    # all_user_notifications = list(notification.dispatch())
    # db_session.commit()
    pass


@then("Rincewind gets notified 'Twoflower was made an editor of Expo 2010 by Vetinari'")
def rincewind_notification():
    pass
