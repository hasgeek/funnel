"""Cache refresh actions."""

from __future__ import annotations

from typing import ClassVar, Dict, Generic, Iterable, List, Optional, Set, Type, TypeVar

import click
import rich.progress

from ... import models
from ...models import MarkdownModelUnion, db, sa
from . import refresh

_M = TypeVar('_M', bound=MarkdownModelUnion)


class MarkdownModel(Generic[_M]):
    """Holding class for a model that has markdown fields with custom configuration."""

    registry: ClassVar[Dict[str, MarkdownModel]] = {}
    config_registry: ClassVar[Dict[str, Set[MarkdownModel]]] = {}

    def __init__(self, model: Type[_M], fields: Set[str]) -> None:
        self.name = model.__tablename__
        self.model = model
        self.fields = fields
        self.config_fields: Dict[str, Set[str]] = {}
        for field in fields:
            config = getattr(model, field).original_property.composite_class.config.name
            self.config_fields.setdefault(config, set()).add(field)

    @classmethod
    def register(cls, model: Type[_M], fields: Set[str]) -> None:
        """Create an instance and add it to the registry."""
        obj = cls(model, fields)
        for config in obj.config_fields:
            cls.config_registry.setdefault(config, set()).add(obj)
        cls.registry[obj.name] = obj

    def reparse(self, config: Optional[str] = None, obj: Optional[_M] = None) -> None:
        """Reparse Markdown fields, optionally for a single config profile."""
        if config and config not in self.config_fields:
            return
        if config:
            fields = self.config_fields[config]
        else:
            fields = self.fields

        iter_list: Iterable[_M]

        if obj is not None:
            iter_list = [obj]
            iter_total = 1
        else:
            load_columns = (
                [self.model.id]
                + [getattr(self.model, f'{field}_text'.lstrip('_')) for field in fields]
                + [getattr(self.model, f'{field}_html'.lstrip('_')) for field in fields]
            )
            iter_list = (
                self.model.query.order_by(self.model.id)
                .options(sa.orm.load_only(*load_columns))
                .yield_per(10)
            )
            iter_total = self.model.query.count()

        for item in rich.progress.track(
            iter_list, description=self.name, total=iter_total
        ):
            for field in fields:
                setattr(item, field, getattr(item, field).text)

        # Save after reparsing
        with rich.progress.Progress(
            rich.progress.SpinnerColumn(),
            rich.progress.TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("saving...")
            db.session.commit()


MarkdownModel.register(models.Comment, {'_message'})
MarkdownModel.register(models.Account, {'description'})
MarkdownModel.register(models.Project, {'description', 'instructions'})
MarkdownModel.register(models.Proposal, {'body'})
MarkdownModel.register(models.Session, {'description'})
MarkdownModel.register(models.Update, {'body'})
MarkdownModel.register(models.Venue, {'description'})
MarkdownModel.register(models.VenueRoom, {'description'})


@refresh.command('markdown')
@click.argument(
    'content', type=click.Choice(list(MarkdownModel.registry.keys())), nargs=-1
)
@click.option(
    '-a',
    '--all',
    'allcontent',
    is_flag=True,
    help="Reparse all Markdown content (use with caution).",
)
@click.option(
    '-c',
    '--config',
    type=click.Choice(list(MarkdownModel.config_registry.keys())),
    help="Reparse Markdown content using a specific configuration.",
)
@click.option(
    '-u',
    '--url',
    help="Reparse content at this URL",
)
def markdown(
    content: List[str], config: Optional[str], allcontent: bool, url: Optional[str]
) -> None:
    """Reparse Markdown content."""
    if allcontent:
        if config or content or url:
            raise click.BadOptionUsage(
                'allcontent',
                "The --all option overrides other options and must be used standalone",
            )
        for mm in MarkdownModel.registry.values():
            mm.reparse()
    else:
        if url:
            raise click.BadOptionUsage('url', "URL refresh is not supported yet.")
        if content:
            for model in content:
                MarkdownModel.registry[model].reparse()
        if config:
            for mm in MarkdownModel.config_registry[config]:
                mm.reparse(config)
    if not (allcontent or config or content or url):
        click.echo("Specify content, --config <name>, --url <url>, or --all")
