<%!
import re

%>"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: str = ${repr(down_revision)}
branch_labels: Optional[Union[str, Tuple[str, ...]]] = ${repr(branch_labels)}
depends_on: Optional[Union[str, Tuple[str, ...]]] = ${repr(depends_on)}


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()

<%
    from flask import current_app
    if current_app.config.get('SQLALCHEMY_BINDS') is not None:
        bind_names = list(current_app.config['SQLALCHEMY_BINDS'].keys())
    else:
        bind_names = []
        get_bind_names = getattr(current_app.extensions['migrate'].db, 'bind_names', None)
        if get_bind_names:
            bind_names = get_bind_names()
    db_names = [''] + bind_names
%>

## generate an "upgrade_<xyz>() / downgrade_<xyz>()" function
## for each database bind in app config.

% for db_name in db_names:

def upgrade_${db_name}() -> None:
    % if db_name == '':
    """Upgrade default database."""
    % else
    """Upgrade ${db_name} database."""
    % endif
    ${context.get("%s_upgrades" % db_name, "pass")}


def downgrade_${db_name}() -> None:
    % if db_name == '':
    """Downgrade default database."""
    % else
    """Downgrade ${db_name} database."""
    % endif
    ${context.get("%s_downgrades" % db_name, "pass")}

% endfor
