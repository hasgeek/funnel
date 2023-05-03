"""Tests for account menu drop-down views."""

import time

import pytest

from funnel import models


@pytest.mark.dbcommit()  # Required for granted_at time to be unique per commit
@pytest.mark.parametrize(
    (
        'number_of_orgs',
        'require_listed',
        'require_overflow',
        'returned_listed',
        'returned_overflow',
        'returned_extra_count',
    ),
    [
        (1, 1, 0, 1, 0, 0),
        (2, 1, 0, 1, 0, 1),
        (2, 1, 1, 1, 1, 1),
        (2, 2, 0, 2, 0, 0),
        (3, 3, 0, 3, 0, 0),
        (4, 3, 1, 3, 1, 1),
        (10, 3, 7, 3, 7, 7),
        (12, 5, 7, 5, 7, 7),
    ],
)
def test_recent_organization_memberships_count(
    db_session,
    user_twoflower,
    number_of_orgs,
    require_listed,
    require_overflow,
    returned_listed,
    returned_overflow,
    returned_extra_count,
) -> None:
    """Test if organization list in account menu handles counts correctly."""
    for i in range(number_of_orgs):
        org = models.Organization(
            name=f'org{i}', title=f"Org {i}", owner=user_twoflower
        )
        db_session.add(org)
        db_session.commit()
        time.sleep(0.001)
    result = user_twoflower.views.recent_organization_memberships(
        require_listed, require_overflow
    )
    # Most recently added org should be first in results. The `dbcommit` mark is
    # required to ensure this, as granted_at timestamp is set by the SQL transaction
    assert result.recent[0].account.name == org.name
    assert len(result.recent) == returned_listed
    assert len(result.overflow) == returned_overflow
    assert result.extra_count == returned_extra_count
