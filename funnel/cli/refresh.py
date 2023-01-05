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
@click.argument('profile', type=click.Choice(PROFILES.keys()), required=False)
@click.option(
    '--all',
    'all_profiles',
    is_flag=True,
    help='Reparse all markdown content site-wide.',
)
@click.option(
    '--url',
    help='Reparse markdown content for the given URL.',
)
def markdown(profile, all_profiles, url) -> None:
    """Reparse markdown content."""
    field_list = {}
    if profile is None and not all_profiles and url is None:
        print('Please specify content profile or URL.')  # noqa: T201
        return
    if all_profiles:
        field_list = FIELDS
    elif url is not None:
        pass
    else:
        field_list = {
            field_name: FIELDS[field_name] for field_name in PROFILES[profile]
        }
    count = 0
    for field_name, field in field_list.items():
        c = reparse_markdown_field(field)
        print(f'Reparsed content for {c} {field_name}')  # noqa: T201
        count += c
    print(f'Total rows reparsed: {count}')  # noqa: T201
    if count > 0:
        db.session.commit()


app.cli.add_command(refresh)
