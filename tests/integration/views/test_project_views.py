# -*- coding: utf-8 -*-

from werkzeug.datastructures import MultiDict

from funnel.forms import LabelForm
from funnel.models import Label


class TestProjectViews(object):
    def test_new_label_get(self, test_client, new_user, new_project):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp = c.get(new_project.url_for('new_label'))
            label_form = LabelForm(parent=new_project, model=Label)
            for field in label_form:
                assert field.name in resp.data

    def test_new_label_without_option(self, test_client, new_user, new_project):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp_post = c.post(
                new_project.url_for('new_label'),
                data=MultiDict(
                    {
                        'title': u"Label V1",
                        'icon_emoji': u"👍",
                        'required': False,
                        'restricted': False,
                    }
                ),
                follow_redirects=True,
            )
            assert u"Manage labels" in resp_post.data.decode('utf-8')
            label_v1 = Label.query.filter_by(
                title=u"Label V1", icon_emoji=u"👍", project=new_project
            ).first()
            assert label_v1 is not None

    def test_new_label_with_option(self, test_client, new_user, new_project):
        with test_client.session_transaction() as session:
            session['lastuser_userid'] = new_user.userid
        with test_client as c:
            resp_post = c.post(
                new_project.url_for('new_label'),
                data=MultiDict(
                    {
                        'title': [u"Label V2", "Option V21", "Option V22"],
                        'icon_emoji': [u"👍", "", ""],
                        'required': False,
                        'restricted': False,
                    }
                ),
                follow_redirects=True,
            )
            assert u"Manage labels" in resp_post.data.decode('utf-8')
            label_v2 = Label.query.filter_by(
                title=u"Label V2", icon_emoji=u"👍", project=new_project
            ).first()
            assert label_v2 is not None
            assert label_v2.has_options
            assert len(label_v2.options) == 2

            assert label_v2.options[0].title == "Option V21"
            assert label_v2.options[0].icon_emoji == ""
            assert label_v2.options[0].icon == "OV"

            assert label_v2.options[1].title == "Option V22"
            assert label_v2.options[1].icon_emoji == ""
            assert label_v2.options[1].icon == "OV"
