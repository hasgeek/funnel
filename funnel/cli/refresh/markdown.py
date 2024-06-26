"""Cache refresh actions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar, Generic, TypeVar

import click
import rich.progress

from ... import models
from ...models import db, sa_orm
from . import refresh

_M = TypeVar('_M', bound=models.ModelIdProtocol)


class MarkdownModel(Generic[_M]):
    """Holding class for a model that has markdown fields with custom configuration."""

    #: Dict of ``{MarkdownModel().name: MarkdownModel()}``
    registry: ClassVar[dict[str, MarkdownModel]] = {}
    #: Dict of ``{config_name: MarkdownModel()}``, where the fields on the model using
    #: that config are enumerated in :attr:`config_fields`
    config_registry: ClassVar[dict[str, set[MarkdownModel]]] = {}

    def __init__(self, model: type[_M], fields: set[str]) -> None:
        self.name = model.__tablename__
        self.model = model
        self.fields = fields
        self.config_fields: dict[str, set[str]] = {}
        for field in fields:
            config = getattr(model, field).original_property.composite_class.config.name
            self.config_fields.setdefault(config, set()).add(field)

    @classmethod
    def register(cls, model: type[_M], fields: set[str]) -> None:
        """Create an instance and add it to the registry."""
        obj = cls(model, fields)
        for config in obj.config_fields:
            cls.config_registry.setdefault(config, set()).add(obj)
        cls.registry[obj.name] = obj

    def reparse(self, config: str | None = None, obj: _M | None = None) -> None:
        """Reparse Markdown fields, optionally for a single config profile."""
        if config and config not in self.config_fields:
            return
        fields = self.config_fields[config] if config else self.fields

        iter_list: Iterable[_M]

        if obj is not None:
            iter_list = [obj]
            iter_total = 1
        else:
            load_columns = (
                [self.model.id_]
                + [getattr(self.model, f'{field}_text'.lstrip('_')) for field in fields]
                + [getattr(self.model, f'{field}_html'.lstrip('_')) for field in fields]
            )
            iter_list = (
                self.model.query.order_by(self.model.id_)
                .options(sa_orm.load_only(*load_columns))
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
    content: list[str], config: str | None, allcontent: bool, url: str | None
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
