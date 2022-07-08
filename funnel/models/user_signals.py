"""Signals for user/org models using the older untyped Blinker system (deprecated)."""

from __future__ import annotations

from sqlalchemy import event

from ..signals import (
    model_org_deleted,
    model_org_edited,
    model_org_new,
    model_team_deleted,
    model_team_edited,
    model_team_new,
    model_user_deleted,
    model_user_edited,
    model_user_new,
    model_useremail_deleted,
    model_useremail_edited,
    model_useremail_new,
    model_useremailclaim_deleted,
    model_useremailclaim_edited,
    model_useremailclaim_new,
    model_userphone_deleted,
    model_userphone_edited,
    model_userphone_new,
    user_data_changed,
)
from .user import Organization, Team, User, UserEmail, UserEmailClaim, UserPhone


@event.listens_for(User, 'after_insert')
def _user_new(_mapper, _connection, target):
    model_user_new.send(target)


@event.listens_for(User, 'after_update')
def _user_edited(_mapper, _connection, target):
    model_user_edited.send(target)


@event.listens_for(User, 'after_delete')
def _user_deleted(_mapper, _connection, target):
    model_user_deleted.send(target)


@event.listens_for(Organization, 'after_insert')
def _org_new(_mapper, _connection, target):
    model_org_new.send(target)


@event.listens_for(Organization, 'after_update')
def _org_edited(_mapper, _connection, target):
    model_org_edited.send(target)


@event.listens_for(Organization, 'after_delete')
def _org_deleted(_mapper, _connection, target):
    model_org_deleted.send(target)


@event.listens_for(Team, 'after_insert')
def _team_new(_mapper, _connection, target):
    model_team_new.send(target)


@event.listens_for(Team, 'after_update')
def _team_edited(_mapper, _connection, target):
    model_team_edited.send(target)


@event.listens_for(Team, 'after_delete')
def _team_deleted(_mapper, _connection, target):
    model_team_deleted.send(target)


@event.listens_for(UserEmail, 'after_insert')
def _useremail_new(_mapper, _connection, target):
    model_useremail_new.send(target)


@event.listens_for(UserEmail, 'after_update')
def _useremail_edited(_mapper, _connection, target):
    model_useremail_edited.send(target)


@event.listens_for(UserEmail, 'after_delete')
def _useremail_deleted(_mapper, _connection, target):
    model_useremail_deleted.send(target)
    user_data_changed.send(target.user, changes=['email-delete'])


@event.listens_for(UserEmailClaim, 'after_insert')
def _useremailclaim_new(_mapper, _connection, target):
    model_useremailclaim_new.send(target)


@event.listens_for(UserEmailClaim, 'after_update')
def _useremailclaim_edited(_mapper, _connection, target):
    model_useremailclaim_edited.send(target)


@event.listens_for(UserEmailClaim, 'after_delete')
def _useremailclaim_deleted(_mapper, _connection, target):
    model_useremailclaim_deleted.send(target)


@event.listens_for(UserPhone, 'after_insert')
def _userphone_new(_mapper, _connection, target):
    model_userphone_new.send(target)


@event.listens_for(UserPhone, 'after_update')
def _userphone_edited(_mapper, _connection, target):
    model_userphone_edited.send(target)


@event.listens_for(UserPhone, 'after_delete')
def _userphone_deleted(_mapper, _connection, target):
    model_userphone_deleted.send(target)
    user_data_changed.send(target.user, changes=['phone-delete'])
