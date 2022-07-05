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

model_useremail_new = model_signals.signal('model-useremail-new')
model_useremail_edited = model_signals.signal('model-useremail-edited')
model_useremail_deleted = model_signals.signal('model-useremail-deleted')

model_useremailclaim_new = model_signals.signal('model-useremail-new')
model_useremailclaim_edited = model_signals.signal('model-useremail-edited')
model_useremailclaim_deleted = model_signals.signal('model-useremail-deleted')

model_userphone_new = model_signals.signal('model-useremail-new')
model_userphone_edited = model_signals.signal('model-useremail-edited')
model_userphone_deleted = model_signals.signal('model-useremail-deleted')

model_userphoneclaim_new = model_signals.signal('model-useremail-new')
model_userphoneclaim_edited = model_signals.signal('model-useremail-edited')
model_userphoneclaim_deleted = model_signals.signal('model-useremail-deleted')

resource_access_granted = model_signals.signal('resource-access-granted')

emailaddress_refcount_dropping = model_signals.signal(
    'emailaddress-refcount-dropping',
    doc="Signal indicating that an EmailAddress's refcount is about to drop",
)

# Higher level signals
user_login = app_signals.signal('user-login')
user_registered = app_signals.signal('user-registered')
user_data_changed = app_signals.signal('user-data-changed')
org_data_changed = app_signals.signal('org-data-changed')
team_data_changed = app_signals.signal('team-data-changed')
session_revoked = app_signals.signal('session-revoked')

# Membership signals
project_crew_membership_added = app_signals.signal('project_crew_membership_added')
project_crew_membership_invited = app_signals.signal('project_crew_membership_invited')
project_crew_membership_revoked = app_signals.signal('project_crew_membership_revoked')

# Commentset role change signals (sends user, document)
project_role_change = app_signals.signal('project_role_change')
proposal_role_change = app_signals.signal('proposal_role_change')
