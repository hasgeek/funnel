"""Legacy handlers for notifying auth clients of user data changes (deprecated)."""

from __future__ import annotations

from typing import Optional

from ..models import Account, AuthToken, LoginSession, Organization, Team
from ..signals import (
    org_data_changed,
    session_revoked,
    team_data_changed,
    user_data_changed,
)
from .jobs import send_auth_client_notice

user_changes_to_notify = {
    'merge',
    'profile',
    'email',
    'email-claim',
    'email-delete',
    'email-update-primary',
    'phone',
    'phone-delete',
    'team-membership',
}


@session_revoked.connect
def notify_session_revoked(session: LoginSession) -> None:
    for auth_client in session.auth_clients:
        if auth_client.trusted and auth_client.notification_uri:
            send_auth_client_notice.queue(
                auth_client.notification_uri,
                data={
                    'userid': session.account.buid,  # XXX: Deprecated parameter
                    'buid': session.account.buid,
                    'type': 'user',
                    'changes': ['logout'],
                    'sessionid': session.buid,
                },
            )


@user_data_changed.connect
def notify_user_data_changed(user: Account, changes) -> None:
    """Send notifications to trusted auth clients about relevant user data changes."""
    if user_changes_to_notify & set(changes):
        # We have changes that apps need to hear about
        for token in user.authtokens:
            if (
                token.auth_client.trusted
                and token.is_valid()
                and token.auth_client.notification_uri
            ):
                tokenscope = token.effective_scope
                notify_changes = []
                for change in changes:
                    if change in ['merge', 'profile']:
                        notify_changes.append(change)
                    elif change in [
                        'email',
                        'email-claim',
                        'email-delete',
                        'email-update-primary',
                    ]:
                        if {'email', 'email/*'}.intersection(tokenscope):
                            notify_changes.append(change)
                    elif change in [
                        'phone',
                        'phone-delete',
                        'phone-update-primary',
                    ]:
                        if {'phone', 'phone/*'}.intersection(tokenscope):
                            notify_changes.append(change)
                    elif change in ['team-membership']:  # skipcq: PTC-W0048
                        if {
                            'organizations',
                            'organizations/*',
                            'teams',
                            'teams/*',
                        }.intersection(tokenscope):
                            notify_changes.append(change)
                if notify_changes:
                    send_auth_client_notice.queue(
                        token.auth_client.notification_uri,
                        data={
                            'userid': user.buid,  # XXX: Deprecated parameter
                            'buid': user.buid,
                            'type': 'user',
                            'changes': notify_changes,
                        },
                    )


@org_data_changed.connect
def notify_org_data_changed(
    org: Organization, user: Account, changes, team: Optional[Team] = None
) -> None:
    """
    Send notifications to trusted auth clients about org data changes.

    Like :func:`notify_user_data_changed`, except also looks at all other owners of this
    org to find apps that need to be notified.
    """
    client_users = {}
    for token in AuthToken.all(accounts=org.admin_users):
        if (
            token.auth_client.trusted
            and token.is_valid()
            and {'*', 'organizations', 'organizations/*'}.intersection(
                token.effective_scope
            )
            and token.auth_client.notification_uri
        ):
            client_users.setdefault(token.auth_client, []).append(token.effective_user)
    # Now we have a list of clients to notify and a list of users to notify them with
    for auth_client, users in client_users.items():
        if user is not None and user in users:
            notify_user = user
        else:
            notify_user = users[0]  # First user available
        if auth_client.trusted:
            send_auth_client_notice.queue(
                auth_client.notification_uri,
                data={
                    'userid': notify_user.buid,  # XXX: Deprecated parameter
                    'buid': notify_user.buid,
                    'type': 'org' if team is None else 'team',
                    'orgid': org.buid,
                    'teamid': team.buid if team is not None else None,
                    'changes': changes,
                },
            )


@team_data_changed.connect
def notify_team_data_changed(team: Team, user: Account, changes) -> None:
    """Notify :func:`notify_org_data_changed` for changes to the team."""
    notify_org_data_changed(
        team.account, user=user, changes=['team-' + c for c in changes], team=team
    )
