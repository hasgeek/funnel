"""Tests for account deletion."""

from pytest_bdd import given, parsers, scenarios, then, when

from funnel import models

scenarios('account/delete_confirm.feature')


@given(parsers.parse('{user} has a protected account'), target_fixture='current_user')
def given_protected_account(getuser, user: str) -> models.User:
    user_obj = getuser(user)
    assert user_obj.is_protected is True
    return user_obj


@given('they are the sole owner of Unseen University')
def given_sole_owner(current_user: models.Account, org_uu: models.Organization) -> None:
    assert list(org_uu.owner_users) == [current_user]


@given('they are a co-owner of Unseen University', target_fixture='org_owner')
def given_coowner(
    db_session, current_user: models.Account, org_uu: models.Organization
) -> models.AccountAdminMembership:
    for membership in org_uu.active_admin_memberships:
        if membership.member == current_user:
            if membership.is_owner:
                return membership
            membership = membership.replace(actor=current_user, is_owner=True)
            return membership
    membership = models.AccountAdminMembership(
        member=current_user,
        granted_by=current_user,
        account=org_uu,
        is_owner=True,
    )
    db_session.add(membership)
    assert len(org_uu.admin_users) > 1
    return membership


@when('they visit the delete page', target_fixture='delete_page')
def when_user_visits_delete_page(client) -> None:
    return client.get('/account/delete')


@then('they are cleared to delete the account')
def then_user_delete_confirm(delete_page) -> None:
    assert delete_page.form('form-account-delete') is not None


@then('they are told they have organizations without co-owners')
def then_told_unshared_orgs(delete_page) -> None:
    assert delete_page.form('form-account-delete') is None
    assert "organizations without co-owners" in delete_page.data.decode()


@then('they are told their account is protected')
def then_told_protected_account(delete_page) -> None:
    assert delete_page.form('form-account-delete') is None
    assert "This account is protected" in delete_page.data.decode()
