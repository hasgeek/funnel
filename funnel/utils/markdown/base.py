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
    fence_extend_plugin,
    footnote_extend_plugin,
    ins_plugin,
    mark_plugin,
    sub_plugin,
    sup_plugin,
)

__all__ = ['MarkdownPlugin', 'MarkdownConfig']


OptionStrings = Literal['html', 'breaks', 'linkify', 'typographer']


@dataclass
class MarkdownPlugin:
    """Markdown plugin registry with configuration."""

    #: Registry of named sub-classes
    registry: ClassVar[Dict[str, MarkdownConfig]] = {}

    #: Optional name for this config, for adding to the registry
    name: str
    func: Callable
    config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # If this plugin+configuration has a name, add it to the registry
        if self.name is not None:
            if self.name in self.registry:
                raise NameError(f"Plugin {self.name} has already been registered")
            self.registry[self.name] = self


@dataclass
class MarkdownConfig:
    """Markdown processor with custom configuration, with a registry."""

    #: Registry of named sub-classes
    registry: ClassVar[Dict[str, MarkdownConfig]] = {}

    #: Optional name for this config, for adding to the registry
    name: Optional[str] = None

    #: Markdown-it preset configuration
    preset: Literal[
        'default', 'zero', 'commonmark', 'js-default', 'gfm-like'
    ] = 'commonmark'
    #: Updated options against the preset
    options_update: Optional[Dict[OptionStrings, bool]] = None
    #: Allow only inline rules (skips all block rules)?
    inline: bool = False

    #: Use these plugins
    plugins: Iterable[Union[str, MarkdownPlugin]] = ()
    #: Enable these rules (provided by plugins)
    enable_rules: Optional[Set[str]] = None
    #: Disable these rules
    disable_rules: Optional[Set[str]] = None

    #: If linkify is enabled, apply to fuzzy links too?
    linkify_fuzzy_link: bool = False
    #: If linkify is enabled, make email links too?
    linkify_fuzzy_email: bool = False

    def __post_init__(self):
        try:
            self.plugins = [
                MarkdownPlugin.registry[plugin] if isinstance(plugin, str) else plugin
                for plugin in self.plugins
            ]
        except KeyError as exc:
            raise TypeError(f"Unknown Markdown plugin {exc.args[0]}") from None

        # If this plugin+configuration has a name, add it to the registry
        if self.name is not None:
            if self.name in self.registry:
                raise NameError(f"Config {self.name} has already been registered")
            self.registry[self.name] = self

    @overload
    def render(self, text: None) -> None:
        ...

    @overload
    def render(self, text: str) -> Markup:
        ...

    def render(self, text: Optional[str]) -> Optional[Markup]:
        """Parse and render Markdown using markdown-it-py with the selected config."""
        if text is None:
            return None

        # Replace invisible characters with spaces
        text = normalize_spaces_multiline(text)

        md = MarkdownIt(self.preset, self.options_update or {})

        if md.linkify is not None:
            md.linkify.set(
                {
                    'fuzzy_link': self.linkify_fuzzy_link,
                    'fuzzy_email': self.linkify_fuzzy_email,
                }
            )

        if self.enable_rules:
            md.enable(self.enable_rules)
        if self.disable_rules:
            md.disable(self.disable_rules)

        for plugin in self.plugins:
            md.use(plugin.func, **(plugin.config or {}))  # type: ignore[union-attr]

        if self.inline:
            return Markup(md.renderInline(text or ''))
        return Markup(md.render(text or ''))


# --- Markdown plugins -----------------------------------------------------------------

MarkdownPlugin('footnote', footnote.footnote_plugin)
MarkdownPlugin(
    'heading_anchors',
    anchors.anchors_plugin,
    {
        'min_level': 1,
        'max_level': 6,
        'slug_func': lambda x: 'h:' + make_name(x),
        'permalink': True,
        'permalinkSymbol': '#',
    },
)
MarkdownPlugin(
    'tasklists',
    tasklists.tasklists_plugin,
    {'enabled': True, 'label': True, 'label_after': False},
)
MarkdownPlugin('ins', ins_plugin)
MarkdownPlugin('del', del_plugin)
MarkdownPlugin('sub', sub_plugin)
MarkdownPlugin('sup', sup_plugin)
MarkdownPlugin('mark', mark_plugin)
MarkdownPlugin('markmap', embeds_plugin, {'name': 'markmap'})
MarkdownPlugin('vega-lite', embeds_plugin, {'name': 'vega-lite'})
MarkdownPlugin('mermaid', embeds_plugin, {'name': 'mermaid'})
MarkdownPlugin('fence_ext', fence_extend_plugin)
MarkdownPlugin('footnote_ext', footnote_extend_plugin)
# MarkdownPlugin('toc', toc_plugin)

# --- Markdown configurations ----------------------------------------------------------

MarkdownConfig(
    name='basic', options_update={'html': False, 'breaks': True}, plugins={'fence_ext'}
)
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
        'fence_ext',
        'footnote_ext'
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
