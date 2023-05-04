"""Signals for user/org models using the older untyped Blinker system (deprecated)."""

from __future__ import annotations

from sqlalchemy import event

from ..signals import (
    model_accountemail_deleted,
    model_accountemail_edited,
    model_accountemail_new,
    model_accountemailclaim_deleted,
    model_accountemailclaim_edited,
    model_accountemailclaim_new,
    model_accountphone_deleted,
    model_accountphone_edited,
    model_accountphone_new,
    model_org_deleted,
    model_org_edited,
    model_org_new,
    model_team_deleted,
    model_team_edited,
    model_team_new,
    model_user_deleted,
    model_user_edited,
    model_user_new,
)
from .account import (
    Account,
    AccountEmail,
    AccountEmailClaim,
    AccountPhone,
    Organization,
    Team,
)


@event.listens_for(Account, 'after_insert')
def _user_new(_mapper, _connection, target):
    model_user_new.send(target)


@event.listens_for(Account, 'after_update')
def _user_edited(_mapper, _connection, target):
    model_user_edited.send(target)


@event.listens_for(Account, 'after_delete')
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


@event.listens_for(AccountEmail, 'after_insert')
def _accountemail_new(_mapper, _connection, target):
    model_accountemail_new.send(target)


@event.listens_for(AccountEmail, 'after_update')
def _accountemail_edited(_mapper, _connection, target):
    model_accountemail_edited.send(target)


@event.listens_for(AccountEmail, 'after_delete')
def _accountemail_deleted(_mapper, _connection, target):
    model_accountemail_deleted.send(target)


@event.listens_for(AccountEmailClaim, 'after_insert')
def _accountemailclaim_new(_mapper, _connection, target):
    model_accountemailclaim_new.send(target)


@event.listens_for(AccountEmailClaim, 'after_update')
def _accountemailclaim_edited(_mapper, _connection, target):
    model_accountemailclaim_edited.send(target)


@event.listens_for(AccountEmailClaim, 'after_delete')
def _accountemailclaim_deleted(_mapper, _connection, target):
    model_accountemailclaim_deleted.send(target)


@event.listens_for(AccountPhone, 'after_insert')
def _accountphone_new(_mapper, _connection, target):
    model_accountphone_new.send(target)


@event.listens_for(AccountPhone, 'after_update')
def _accountphone_edited(_mapper, _connection, target):
    model_accountphone_edited.send(target)


@event.listens_for(AccountPhone, 'after_delete')
def _accountphone_deleted(_mapper, _connection, target):
    model_accountphone_deleted.send(target)
