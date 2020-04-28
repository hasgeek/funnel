# -*- coding: utf-8 -*-

from werkzeug.datastructures import MultiDict

from funnel.models import Label


class TestLabelViews(object):
    def test_manage_labels_view(
        self, test_client, test_db, new_project, new_user, new_label, new_main_label
    ):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            resp = c.get(new_project.url_for('labels'))
            assert "Manage labels" in resp.data.decode('utf-8')
            assert new_label.title in resp.data.decode('utf-8')
            assert new_main_label.title in resp.data.decode('utf-8')

    def test_labels_order_view(
        self, test_client, test_db, new_project, new_user, new_label, new_main_label
    ):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            assert new_label.seq == 1
            assert new_main_label.seq == 2

            # we'll send the label names in reverse order and that should
            # reorder them in the project
            resp = c.post(
                new_project.url_for('labels'),
                data=MultiDict({'name': [new_main_label.name, new_label.name]}),
                follow_redirects=True,
            )

            # make sure the page loaded properly
            assert "Manage labels" in resp.data.decode('utf-8')
            assert new_label.title in resp.data.decode('utf-8')
            assert new_main_label.title in resp.data.decode('utf-8')

            # make sure the reoder took place
            assert new_label.seq == 2
            assert new_main_label.seq == 1

    def test_new_label_view(self, test_client, test_db, new_project, new_user):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            resp = c.post(
                new_project.url_for('new_label'),
                data=MultiDict(
                    {
                        'title': ["New Main Label", "New Option A", "New Option B"],
                        'icon_emoji': ["💯", "", ""],
                    }
                ),
                follow_redirects=True,
            )

            mlabel = Label.query.filter_by(
                project=new_project, title="New Main Label"
            ).first()
            assert mlabel is not None
            assert mlabel.icon == "💯"
            assert mlabel.has_options
            assert mlabel.is_main_label
            assert mlabel.main_label is None
            assert len(mlabel.options) == 2

            assert mlabel.options[0].title == "New Option A"
            assert mlabel.options[0].seq == 1
            assert mlabel.options[1].title == "New Option B"
            assert mlabel.options[1].seq == 2

            # make sure the page loaded properly
            assert "Manage labels" in resp.data.decode('utf-8')
            assert mlabel.title in resp.data.decode('utf-8')

    def test_edit_option_label_view(
        self, test_client, test_db, new_project, new_user, new_main_label
    ):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            opt_label = new_main_label.options[0]
            resp = c.post(opt_label.url_for('edit'), follow_redirects=True)
            assert "Manage labels" in resp.data.decode('utf-8')
            assert "Only main labels can be edited" in resp.data.decode('utf-8')

    def test_edit_main_label_view(
        self, test_client, test_db, new_project, new_user, new_main_label
    ):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            assert new_main_label.title == "Parent Label A"
            assert new_main_label.name == "parent-label-a"
            assert new_main_label.icon_emoji is None

            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            assert label_a1.title == "Label A1"
            assert label_a1.name == "label-a1"
            assert label_a2.title == "Label A2"
            assert label_a2.name == "label-a2"

            resp = c.post(
                new_main_label.url_for('edit'),
                data=MultiDict(
                    {
                        'name': ["parent-label-a", "label-a1", "label-a2"],
                        'title': [
                            "Parent Label A Edited",
                            "Label A1 Edited",
                            "Label A2 Edited",
                        ],
                        'icon_emoji': ["🔟", "👍", "❌"],
                    }
                ),
                follow_redirects=True,
            )
            assert "Manage labels" in resp.data.decode('utf-8')
            assert "Label has been edited" in resp.data.decode('utf-8')

            assert new_main_label.title == "Parent Label A Edited"
            assert new_main_label.name == "parent-label-a"
            assert new_main_label.icon_emoji == "🔟"

            assert label_a1.title == "Label A1 Edited"
            assert label_a1.name == "label-a1"
            assert label_a1.icon == "👍"
            assert label_a2.title == "Label A2 Edited"
            assert label_a2.name == "label-a2"
            assert label_a2.icon == "❌"


class TestLabelArchiveView(object):
    def test_label_archive(self, test_client, test_db, new_user, new_label):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            resp = c.post(new_label.url_for('archive'), follow_redirects=True)
            label = Label.query.get(new_label.id)
            assert "Manage labels" in resp.data.decode('utf-8')
            assert "The label has been archived" in resp.data.decode('utf-8')
            assert label.archived is True


class TestLabelDeleteView(object):
    """
    Separate class because the ``new_label`` fixture has a class scope.
    If we delete it in any other test classes, it'll mess with other
    tests in those classes.
    """

    def test_main_label_delete(self, test_client, test_db, new_user, new_label):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            resp = c.post(new_label.url_for('delete'), follow_redirects=True)
            assert "Manage labels" in resp.data.decode('utf-8')
            assert "The label has been deleted" in resp.data.decode('utf-8')
            label = Label.query.get(new_label.id)
            assert label is None

    def test_option_label_delete(self, test_client, test_db, new_user, new_main_label):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            assert label_a1.title == "Label A1"
            assert label_a1.seq == 1
            assert label_a2.title == "Label A2"
            assert label_a2.seq == 2

            # let's delete A1
            resp = c.post(label_a1.url_for('delete'), follow_redirects=True)
            assert "Manage labels" in resp.data.decode('utf-8')
            assert "The label has been deleted" in resp.data.decode('utf-8')
            label = Label.query.get(label_a1.id)
            assert label is None

            # as A1 is deleted, A2's sequence should change to 1
            assert label_a2.seq == 1


class TestOptionedLabelDeleteView(object):
    def test_optioned_label_delete(
        self, test_client, test_db, new_user, new_main_label
    ):
        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            # let's delete the main optioned label
            resp = c.post(new_main_label.url_for('delete'), follow_redirects=True)
            assert "Manage labels" in resp.data.decode('utf-8')
            assert "The label has been deleted" in resp.data.decode('utf-8')
            mlabel = Label.query.get(new_main_label.id)
            assert mlabel is None

            # so the option labels should have been deleted as well
            for olabel in [label_a1, label_a2]:
                assert Label.query.get(olabel.id) is None
