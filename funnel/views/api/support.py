"""Support API, internal use only."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, Tuple

from flask import abort, request

from baseframe import _
from coaster.views import requestform

from ... import app
from ...models import PhoneNumber, parse_phone_number
from ...typing import P, T


def requires_support_auth_token(f: Callable[P, T]) -> Callable[P, T]:
    """Check for support API token before accepting the request."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        """Wrap a view."""
        api_key = app.config.get('INTERNAL_SUPPORT_API_KEY')
        if not api_key:
            abort(501, description=_("API key is not configured"))
        if request.headers.get('Authorization') != f'Bearer {api_key}':
            abort(403)
        return f(*args, **kwargs)

    return wrapper


@app.route('/api/1/support/callerid', methods=['POST'])
@requires_support_auth_token
@requestform('number')
def support_callerid(number: str) -> Tuple[Dict[str, Any], int]:
    """Retrieve information about a phone number for caller id."""
    parsed_number = parse_phone_number(number)
    if not parsed_number:
        return {
            'status': 'error',
            'error': 'invalid',
            'error_description': _("Invalid phone number"),
        }, 422
    phone_number = PhoneNumber.get(parsed_number)
    if not phone_number:
        return {
            'status': 'error',
            'error': 'unknown',
            'error_description': _("Unknown phone number"),
        }, 422

    info = {
        'number': phone_number.number,
        'created_at': phone_number.created_at,
        'active_at': phone_number.active_at,
        'is_blocked': phone_number.is_blocked,
    }
    if phone_number.used_in_account_phone:
        user_phone = phone_number.used_in_account_phone[0]
        info['account'] = {
            'title': user_phone.account.fullname,
            'name': user_phone.account.username,
        }
    return {'status': 'ok', 'result': info}, 200
    # TODO: Check in TicketParticipant.phone
