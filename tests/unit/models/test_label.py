# -*- coding: utf-8 -*-

from funnel.models import Label


class TestLabels(object):
    def test_labelset_from_fixture(self, test_client, test_db, new_labelset):
        assert new_labelset.title == u"Labelset A"
        assert new_labelset.name == u"labelset-a"
        assert new_labelset.seq == 1

    def test_label_from_fixture(self, test_client, test_db, new_labelset):
        assert len(new_labelset.labels) > 0
        label_a1 = new_labelset.labels[0]
        assert label_a1.title == u"Label A1"
        assert label_a1.name == u"label-a1"
        assert label_a1.icon_emoji == u"👍"
        assert label_a1.icon == u"👍"

    def test_proposal_assignment(self, test_client, test_db, new_labelset, new_proposal):
        label_a1 = new_labelset.labels[0]
        label_a2 = new_labelset.labels[1]
        new_proposal.assign_label(label_a1)
        assert label_a1 in new_proposal.labels

        new_proposal.assign_label(label_a2)
        # because labelset_a is not in radio mode,
        # both labels will exist
        assert label_a1 in new_proposal.labels
        assert label_a2 in new_proposal.labels

    def test_proposal_assignment_radio(self, test_client, test_db, new_labelset, new_proposal):
        new_labelset.radio_mode = True
        test_db.session.add(new_labelset)
        test_db.session.commit()

        label_a1 = new_labelset.labels[0]
        label_a2 = new_labelset.labels[1]
        new_proposal.assign_label(label_a1)
        assert label_a1 in new_proposal.labels

        new_proposal.assign_label(label_a2)
        # because labelset_a is in radio mode,
        # label_a2 will replace label_a1
        # label_a1 will not exist in ``.labels`
        assert label_a1 not in new_proposal.labels
        assert label_a2 in new_proposal.labels

