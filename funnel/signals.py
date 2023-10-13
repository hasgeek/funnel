"""
Signals to communicate between internal parts of the app (deprecated).

This is an older system and relatively unused in newer code as the signalling system is
not type-friendly.
"""

from __future__ import annotations

from flask.signals import Namespace

model_signals = Namespace()
app_signals = Namespace()

model_user_new = model_signals.signal('model-user-new')
model_user_edited = model_signals.signal('model-user-edited')
model_user_deleted = model_signals.signal('model-user-deleted')

model_org_new = model_signals.signal('model-org-new')
model_org_edited = model_signals.signal('model-org-edited')
model_org_deleted = model_signals.signal('model-org-deleted')

model_team_new = model_signals.signal('model-team-new')
model_team_edited = model_signals.signal('model-team-edited')
model_team_deleted = model_signals.signal('model-team-deleted')

model_accountemail_new = model_signals.signal('model-accountemail-new')
model_accountemail_edited = model_signals.signal('model-accountemail-edited')
model_accountemail_deleted = model_signals.signal('model-accountemail-deleted')

model_accountemailclaim_new = model_signals.signal('model-accountemailclaim-new')
model_accountemailclaim_edited = model_signals.signal('model-accountemailclaim-edited')
model_accountemailclaim_deleted = model_signals.signal(
    'model-accountemailclaim-deleted'
)

model_accountphone_new = model_signals.signal('model-accountphone-new')
model_accountphone_edited = model_signals.signal('model-accountphone-edited')
model_accountphone_deleted = model_signals.signal('model-accountphone-deleted')

resource_access_granted = model_signals.signal('resource-access-granted')

emailaddress_refcount_dropping = model_signals.signal(
    'emailaddress-refcount-dropping',
    doc="Signal indicating that an EmailAddress’s refcount is about to drop",
)
phonenumber_refcount_dropping = model_signals.signal(
    'phonenumber-refcount-dropping',
    doc="Signal indicating that a PhoneNumber’s refcount is about to drop",
)

# Higher level signals
user_login = app_signals.signal('user-login')
user_registered = app_signals.signal('user-registered')
user_data_changed = app_signals.signal('user-data-changed')
org_data_changed = app_signals.signal('org-data-changed')
team_data_changed = app_signals.signal('team-data-changed')
session_revoked = app_signals.signal('session-revoked')
project_data_change = app_signals.signal('project_data_change')

# Commentset role change signals (sends user, document)
project_role_change = app_signals.signal('project_role_change')
proposal_role_change = app_signals.signal('proposal_role_change')
