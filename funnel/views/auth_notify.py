from ..jobs import send_auth_client_notice
from ..models import AuthToken
from ..signals import (
    org_data_changed,
    session_revoked,
    team_data_changed,
    user_data_changed,
)

user_changes_to_notify = {
    'merge',
    'profile',
    'email',
    'email-claim',
    'email-delete',
    'email-update-primary',
    'phone',
    'phone-claim',
    'phone-delete',
    'team-membership',
}


@session_revoked.connect
def notify_session_revoked(session):
    for auth_client in session.auth_clients:
        if auth_client.notification_uri:
            send_auth_client_notice.queue(
                auth_client.notification_uri,
                data={
                    'userid': session.user.buid,  # XXX: Deprecated parameter
                    'buid': session.user.buid,
                    'type': 'user',
                    'changes': ['logout'],
                    'sessionid': session.buid,
                },
            )


@user_data_changed.connect
def notify_user_data_changed(user, changes):
    """
    Look for changes that need to be notified to client apps,
    then look for apps that have user data and accept notifications,
    and then notify them.
    """
    if user_changes_to_notify & set(changes):
        # We have changes that apps need to hear about
        for token in user.authtokens:
            if token.is_valid() and token.auth_client.notification_uri:
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
                        'phone-claim',
                        'phone-delete',
                        'phone-update-primary',
                    ]:
                        if {'phone', 'phone/*'}.intersection(tokenscope):
                            notify_changes.append(change)
                    elif change in ['team-membership']:
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
def notify_org_data_changed(org, user, changes, team=None):
    """
    Like :func:`notify_user_data_changed`, except we'll also look at
    all other owners of this org to find apps that need to be notified.
    """
    client_users = {}
    for token in AuthToken.all(users=org.admin_users):
        if (
            {'*', 'organizations', 'organizations/*'}.intersection(
                token.effective_scope
            )
            and token.auth_client.notification_uri
            and token.is_valid()
        ):
            client_users.setdefault(token.auth_client, []).append(token.user)
    # Now we have a list of clients to notify and a list of users to notify them with
    for auth_client, users in client_users.items():
        if user is not None and user in users:
            notify_user = user
        else:
            notify_user = users[0]  # First user available
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
def notify_team_data_changed(team, user, changes):
    """
    Pass-through function that calls :func:`notify_org_data_changed`.
    """
    notify_org_data_changed(
        team.organization, user=user, changes=['team-' + c for c in changes], team=team
    )
