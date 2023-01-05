"""Cache refresh actions."""

from typing import Dict, List, Type, TypedDict

from flask_sqlalchemy.model import Model
from sqlalchemy.orm import composite

from flask.cli import AppGroup
import click

from .. import app, models
from ..models import db

refresh = AppGroup('refresh', help="Tasks to refresh caches")


def get_column(model: Type[Model], column_name: str) -> Type[composite]:
    return {
        '_message': lambda: model._message,  # pylint: disable=protected-access
        'description': lambda: model.description,
        'instructions': lambda: model.instructions,
        'body': lambda: model.body,
    }[column_name]()


class Field(TypedDict):
    model: Type[Model]
    fields: List[str]


FIELDS: Dict[str, Field] = {
    'comments': {'model': models.Comment, 'fields': ['_message']},
    'profiles': {'model': models.Profile, 'fields': ['description']},
    'project_documents': {
        'model': models.Project,
        'fields': ['description', 'instructions'],
    },
    'proposals': {'model': models.Proposal, 'fields': ['body']},
    'sessions': {'model': models.Session, 'fields': ['description']},
    'updates': {'model': models.Update, 'fields': ['body']},
    'venues': {'model': models.Venue, 'fields': ['description']},
    'venue_rooms': {'model': models.VenueRoom, 'fields': ['description']},
}

PROFILES: Dict[str, List[str]] = {
    'basic': ['comments', 'venues', 'venue_rooms'],
    'document': ['profiles', 'project_documents', 'proposals', 'sessions', 'updates'],
    'inline': [],
}


def reparse_markdown_field(field: Field) -> int:
    rows = field['model'].query.all()
    for o in rows:
        for field_name in field['fields']:
            item = getattr(o, field_name)
            item.text = item.text + ''
            item.changed()
    return len(rows)


@refresh.command('markdown')
@click.argument('scope', default='')
def markdown(scope) -> None:
    """Reparse markdown content."""
    message = f"""
Command to reparse markdown content.

flask refresh markdown --all:
    Reparse all markdown content site-wide.

flask refresh markdown <profile>:
    Reparse all markdown content of a particular markdown content profile site-wide.
    type = { ' | '.join(PROFILES.keys()) }.

flask refresh --url <url> (TBD):
    Reparse markdown content for the given URL.
    url should map to a valid object any of the above types.
"""
    field_list = {}
    if scope == '':
        print(message)  # noqa: T201
    elif scope == '--all':
        field_list = FIELDS
    else:
        if scope in PROFILES:
            field_list = {
                field_name: FIELDS[field_name] for field_name in PROFILES[scope]
            }
        else:
            print(message)  # noqa: T201
            return
    count = 0
    for field_name, field in field_list.items():
        c = reparse_markdown_field(field)
        print(f'Reparsed content for {c} {field_name}')  # noqa: T201
        count += c
    print(f'Total rows reparsed: {count}')  # noqa: T201
    if count > 0:
        db.session.commit()


app.cli.add_command(refresh)
