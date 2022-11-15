import pytest

from funnel import models
from funnel.views.account import recent_organization_memberships


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
    for i in range(number_of_orgs):
        org = models.Organization(name=str(i), title=str(i), owner=user_twoflower)
        db_session.add(org)
    db_session.commit()
    result = recent_organization_memberships(
        user_twoflower, require_listed, require_overflow
    )
    assert len(result.recent) == returned_listed
    assert len(result.overflow) == returned_overflow
    assert result.extra_count == returned_extra_count
