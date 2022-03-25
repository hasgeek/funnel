from flask import jsonify

from coaster.views import requestargs

from ..login_session import requires_login
from ... import app
from ...models import Profile


@app.route('/api/1/profile/autocomplete')
@requires_login
@requestargs('q')
def profile_autocomplete(q):
    return jsonify({'profile': [t.name for t in Profile.autocomplete(q)]})
