from __future__ import annotations

from baseframe import baseframe_translations

from .. import app, models
from ..models import db


@app.shell_context_processor
def shell_context():
    """Insert variables into flask shell locals."""
    return {'db': db, 'models': models}


@app.cli.command('dbconfig')
def dbconfig():
    """Show required database configuration."""
    print(
        '''
-- Pipe this into psql as a super user. Example:
-- flask dbconfig | sudo -u postgres psql funnel

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS hll;
'''
    )


@app.cli.command('baseframe_translations_path')
def baseframe_translations_path():
    """Show path to Baseframe translations."""
    print(baseframe_translations.dirname)
