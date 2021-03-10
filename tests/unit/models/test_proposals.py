from funnel.models import Proposal


def test_reorder(db_session, user_angua, project_expo2010):
    proposal1 = Proposal(
        user=user_angua,
        speaker=user_angua,
        project=project_expo2010,
        title="Test Proposal 1",
        body="Test body",
        description="Test proposal 1 description",
    )
    db_session.add(proposal1)
    proposal2 = Proposal(
        user=user_angua,
        speaker=user_angua,
        project=project_expo2010,
        title="Test Proposal 2",
        body="Test body",
        description="Test proposal 2 description",
    )
    db_session.add(proposal2)
    proposal3 = Proposal(
        user=user_angua,
        speaker=user_angua,
        project=project_expo2010,
        title="Test Proposal 3",
        body="Test body",
        description="Test proposal 3 description",
    )
    db_session.add(proposal3)
    db_session.commit()

    assert proposal1.title == "Test Proposal 1"
    assert proposal1.url_id < proposal2.url_id < proposal3.url_id

    proposal1.reorder(below_proposal=proposal2)
    db_session.commit()

    assert proposal1.url_id == (proposal2.url_id + proposal3.url_id) // 2
    assert proposal2.url_id < proposal1.url_id < proposal3.url_id

    proposal1.reorder(below_proposal=proposal3)
    db_session.commit()

    assert proposal1.url_id == proposal3.url_id + 10000
    assert proposal2.url_id < proposal3.url_id < proposal1.url_id

    proposal2.reorder(below_proposal=proposal1)
    db_session.commit()

    assert proposal2.url_id == proposal1.url_id + 10000
    assert proposal3.url_id < proposal1.url_id < proposal2.url_id

    proposal1.reorder()  # below_proposal=None; move to the top of the list
    db_session.commit()

    assert proposal1.url_id == proposal3.url_id - 10000
    assert proposal1.url_id < proposal3.url_id < proposal2.url_id

    proposal2.reorder(below_proposal=proposal1)
    db_session.commit()

    assert proposal2.url_id == (proposal1.url_id + proposal3.url_id) // 2
    assert proposal1.url_id < proposal2.url_id < proposal3.url_id
