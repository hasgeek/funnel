"""Flask-Migrate and Alembic environment."""

from __future__ import annotations

import logging
from logging.config import fileConfig
from typing import Any

from alembic import context
from alembic.operations import MigrationScript
from flask import current_app
from sqlalchemy import MetaData

USE_TWOPHASE = False

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

config.set_main_option(
    'sqlalchemy.url',
    str(current_app.extensions['migrate'].db.engines[None].url).replace('%', '%%'),
)
bind_names: list[str] = []
if current_app.config.get('SQLALCHEMY_BINDS') is not None:
    bind_names = list(current_app.config['SQLALCHEMY_BINDS'].keys())
else:
    get_bind_names = getattr(current_app.extensions['migrate'].db, 'bind_names', None)
    if get_bind_names:
        bind_names = get_bind_names()
for this_bind in bind_names:
    context.config.set_section_option(
        this_bind,
        'sqlalchemy.url',
        str(current_app.extensions['migrate'].db.engines[this_bind].url).replace(
            '%', '%%'
        ),
    )
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py, can be acquired:
# my_important_option = config.get_main_option("my_important_option") ... etc.


def get_metadata(bind: str | None) -> MetaData:
    """Return the metadata for a bind."""
    if bind == '':
        bind = None
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[bind]

    # legacy, less flexible implementation
    m = MetaData()
    for t in target_db.metadata.tables.values():
        if t.info.get('bind_key') == bind:
            t.tometadata(m)
    return m


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an Engine is
    acceptable here as well.  By skipping the Engine creation we don't even need a DBAPI
    to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    # for the --sql use case, run migrations for each URL into
    # individual files.

    engines = {'': {'url': context.config.get_main_option('sqlalchemy.url')}}
    for name in bind_names:
        engines[name] = rec = {}
        rec['url'] = context.config.get_section_option(name, 'sqlalchemy.url')

    for name, rec in engines.items():
        logger.info("Migrating database %s", (name or '<default>'))
        file_ = f'{name}.sql'
        logger.info("Writing output to %s", file_)
        with open(file_, 'w', encoding='utf-8') as buffer:
            context.configure(
                url=rec['url'],
                output_buffer=buffer,
                target_metadata=get_metadata(name),
                literal_binds=True,
            )
            with context.begin_transaction():
                context.run_migrations(engine_name=name)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: https://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(
        _context: Any, _revision: Any, directives: list[MigrationScript]
    ) -> None:
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if len(script.upgrade_ops_list) >= len(bind_names) + 1:
                empty = True
                for upgrade_ops in script.upgrade_ops_list:
                    if not upgrade_ops.is_empty():
                        empty = False
                if empty:
                    directives[:] = []
                    logger.info("No changes in schema detected.")

    # for the direct-to-DB use case, start a transaction on all
    # engines, then run all migrations, then commit all transactions.
    engines = {'': {'engine': current_app.extensions['migrate'].db.engines[None]}}
    for name in bind_names:
        engines[name] = {'engine': current_app.extensions['migrate'].db.engines[name]}

    for rec in engines.values():
        engine = rec['engine']
        rec['connection'] = conn = engine.connect()

        if USE_TWOPHASE:
            rec['transaction'] = conn.begin_twophase()
        else:
            rec['transaction'] = conn.begin()

    try:
        if len(engines) == 1:
            # Do not pass an engine_name parameter when there is only one default bind
            # This allows legacy migrations to run before models with binds are
            # introduced.
            rec = next(iter(engines.values()))
            context.configure(
                connection=rec['connection'],
                upgrade_token='_upgrades',  # noqa: S106
                downgrade_token='_downgrades',  # noqa: S106
                target_metadata=get_metadata(''),
                process_revision_directives=process_revision_directives,
                **current_app.extensions['migrate'].configure_args,
            )
            context.run_migrations()

        else:
            for name, rec in engines.items():
                logger.info("Migrating database %s", name or '<default>')
                context.configure(
                    connection=rec['connection'],
                    upgrade_token=f'{name}_upgrades',
                    downgrade_token=f'{name}_downgrades',
                    target_metadata=get_metadata(name),
                    process_revision_directives=process_revision_directives,
                    **current_app.extensions['migrate'].configure_args,
                )
                context.run_migrations(engine_name=name)

        if USE_TWOPHASE:
            for rec in engines.values():
                rec['transaction'].prepare()

        for rec in engines.values():
            rec['transaction'].commit()
    except:
        for rec in engines.values():
            rec['transaction'].rollback()
        raise
    finally:
        for rec in engines.values():
            rec['connection'].close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
