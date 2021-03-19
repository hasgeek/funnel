from funnel.models import Comment


def test_spam_comment(db_session, user_twoflower, project_expo2010):
    not_spam = Comment(
        user=user_twoflower,
        commentset=project_expo2010.commentset,
        message="Test comment",
    )
    db_session.add(not_spam)
    db_session.commit()

    assert bool(not_spam.state.SPAM) is False
    assert str(not_spam.message) == "Test comment"

    not_spam.mark_spam()
    db_session.commit()
    spam = not_spam

    assert bool(spam.state.SPAM) is True
    assert str(spam.user) == "[removed]"
    assert str(spam.message) == "[removed]"


def test_suspended_user_comment(db_session, user_twoflower, project_expo2010):
    not_spam = Comment(
        user=user_twoflower,
        commentset=project_expo2010.commentset,
        message="Test comment 2",
    )
    db_session.add(not_spam)
    db_session.commit()

    assert bool(not_spam.state.SPAM) is False
    assert str(not_spam.message) == "Test comment 2"

    user_twoflower.mark_suspended()  # user gets suspended
    db_session.commit()
    comment_by_suspended_user = not_spam

    assert bool(comment_by_suspended_user.state.SPAM) is False  # Comment is not spam
    assert (
        str(comment_by_suspended_user.user) == "[removed]"
    )  # but the content is hidden
    assert (
        str(comment_by_suspended_user.message) == "[removed]"
    )  # but the content is hidden
