# -*- coding: utf-8 -*-

from werkzeug.datastructures import MultiDict
from funnel.models import Label
from funnel.forms import LabelForm, LabelOptionForm


class TestProjectViews(object):
    def test_labels_view(self, test_client, new_user, new_project):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp = c.get(new_project.url_for('new_label'))
            label_form = LabelForm(parent=new_project, model=Label)
            for field in label_form:
                assert field.name in resp.data

            resp_post = c.post(new_project.url_for('new_label'), data=MultiDict({
                'title': u"Label V1", 'icon_emoji': u"👍",
                'required': False, 'restricted': False
            }), follow_redirects=True)
            assert u"Manage labels" in resp_post.data.decode('utf-8')
            label_v2 = Label.query.filter_by(title=u"Label V1", icon_emoji=u"👍", project=new_project).first()
            assert label_v2 is not None
