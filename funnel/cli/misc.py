"""Miscellaneous CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from dotenv import dotenv_values

from baseframe import baseframe_translations

from .. import app, models
from ..models import db


@app.shell_context_processor
def shell_context() -> dict[str, Any]:
    """Insert variables into flask shell locals."""
    return {'db': db, 'models': models}


@app.cli.command('dbconfig')
def dbconfig() -> None:
    """Show required database configuration."""
    click.echo(
        '''
-- Pipe this into psql as a super user. Example:
-- flask dbconfig | sudo -u postgres psql funnel

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS hll;
'''
    )


@app.cli.command('dbcreate')
def dbcreate() -> None:
    """Populate database schema."""
    db.create_all()
    db.session.commit()


@app.cli.command('baseframe_translations_path')
def baseframe_translations_path() -> None:
    """Show path to Baseframe translations."""
    click.echo(list(baseframe_translations.translation_directories)[0])


@app.cli.command('checkenv')
@click.argument('file', type=click.Path(exists=True, path_type=Path), default='.env')
def check_env(file: Path) -> None:
    """Compare environment file with sample.env and lists variables that do not exist."""
    env = dotenv_values(file)
    for var in dotenv_values('sample.env'):
        if var not in env:
            click.echo(var + ' does not exist')
