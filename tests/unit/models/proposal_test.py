"""Tests for Proposal model."""

from funnel import models

from ...conftest import scoped_session


def test_reorder(
    db_session: scoped_session,
    user_twoflower: models.User,
    project_expo2010: models.Project,
) -> None:
    proposal1 = models.Proposal(
        created_by=user_twoflower,
        project=project_expo2010,
        title="Test Proposal 1",
        body="Test body",
        description="Test proposal 1 description",
    )
    db_session.add(proposal1)
    proposal2 = models.Proposal(
        created_by=user_twoflower,
        project=project_expo2010,
        title="Test Proposal 2",
        body="Test body",
        description="Test proposal 2 description",
    )
    db_session.add(proposal2)
    proposal3 = models.Proposal(
        created_by=user_twoflower,
        project=project_expo2010,
        title="Test Proposal 3",
        body="Test body",
        description="Test proposal 3 description",
    )
    db_session.add(proposal3)
    db_session.commit()

    assert proposal1.url_id == 1
    assert proposal2.url_id == 2
    assert proposal3.url_id == 3

    assert proposal1.title == "Test Proposal 1"
    assert proposal1.url_id < proposal2.url_id < proposal3.url_id

    proposal1.reorder_after(proposal2)
    db_session.commit()

    assert proposal2.url_id == 1
    assert proposal1.url_id == 2
    assert proposal3.url_id == 3

    proposal1.reorder_after(proposal3)
    db_session.commit()

    assert proposal2.url_id == 1
    assert proposal3.url_id == 2
    assert proposal1.url_id == 3

    proposal2.reorder_after(proposal1)
    db_session.commit()

    assert proposal3.url_id == 1
    assert proposal1.url_id == 2
    assert proposal2.url_id == 3

    proposal1.reorder_before(proposal3)
    db_session.commit()

    assert proposal1.url_id == 1
    assert proposal3.url_id == 2
    assert proposal2.url_id == 3

    proposal3.reorder_after(proposal2)
    db_session.commit()

    assert proposal1.url_id == 1
    assert proposal2.url_id == 2
    assert proposal3.url_id == 3
