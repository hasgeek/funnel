# -*- coding: utf-8 -*-

import pytest
from funnel.models import Label


class TestLabels(object):
    def test_main_label_from_fixture(self, test_client, new_main_label):
        assert new_main_label.title == u"Parent Label A"
        assert new_main_label.seq == 1
        assert new_main_label.is_parent
        assert new_main_label.required
        assert new_main_label.restricted
        assert not new_main_label.archived
        assert len(new_main_label.options) > 0

    def test_child_label_from_fixture(self, test_client, test_db, new_main_label):
        assert len(new_main_label.options) > 0
        label_a1 = new_main_label.options[0]
        assert label_a1.title == u"Label A1"
        assert label_a1.icon_emoji == u"👍"
        assert label_a1.icon == u"👍"
        assert not label_a1.is_parent

    def test_label_from_fixture(self, test_client, test_db, new_label):
        assert new_label.title == u"Label B"
        assert new_label.icon_emoji == u"🔟"
        assert new_label.icon == u"🔟"
        assert not new_label.is_parent

        with pytest.raises(ValueError):
            # because Label B is not a parent label, it cannot be required
            new_label.required = True

    def test_proposal_assignment_radio(self, test_client, test_db, new_main_label, new_proposal):
        # Parent labels are always in radio mode
        label_a1 = new_main_label.options[0]
        label_a2 = new_main_label.options[1]
        new_proposal.assign_label(label_a1)
        assert label_a1 in new_proposal.labels

        new_proposal.assign_label(label_a2)
        # because new_main_label is in radio mode,
        # label_a2 will replace label_a1
        assert label_a1 not in new_proposal.labels
        assert label_a2 in new_proposal.labels

    def test_label_flags(self, new_main_label, new_label):
        restricted_labels = Label.query.filter(Label.restricted == True).all()
        assert new_main_label in restricted_labels
        assert new_label not in restricted_labels
