from flask import url_for
from werkzeug.datastructures import MultiDict

from funnel.models import (
    MODERATOR_REPORT_TYPE,
    Comment,
    CommentModeratorReport,
    SiteMembership,
)


def test_comment_report_same(
    client,
    db_session,
    new_user,
    new_user2,
    new_user_admin,
    new_user_owner,
    new_project,
):
    # Let's give new_user site_editor role
    sm = SiteMembership(user=new_user, is_comment_moderator=True, granted_by=new_user)
    sm2 = SiteMembership(
        user=new_user_admin, is_comment_moderator=True, granted_by=new_user_admin
    )
    sm3 = SiteMembership(
        user=new_user_owner, is_comment_moderator=True, granted_by=new_user_owner
    )
    db_session.add_all([sm, sm2, sm3])
    db_session.commit()

    assert new_user.is_comment_moderator is True
    assert new_user_admin.is_comment_moderator is True
    assert new_user_owner.is_comment_moderator is True

    # Let's make a comment
    comment = Comment(
        user=new_user2,
        commentset=new_project.commentset,
        message="Test comment message",
    )
    db_session.add(comment)
    db_session.commit()
    comment_id = comment.id
    assert bool(comment.state.PUBLIC) is True

    # report the comment as new_user_admin
    report1, created = CommentModeratorReport.submit(
        actor=new_user_admin, comment=comment
    )
    if created:
        db_session.commit()
    report1_id = report1.id

    assert comment.is_reviewed_by(new_user_admin)

    with client.session_transaction() as session:
        session['userid'] = new_user.userid

    # if new_user also reports it as spam,
    # the report will be removed, and comment will be in Spam state
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    resp_post = client.post(
        url_for('siteadmin_review_comment', report=report1.uuid_b58),
        data=MultiDict(
            {'csrf_token': csrf_token, 'report_type': MODERATOR_REPORT_TYPE.SPAM}
        ),
        follow_redirects=True,
    )
    assert (
        "There are no comment reports to review at this time"
        in resp_post.data.decode('utf-8')
    )
    comment_refetched = Comment.query.filter_by(id=comment_id).one()
    assert bool(comment_refetched.state.SPAM) is True
    # report will be deleted
    assert (
        CommentModeratorReport.query.filter_by(id=report1_id, resolved_at=None).first()
        is None
    )


def test_comment_report_opposing(
    client,
    db_session,
    new_user,
    new_user2,
    new_user_admin,
    new_user_owner,
    new_project,
):
    # Let's give new_user site_editor role
    sm = SiteMembership(user=new_user, is_comment_moderator=True, granted_by=new_user)
    sm2 = SiteMembership(
        user=new_user_admin, is_comment_moderator=True, granted_by=new_user_admin
    )
    sm3 = SiteMembership(
        user=new_user_owner, is_comment_moderator=True, granted_by=new_user_owner
    )
    db_session.add_all([sm, sm2, sm3])
    db_session.commit()

    assert new_user.is_comment_moderator is True
    assert new_user_admin.is_comment_moderator is True
    assert new_user_owner.is_comment_moderator is True

    # Let's make another comment
    comment2 = Comment(
        user=new_user2,
        commentset=new_project.commentset,
        message="Test second comment message",
    )
    db_session.add(comment2)
    db_session.commit()
    comment2_id = comment2.id
    assert bool(comment2.state.PUBLIC) is True

    # report the comment as new_user_admin
    report2, created = CommentModeratorReport.submit(
        actor=new_user_admin, comment=comment2
    )
    if created:
        db_session.commit()

    with client.session_transaction() as session:
        session['userid'] = new_user.userid
    # if new_user reports it as not a spam,
    # a new report will be created, and comment will stay in public state
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    resp_post = client.post(
        url_for('siteadmin_review_comment', report=report2.uuid_b58),
        data=MultiDict(
            {'csrf_token': csrf_token, 'report_type': MODERATOR_REPORT_TYPE.OK}
        ),
        follow_redirects=True,
    )
    assert (
        "There are no comment reports to review at this time"
        in resp_post.data.decode('utf-8')
    )
    comment2_refetched = Comment.query.filter_by(id=comment2_id).one()
    assert bool(comment2_refetched.state.SPAM) is False
    assert bool(comment2_refetched.state.PUBLIC) is True
    # a new report will be created
    assert comment2_refetched.is_reviewed_by(new_user)
    assert (
        CommentModeratorReport.query.filter_by(
            comment=comment2_refetched,
            user=new_user,
            report_type=MODERATOR_REPORT_TYPE.OK,
        ).one()
        is not None
    )


def test_comment_report_majority_spam(
    client,
    db_session,
    new_user,
    new_user2,
    new_user_admin,
    new_user_owner,
    new_project,
):
    # Let's give new_user site_editor role
    sm = SiteMembership(user=new_user, is_comment_moderator=True, granted_by=new_user)
    sm2 = SiteMembership(
        user=new_user_admin, is_comment_moderator=True, granted_by=new_user_admin
    )
    sm3 = SiteMembership(
        user=new_user_owner, is_comment_moderator=True, granted_by=new_user_owner
    )
    db_session.add_all([sm, sm2, sm3])
    db_session.commit()

    assert new_user.is_comment_moderator is True
    assert new_user_admin.is_comment_moderator is True
    assert new_user_owner.is_comment_moderator is True

    # Let's make another comment
    comment3 = Comment(
        user=new_user2,
        commentset=new_project.commentset,
        message="Test second comment message",
    )
    db_session.add(comment3)
    db_session.commit()
    comment3_id = comment3.id
    assert bool(comment3.state.PUBLIC) is True

    # report the comment as spam as new_user_admin
    report3, created = CommentModeratorReport.submit(
        actor=new_user_admin, comment=comment3
    )
    if created:
        db_session.commit()
    report3_id = report3.id

    # report the comment as not spam as new_user_owner
    report4 = CommentModeratorReport(
        user=new_user_owner, comment=comment3, report_type=MODERATOR_REPORT_TYPE.OK
    )
    db_session.add(report4)
    db_session.commit()
    report4_id = report4.id

    with client.session_transaction() as session:
        session['userid'] = new_user.userid
    # if new_user reports it as a spam,
    # the comment will be marked as spam as that's the majority vote
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    resp_post = client.post(
        url_for('siteadmin_review_comment', report=report3.uuid_b58),
        data=MultiDict(
            {'csrf_token': csrf_token, 'report_type': MODERATOR_REPORT_TYPE.SPAM}
        ),
        follow_redirects=True,
    )
    assert (
        "There are no comment reports to review at this time"
        in resp_post.data.decode('utf-8')
    )
    comment3_refetched = Comment.query.filter_by(id=comment3_id).one()
    assert bool(comment3_refetched.state.SPAM) is True
    # the reports will be deleted
    assert (
        CommentModeratorReport.query.filter_by(id=report3_id, resolved_at=None).first()
        is None
    )
    assert (
        CommentModeratorReport.query.filter_by(id=report4_id, resolved_at=None).first()
        is None
    )


def test_comment_report_majority_ok(
    client,
    db_session,
    new_user,
    new_user2,
    new_user_admin,
    new_user_owner,
    new_project,
):
    # Let's give new_user site_editor role
    sm = SiteMembership(user=new_user, is_comment_moderator=True, granted_by=new_user)
    sm2 = SiteMembership(
        user=new_user_admin, is_comment_moderator=True, granted_by=new_user_admin
    )
    sm3 = SiteMembership(
        user=new_user_owner, is_comment_moderator=True, granted_by=new_user_owner
    )
    db_session.add_all([sm, sm2, sm3])
    db_session.commit()

    assert new_user.is_comment_moderator is True
    assert new_user_admin.is_comment_moderator is True
    assert new_user_owner.is_comment_moderator is True

    # Let's make another comment
    comment4 = Comment(
        user=new_user2,
        commentset=new_project.commentset,
        message="Test second comment message",
    )
    db_session.add(comment4)
    db_session.commit()
    comment4_id = comment4.id
    assert bool(comment4.state.PUBLIC) is True

    # report the comment as spam as new_user_admin
    report5, created = CommentModeratorReport.submit(
        actor=new_user_admin, comment=comment4
    )
    if created:
        db_session.commit()
    report5_id = report5.id

    # report the comment as not spam as new_user_owner
    report6 = CommentModeratorReport(
        user=new_user_owner, comment=comment4, report_type=MODERATOR_REPORT_TYPE.OK
    )
    db_session.add(report6)
    db_session.commit()
    report6_id = report6.id

    with client.session_transaction() as session:
        session['userid'] = new_user.userid
    # if new_user reports it as not a spam,
    # the comment will not be marked as spam as that's the majority vote,
    # but all the reports will be deleted
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    resp_post = client.post(
        url_for('siteadmin_review_comment', report=report5.uuid_b58),
        data=MultiDict(
            {'csrf_token': csrf_token, 'report_type': MODERATOR_REPORT_TYPE.OK}
        ),
        follow_redirects=True,
    )
    assert (
        "There are no comment reports to review at this time"
        in resp_post.data.decode('utf-8')
    )
    comment4_refetched = Comment.query.filter_by(id=comment4_id).one()
    assert bool(comment4_refetched.state.PUBLIC) is True
    # the reports will be deleted
    assert (
        CommentModeratorReport.query.filter_by(id=report5_id, resolved_at=None).first()
        is None
    )
    assert (
        CommentModeratorReport.query.filter_by(id=report6_id, resolved_at=None).first()
        is None
    )
