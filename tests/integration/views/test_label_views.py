# -*- coding: utf-8 -*-

import json
from werkzeug.datastructures import MultiDict
from funnel.models import Label
from funnel.forms import ProposalLabelsAdminForm


class TestLabelViews(object):
    def test_manage_labels_view(self, test_client, test_db, new_project, new_user, new_label, new_main_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp = c.get(new_project.url_for('labels'))
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert new_label.title in resp.data.decode('utf-8')
            assert new_main_label.title in resp.data.decode('utf-8')

    def test_labels_order_view(self, test_client, test_db, new_project, new_user, new_label, new_main_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            assert new_label.seq == 1
            assert new_main_label.seq == 2

            # we'll send the label names in reverse order and that should
            # reorder them in the project
            resp = c.post(new_project.url_for('labels'), data=MultiDict({
                'name': [new_main_label.name, new_label.name]
                }), follow_redirects=True)

            # make sure the page loaded properly
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert new_label.title in resp.data.decode('utf-8')
            assert new_main_label.title in resp.data.decode('utf-8')

            # make sure the reoder took place
            assert new_label.seq == 2
            assert new_main_label.seq == 1

    def test_new_label_view(self, test_client, test_db, new_project, new_user):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp = c.post(new_project.url_for('new_label'), data=MultiDict({
                'title': ["New Main Label", "New Option A", "New Option B"],
                'icon_emoji': [u"💯", u"", u""],
                }), follow_redirects=True)

            mlabel = Label.query.filter_by(project=new_project, title=u"New Main Label").first()
            assert mlabel is not None
            assert mlabel.icon == u"💯"
            assert mlabel.has_options
            assert mlabel.is_main_label
            assert mlabel.main_label is None
            assert len(mlabel.options) == 2

            assert mlabel.options[0].title == "New Option A"
            assert mlabel.options[0].seq == 1
            assert mlabel.options[1].title == "New Option B"
            assert mlabel.options[1].seq == 2

            # make sure the page loaded properly
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert mlabel.title in resp.data.decode('utf-8')

    def test_edit_option_label_view(self, test_client, test_db, new_project, new_user, new_main_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            opt_label = new_main_label.options[0]
            resp = c.post(opt_label.url_for('edit'), follow_redirects=True)
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert u"Only main labels can be edited" in resp.data.decode('utf-8')

    def test_edit_main_label_view(self, test_client, test_db, new_project, new_user, new_main_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            assert new_main_label.title == u"Parent Label A"
            assert new_main_label.name == u"parent-label-a"
            assert new_main_label.icon_emoji is None

            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            assert label_a1.title == u"Label A1"
            assert label_a1.name == u"label-a1"
            assert label_a2.title == u"Label A2"
            assert label_a2.name == u"label-a2"

            resp = c.post(new_main_label.url_for('edit'), data=MultiDict({
                'name': ["parent-label-a", "label-a1", "label-a2"],
                'title': ["Parent Label A Edited", "Label A1 Edited", "Label A2 Edited"],
                'icon_emoji': [u"🔟", u"👍", u"❌"]
                }), follow_redirects=True)
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert u"Label has been edited" in resp.data.decode('utf-8')

            assert new_main_label.title == u"Parent Label A Edited"
            assert new_main_label.name == u"parent-label-a"
            assert new_main_label.icon_emoji == u"🔟"

            assert label_a1.title == u"Label A1 Edited"
            assert label_a1.name == u"label-a1"
            assert label_a1.icon == u"👍"
            assert label_a2.title == u"Label A2 Edited"
            assert label_a2.name == u"label-a2"
            assert label_a2.icon == u"❌"


class TestLabelArchiveView(object):
    def test_label_archive(self, test_client, test_db, new_user, new_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp = c.post(new_label.url_for('archive'), follow_redirects=True)
            label = Label.query.get(new_label.id)
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert u"The label has been archived" in resp.data.decode('utf-8')
            assert label.archived is True


class TestLabelDeleteView(object):
    """
    Separate class because the ``new_label`` fixture has a class scope.
    If we delete it in any other test classes, it'll mess with other
    tests in those classes.
    """
    def test_main_label_delete(self, test_client, test_db, new_user, new_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp = c.post(new_label.url_for('delete'), follow_redirects=True)
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert u"The label has been deleted" in resp.data.decode('utf-8')
            label = Label.query.get(new_label.id)
            assert label is None

    def test_option_label_delete(self, test_client, test_db, new_user, new_main_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            assert label_a1.title == u"Label A1"
            assert label_a1.seq == 1
            assert label_a2.title == u"Label A2"
            assert label_a2.seq == 2

            # let's delete A1
            resp = c.post(label_a1.url_for('delete'), follow_redirects=True)
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert u"The label has been deleted" in resp.data.decode('utf-8')
            label = Label.query.get(label_a1.id)
            assert label is None

            # as A1 is deleted, A2's sequence should change to 1
            assert label_a2.seq == 1


class TestOptionedLabelDeleteView(object):
    def test_optioned_label_delete(self, test_client, test_db, new_user, new_main_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            # let's delete the main optioned label
            resp = c.post(new_main_label.url_for('delete'), follow_redirects=True)
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert u"The label has been deleted" in resp.data.decode('utf-8')
            mlabel = Label.query.get(new_main_label.id)
            assert mlabel is None

            # so the option labels should have been deleted as well
            for olabel in [label_a1, label_a2]:
                assert Label.query.get(olabel.id) is None


class TestProposalLabelsView(object):
    def test_proposal_labels_update_view(self, test_client, test_db, new_user, new_label, new_main_label, new_proposal):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            assert not label_a1.is_applied_to(new_proposal)
            assert not label_a2.is_applied_to(new_proposal)
            assert not new_main_label.is_applied_to(new_proposal)

            respa = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [label_a1.name],
                    'removeLabel': []
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respa.data)['status'] == 'ok'
            assert label_a1.is_applied_to(new_proposal)
            assert new_main_label.is_applied_to(new_proposal)
            assert new_main_label.option_applied_to(new_proposal) == label_a1

            respb = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [label_a2.name],
                    'removeLabel': []
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respb.data)['status'] == 'ok'
            assert not label_a1.is_applied_to(new_proposal)  # because a1 was replaced by a2
            assert label_a2.is_applied_to(new_proposal)
            assert new_main_label.is_applied_to(new_proposal)
            assert new_main_label.option_applied_to(new_proposal) == label_a2

            respc = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [],
                    'removeLabel': [label_a1.name]  # this does nothing as a1 is not even appled to this proposal
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respc.data)['status'] == 'ok'
            assert not label_a1.is_applied_to(new_proposal)
            assert label_a2.is_applied_to(new_proposal)

            respd = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [],
                    'removeLabel': [label_a2.name]
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respd.data)['status'] == 'ok'
            assert not label_a1.is_applied_to(new_proposal)
            assert not label_a2.is_applied_to(new_proposal)
            assert not new_main_label.is_applied_to(new_proposal)

            assert not new_label.is_applied_to(new_proposal)
            assert new_label.option_applied_to(new_proposal) is None
            respd = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [new_label.name],
                    'removeLabel': []
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respd.data)['status'] == 'ok'
            assert new_label.is_applied_to(new_proposal)
            assert new_label.option_applied_to(new_proposal) == new_label

            respd = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [],
                    'removeLabel': [new_label.name]
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respd.data)['status'] == 'ok'
            assert not new_label.is_applied_to(new_proposal)
            assert new_label.option_applied_to(new_proposal) is None

    def test_proposal_labels_update_archived_view(self, test_client, test_db, new_user, new_label, new_main_label, new_proposal):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            label_a1 = new_main_label.options[0]
            label_a2 = new_main_label.options[1]

            assert not label_a1.is_applied_to(new_proposal)
            assert not label_a2.is_applied_to(new_proposal)
            assert not new_main_label.is_applied_to(new_proposal)
            assert not new_label.is_applied_to(new_proposal)

            respa = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [label_a1.name],
                    'removeLabel': []
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respa.data)['status'] == 'ok'
            assert label_a1.is_applied_to(new_proposal)

            # now let's archive new_main_label
            respla = c.post(new_main_label.url_for('archive'), data={}, follow_redirects=True)
            assert u"The label has been archived" in respla.data.decode('utf-8')
            assert new_main_label.archived is True

            # the option should still be attached to the proposal
            assert label_a1.is_applied_to(new_proposal)

            # this label should still load in the admin form which is sent along with proposal json
            admin_form = ProposalLabelsAdminForm(obj=new_proposal, model=new_proposal.__class__, parent=new_proposal.project)
            assert hasattr(admin_form.formlabels, label_a1.name)

            respj = c.get(new_proposal.url_for('json'))
            assert 'admin_form' in json.loads(respj.data)
            assert label_a1.form_label_text in json.loads(respj.data).get('admin_form')

            # now let's remove this label from the proposal
            respa = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [],
                    'removeLabel': [label_a1.name]
                }), content_type='application/json', follow_redirects=True)

            assert json.loads(respa.data)['status'] == 'ok'
            assert not label_a1.is_applied_to(new_proposal)

            # it should no longer load in admin form
            admin_form = ProposalLabelsAdminForm(obj=new_proposal, model=new_proposal.__class__, parent=new_proposal.project)
            assert not hasattr(admin_form.formlabels, label_a1.name)

            respj = c.get(new_proposal.url_for('json'))
            assert 'admin_form' in json.loads(respj.data)
            assert label_a1.form_label_text not in json.loads(respj.data).get('admin_form')

            # now the label can no longer be applied to a proposal
            respa = c.post(new_proposal.url_for('edit_labels'), data=json.dumps({
                    'addLabel': [label_a1.name],
                    'removeLabel': []
                }), content_type='application/json', follow_redirects=True)
            assert respa.status_code == 400
            assert json.loads(respa.data)['status'] == 'error'
            assert json.loads(respa.data)['error_description'] == "Archived labels can only be unset"
