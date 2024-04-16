"""Tests for commentsets."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from funnel import models

from ...conftest import scoped_session


@pytest.fixture
def comment1(
    db_session: scoped_session,
    project_expo2010: models.Project,
    user_rincewind: models.User,
) -> models.Comment:
    """Test comment 1."""
    c = models.Comment(
        posted_by=user_rincewind,
        commentset=project_expo2010.commentset,
        message="Test message 1",
    )
    db_session.add(c)
    db_session.commit()
    return c


@pytest.fixture
def comment2(
    db_session: scoped_session,
    project_expo2010: models.Project,
    user_rincewind: models.User,
) -> models.Comment:
    """Test comment 2."""
    c = models.Comment(
        posted_by=user_rincewind,
        commentset=project_expo2010.commentset,
        message="Test message 2",
    )
    db_session.add(c)
    db_session.commit()
    return c


def test_comment_delete_does_not_cascade_to_commentset(
    db_session: scoped_session,
    project_expo2010: models.Project,
    comment1: models.Comment,
    comment2: models.Comment,
) -> None:
    """Deleting a comment does not remove the commentset."""
    commentset_id = project_expo2010.commentset_id
    db_session.delete(comment2)
    db_session.commit()
    commentset = models.Commentset.query.get(commentset_id)
    assert commentset is not None
    assert commentset.id == commentset_id
    assert commentset == project_expo2010.commentset
    assert list(commentset.comments) == [comment1]


def test_commentset_cannot_be_deleted(db_session, project_expo2010) -> None:
    """Commentset cannot be deleted directly."""
    db_session.commit()  # Commit project_expo2010 and its commentset
    db_session.delete(project_expo2010.commentset)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_commentset_delete_cascades_to_comments(
    db_session: scoped_session,
    project_expo2010: models.Project,
    comment1: models.Comment,
    comment2: models.Comment,
) -> None:
    """Deleting a commentset (via its host) also removes comments."""
    commentset_id = project_expo2010.commentset_id
    commentset = models.Commentset.query.get(commentset_id)
    comment1_id = comment1.id
    comment1_reload = models.Comment.query.get(comment1_id)
    comment2_id = comment2.id
    comment2_reload = models.Comment.query.get(comment2_id)
    assert commentset is not None
    assert comment1_reload is not None
    assert comment2_reload is not None

    db_session.delete(project_expo2010)
    db_session.commit()

    commentset = models.Commentset.query.get(commentset_id)
    comment1_reload = models.Comment.query.get(comment1_id)
    comment2_reload = models.Comment.query.get(comment2_id)
    assert commentset is None
    assert comment1_reload is None
    assert comment2_reload is None
