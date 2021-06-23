"""Signals for user/org models."""

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
    model_userphoneclaim_deleted,
    model_userphoneclaim_edited,
    model_userphoneclaim_new,
)
from .user import (
    Organization,
    Team,
    User,
    UserEmail,
    UserEmailClaim,
    UserPhone,
    UserPhoneClaim,
)


@event.listens_for(User, 'after_insert')
def _user_new(mapper, connection, target):
    model_user_new.send(target)


@event.listens_for(User, 'after_update')
def _user_edited(mapper, connection, target):
    model_user_edited.send(target)


@event.listens_for(User, 'after_delete')
def _user_deleted(mapper, connection, target):
    model_user_deleted.send(target)


@event.listens_for(Organization, 'after_insert')
def _org_new(mapper, connection, target):
    model_org_new.send(target)


@event.listens_for(Organization, 'after_update')
def _org_edited(mapper, connection, target):
    model_org_edited.send(target)


@event.listens_for(Organization, 'after_delete')
def _org_deleted(mapper, connection, target):
    model_org_deleted.send(target)


@event.listens_for(Team, 'after_insert')
def _team_new(mapper, connection, target):
    model_team_new.send(target)


@event.listens_for(Team, 'after_update')
def _team_edited(mapper, connection, target):
    model_team_edited.send(target)


@event.listens_for(Team, 'after_delete')
def _team_deleted(mapper, connection, target):
    model_team_deleted.send(target)


@event.listens_for(UserEmail, 'after_insert')
def _useremail_new(mapper, connection, target):
    model_useremail_new.send(target)


@event.listens_for(UserEmail, 'after_update')
def _useremail_edited(mapper, connection, target):
    model_useremail_edited.send(target)


@event.listens_for(UserEmail, 'after_delete')
def _useremail_deleted(mapper, connection, target):
    model_useremail_deleted.send(target)


@event.listens_for(UserEmailClaim, 'after_insert')
def _useremailclaim_new(mapper, connection, target):
    model_useremailclaim_new.send(target)


@event.listens_for(UserEmailClaim, 'after_update')
def _useremailclaim_edited(mapper, connection, target):
    model_useremailclaim_edited.send(target)


@event.listens_for(UserEmailClaim, 'after_delete')
def _useremailclaim_deleted(mapper, connection, target):
    model_useremailclaim_deleted.send(target)


@event.listens_for(UserPhone, 'after_insert')
def _userphone_new(mapper, connection, target):
    model_userphone_new.send(target)


@event.listens_for(UserPhone, 'after_update')
def _userphone_edited(mapper, connection, target):
    model_userphone_edited.send(target)


@event.listens_for(UserPhone, 'after_delete')
def _userphone_deleted(mapper, connection, target):
    model_userphone_deleted.send(target)


@event.listens_for(UserPhoneClaim, 'after_insert')
def _userphoneclaim_new(mapper, connection, target):
    model_userphoneclaim_new.send(target)


@event.listens_for(UserPhoneClaim, 'after_update')
def _userphoneclaim_edited(mapper, connection, target):
    model_userphoneclaim_edited.send(target)


@event.listens_for(UserPhoneClaim, 'after_delete')
def _userphoneclaim_deleted(mapper, connection, target):
    model_userphoneclaim_deleted.send(target)
