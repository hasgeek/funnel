"""Markdown parser and config profiles."""
# pylint: disable=too-many-arguments

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Union,
    overload,
)

from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins import anchors, footnote, tasklists
from typing_extensions import Literal

from coaster.utils import make_name
from coaster.utils.text import normalize_spaces_multiline

from .mdit_plugins import (  # toc_plugin,
    del_plugin,
    embeds_plugin,
    ins_plugin,
    mark_plugin,
    sub_plugin,
    sup_plugin,
)

__all__ = ['markdown', 'markdown_plugins', 'markdown_plugin_config', 'MarkdownConfig']

default_markdown_extensions: List[str] = ['footnote', 'heading_anchors', 'tasklists']

markdown_plugins: Dict[str, Callable] = {
    'footnote': footnote.footnote_plugin,
    'heading_anchors': anchors.anchors_plugin,
    'tasklists': tasklists.tasklists_plugin,
    'ins': ins_plugin,
    'del': del_plugin,
    'sub': sub_plugin,
    'sup': sup_plugin,
    'mark': mark_plugin,
    'markmap': embeds_plugin,
    'vega-lite': embeds_plugin,
    'mermaid': embeds_plugin,
    # 'toc': toc_plugin,
}

markdown_plugin_config: Dict[str, Dict[str, Any]] = {
    'heading_anchors': {
        'min_level': 1,
        'max_level': 3,
        'slug_func': lambda x, **options: 'h:' + make_name(x, **options),
        'permalink': True,
    },
    'tasklists': {'enabled': True, 'label': True, 'label_after': False},
    'markmap': {'name': 'markmap'},
    'vega-lite': {'name': 'vega-lite'},
    'mermaid': {'name': 'mermaid'},
}

OptionStrings = Literal['html', 'breaks', 'linkify', 'typographer']


@dataclass
class MarkdownConfig:
    """Markdown config metadata in a non-callable class structure."""

    #: Registry of named sub-classes
    registry: ClassVar[Dict[str, MarkdownConfig]] = {}

    #: Optional name for this config, for adding to the registry
    name: Optional[str] = None

    #: Markdown-it preset configuration
    preset: Literal['zero', 'commonmark', 'js-default', 'gfm-like'] = 'commonmark'
    #: Updated options against the preset
    options_update: Optional[Dict[OptionStrings, bool]] = None
    #: Allow only inline rules (skips all block rules)?
    inline: bool = False

    #: Use these plugins
    plugins: Iterable[str] = ()
    #: Enable these rules (provided by plugins)
    enable_rules: Optional[Set[str]] = None
    #: Disable these rules
    disable_rules: Optional[Set[str]] = None

    #: If linkify is enabled, apply to fuzzy links too?
    linkify_fuzzy_link: bool = False
    #: If linkify is enabled, make email links too?
    linkify_fuzzy_email: bool = False

    def __post_init__(self):
        for ext in self.plugins:
            if ext not in markdown_plugins:
                raise TypeError(f"Unknown Markdown plugin {ext}")

        # If this configuration has a name, add it to the registry
        if self.name is not None:
            self.registry[self.name] = self


MarkdownConfig(name='basic', options_update={'html': False, 'breaks': True})
MarkdownConfig(
    name='document',
    preset='gfm-like',
    options_update={
        'html': False,
        'linkify': True,
        'typographer': True,
        'breaks': True,
    },
    plugins={
        'footnote',
        'heading_anchors',
        'tasklists',
        'ins',
        'del',
        'sub',
        'sup',
        'mark',
        'markmap',
        'vega-lite',
        'mermaid',
        # 'toc',
    },
    enable_rules={'smartquotes'},
)
MarkdownConfig(
    name='inline',
    preset='zero',
    options_update={'html': False, 'breaks': False},
    inline=True,
    enable_rules={'emphasis', 'backticks'},
)


@overload
def markdown(text: None, profile: Union[str, MarkdownConfig]) -> None:
    ...


@overload
def markdown(text: str, profile: Union[str, MarkdownConfig]) -> Markup:
    ...


def markdown(
    text: Optional[str], profile: Union[str, MarkdownConfig]
) -> Optional[Markup]:
    """
    Markdown parser compliant with Commonmark+GFM using markdown-it-py.

    :param profile: Config profile to use
    """
    if text is None:
        return None

    # Replace invisible characters with spaces
    text = normalize_spaces_multiline(text)

    if isinstance(profile, str):
        try:
            profile = MarkdownConfig.registry[profile]
        except KeyError as exc:
            raise KeyError(f"Unknown Markdown config profile '{profile}'") from exc

    # TODO: Move MarkdownIt instance generation to profile class method
    md = MarkdownIt(profile.preset, profile.options_update or {})

    if md.linkify is not None:
        md.linkify.set(
            {
                'fuzzy_link': profile.linkify_fuzzy_link,
                'fuzzy_email': profile.linkify_fuzzy_email,
            }
        )

    if profile.enable_rules:
        md.enable(profile.enable_rules)
    if profile.disable_rules:
        md.disable(profile.disable_rules)

    for e in profile.plugins:
        ext = markdown_plugins[e]
        md.use(ext, **markdown_plugin_config.get(e, {}))

    if profile.inline:
        return Markup(md.renderInline(text or ''))
    return Markup(md.render(text or ''))
