"""Test configuration and fixtures."""

from pytest_bdd import given


@given(
    "Vetinari is an owner of the Ankh-Morpork organization",
    target_fixture='vetinari_admin',
)
def given_vetinari_owner_org(user_vetinari, org_ankhmorpork) -> None:
    assert 'owner' in org_ankhmorpork.roles_for(user_vetinari)
    vetinari_admin = org_ankhmorpork.active_owner_memberships[0]
    assert vetinari_admin.user == user_vetinari
    return vetinari_admin
