from funnel.models import Proposal


class TestProposals:
    def test_reorder(self, test_db, new_user, new_project):
        proposal1 = Proposal(
            user=new_user,
            speaker=new_user,
            project=new_project,
            title="Test Proposal 1",
            body="Test body",
            description="Test proposal 1 description",
        )
        test_db.session.add(proposal1)
        proposal2 = Proposal(
            user=new_user,
            speaker=new_user,
            project=new_project,
            title="Test Proposal 2",
            body="Test body",
            description="Test proposal 2 description",
        )
        test_db.session.add(proposal2)
        proposal3 = Proposal(
            user=new_user,
            speaker=new_user,
            project=new_project,
            title="Test Proposal 3",
            body="Test body",
            description="Test proposal 3 description",
        )
        test_db.session.add(proposal3)
        test_db.session.commit()

        assert proposal1.title == "Test Proposal 1"
        assert proposal1.url_id < proposal2.url_id < proposal3.url_id

        proposal1.reorder(below_proposal=proposal2)
        test_db.session.commit()

        assert proposal1.url_id == (proposal2.url_id + proposal3.url_id) // 2
        assert proposal2.url_id < proposal1.url_id < proposal3.url_id

        proposal1.reorder(below_proposal=proposal3)
        test_db.session.commit()

        assert proposal1.url_id == proposal3.url_id + 10000
        assert proposal2.url_id < proposal3.url_id < proposal1.url_id

        proposal2.reorder(below_proposal=proposal1)
        test_db.session.commit()

        assert proposal2.url_id == proposal1.url_id + 10000
        assert proposal3.url_id < proposal1.url_id < proposal2.url_id

        proposal1.reorder()  # below_proposal=None; move to the top of the list
        test_db.session.commit()

        assert proposal1.url_id == proposal3.url_id - 10000
        assert proposal1.url_id < proposal3.url_id < proposal2.url_id

        proposal2.reorder(below_proposal=proposal1)
        test_db.session.commit()

        assert proposal2.url_id == (proposal1.url_id + proposal3.url_id) // 2
        assert proposal1.url_id < proposal2.url_id < proposal3.url_id
