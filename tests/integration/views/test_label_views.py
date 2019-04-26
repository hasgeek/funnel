# -*- coding: utf-8 -*-

from funnel.models import Label


class TestLabelViews(object):
    def test_label_archive(self, test_client, test_db, new_user, new_label):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp = c.post(new_label.url_for('archive'), follow_redirects=True)
            label = Label.query.get(new_label.id)
            assert u"Manage labels" in resp.data.decode('utf-8')
            assert u"The label has been archived" in resp.data.decode('utf-8')
            assert label.archived is True
