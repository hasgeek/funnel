from flask import url_for
from werkzeug.datastructures import MultiDict

from funnel.models import (
    MODERATOR_REPORT_TYPE,
    Comment,
    CommentModeratorReport,
    SiteMembership,
)


class TestProjectViews(object):
    def test_comment_report_same(
        self,
        test_client,
        test_db,
        new_user,
        new_user2,
        new_user_admin,
        new_user_owner,
        new_project,
    ):
        # Let's give new_user site_editor role
        sm = SiteMembership(user=new_user, is_comment_moderator=True)
        sm2 = SiteMembership(user=new_user_admin, is_comment_moderator=True)
        sm3 = SiteMembership(user=new_user_owner, is_comment_moderator=True)
        test_db.session.add_all([sm, sm2, sm3])
        test_db.session.commit()

        assert new_user.is_comment_moderator is True
        assert new_user_admin.is_comment_moderator is True
        assert new_user_owner.is_comment_moderator is True

        # Let's make a comment
        comment = Comment(
            user=new_user2,
            commentset=new_project.commentset,
            message="Test comment message",
        )
        test_db.session.add(comment)
        test_db.session.commit()
        comment_id = comment.id
        assert bool(comment.state.PUBLIC) is True

        # report the comment as new_user_admin
        report1 = CommentModeratorReport(user=new_user_admin, comment=comment)
        test_db.session.add(report1)
        test_db.session.commit()
        report1_id = report1.id

        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            # if new_user also reports it as spam,
            # the report will be removed, and comment will be in Spam state
            resp_post = c.post(
                url_for('siteadmin_review_comment', report=report1.uuid_b58),
                data=MultiDict({'report_type': MODERATOR_REPORT_TYPE.SPAM}),
                follow_redirects=True,
            )
            assert (
                "There is no comment report no review at this moment"
                in resp_post.data.decode('utf-8')
            )
            comment_refetched = Comment.query.filter_by(id=comment_id).one()
            assert bool(comment_refetched.state.SPAM) is True
            # report will be deleted
            assert CommentModeratorReport.query.filter_by(id=report1_id).first() is None

    def test_comment_report_opposing(
        self,
        test_client,
        test_db,
        new_user,
        new_user2,
        new_user_admin,
        new_user_owner,
        new_project,
    ):
        # Let's make another comment
        comment2 = Comment(
            user=new_user2,
            commentset=new_project.commentset,
            message="Test second comment message",
        )
        test_db.session.add(comment2)
        test_db.session.commit()
        comment2_id = comment2.id
        assert bool(comment2.state.PUBLIC) is True

        # report the comment as new_user_admin
        report2 = CommentModeratorReport(user=new_user_admin, comment=comment2)
        test_db.session.add(report2)
        test_db.session.commit()

        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            # if new_user reports it as not a spam,
            # a new report will be created, and comment will stay in public state
            resp_post = c.post(
                url_for('siteadmin_review_comment', report=report2.uuid_b58),
                data=MultiDict({'report_type': MODERATOR_REPORT_TYPE.OK}),
                follow_redirects=True,
            )
            assert (
                "There is no comment report no review at this moment"
                in resp_post.data.decode('utf-8')
            )
            comment2_refetched = Comment.query.filter_by(id=comment2_id).one()
            assert bool(comment2_refetched.state.SPAM) is False
            assert bool(comment2_refetched.state.PUBLIC) is True
            # a new report will be created
            assert (
                CommentModeratorReport.query.filter_by(
                    comment=comment2_refetched,
                    user=new_user,
                    report_type=MODERATOR_REPORT_TYPE.OK,
                ).one()
                is not None
            )

    def test_comment_report_majority_spam(
        self,
        test_client,
        test_db,
        new_user,
        new_user2,
        new_user_admin,
        new_user_owner,
        new_project,
    ):
        # Let's make another comment
        comment3 = Comment(
            user=new_user2,
            commentset=new_project.commentset,
            message="Test second comment message",
        )
        test_db.session.add(comment3)
        test_db.session.commit()
        comment3_id = comment3.id
        assert bool(comment3.state.PUBLIC) is True

        # report the comment as spam as new_user_admin
        report3 = CommentModeratorReport(user=new_user_admin, comment=comment3)
        test_db.session.add(report3)
        test_db.session.commit()
        report3_id = report3.id

        # report the comment as not spam as new_user_owner
        report4 = CommentModeratorReport(
            user=new_user_owner, comment=comment3, report_type=MODERATOR_REPORT_TYPE.OK
        )
        test_db.session.add(report4)
        test_db.session.commit()
        report4_id = report4.id

        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            # if new_user reports it as a spam,
            # the comment will be marked as spam as that's the majority vote
            resp_post = c.post(
                url_for('siteadmin_review_comment', report=report3.uuid_b58),
                data=MultiDict({'report_type': MODERATOR_REPORT_TYPE.SPAM}),
                follow_redirects=True,
            )
            assert (
                "There is no comment report no review at this moment"
                in resp_post.data.decode('utf-8')
            )
            comment3_refetched = Comment.query.filter_by(id=comment3_id).one()
            assert bool(comment3_refetched.state.SPAM) is True
            # the reports will be deleted
            assert CommentModeratorReport.query.filter_by(id=report3_id).first() is None
            assert CommentModeratorReport.query.filter_by(id=report4_id).first() is None

    def test_comment_report_majority_ok(
        self,
        test_client,
        test_db,
        new_user,
        new_user2,
        new_user_admin,
        new_user_owner,
        new_project,
    ):
        # Let's make another comment
        comment4 = Comment(
            user=new_user2,
            commentset=new_project.commentset,
            message="Test second comment message",
        )
        test_db.session.add(comment4)
        test_db.session.commit()
        comment4_id = comment4.id
        assert bool(comment4.state.PUBLIC) is True

        # report the comment as spam as new_user_admin
        report5 = CommentModeratorReport(user=new_user_admin, comment=comment4)
        test_db.session.add(report5)
        test_db.session.commit()
        report5_id = report5.id

        # report the comment as not spam as new_user_owner
        report6 = CommentModeratorReport(
            user=new_user_owner, comment=comment4, report_type=MODERATOR_REPORT_TYPE.OK
        )
        test_db.session.add(report6)
        test_db.session.commit()
        report6_id = report6.id

        with test_client.session_transaction() as session:
            session['userid'] = new_user.userid
        with test_client as c:
            # if new_user reports it as not a spam,
            # the comment will not be marked as spam as that's the majority vote,
            # but all the reports will be deleted
            resp_post = c.post(
                url_for('siteadmin_review_comment', report=report5.uuid_b58),
                data=MultiDict({'report_type': MODERATOR_REPORT_TYPE.OK}),
                follow_redirects=True,
            )
            assert (
                "There is no comment report no review at this moment"
                in resp_post.data.decode('utf-8')
            )
            comment4_refetched = Comment.query.filter_by(id=comment4_id).one()
            assert bool(comment4_refetched.state.PUBLIC) is True
            # the reports will be deleted
            assert CommentModeratorReport.query.filter_by(id=report5_id).first() is None
            assert CommentModeratorReport.query.filter_by(id=report6_id).first() is None
