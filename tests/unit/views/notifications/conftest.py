"""Test configuration and fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_bdd import given

if TYPE_CHECKING:
    from funnel import models


@given(
    "Vetinari is an owner of the Ankh-Morpork organization",
    target_fixture='vetinari_admin',
)
def given_vetinari_owner_org(
    user_vetinari: models.User, org_ankhmorpork: models.Organization
) -> models.AccountMembership:
    assert 'owner' in org_ankhmorpork.roles_for(user_vetinari)
    vetinari_admin = org_ankhmorpork.active_owner_memberships.first()
    assert vetinari_admin is not None
    assert vetinari_admin.member == user_vetinari
    return vetinari_admin
