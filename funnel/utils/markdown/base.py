"""Markdown parser and config profiles."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, Literal, overload
from typing_extensions import Self

from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins import anchors, container, deflist, footnote, tasklists

from coaster.utils import make_name
from coaster.utils.text import normalize_spaces_multiline

from .mdit_plugins import (  # toc_plugin,
    abbr_plugin,
    block_code_extend_plugin,
    del_plugin,
    embeds_plugin,
    footnote_extend_plugin,
    heading_anchors_fix_plugin,
    ins_plugin,
    mark_plugin,
    sub_plugin,
    sup_plugin,
)
from .tabs import render_tab

__all__ = [
    'MarkdownPlugin',
    'MarkdownConfig',
    'markdown_basic',
    'markdown_document',
    'markdown_mailer',
    'markdown_inline',
]


# --- Markdown dataclasses -------------------------------------------------------------


@dataclass
class MarkdownPlugin:
    """Markdown plugin registry with configuration."""

    #: Registry of instances
    registry: ClassVar[dict[str, MarkdownPlugin]] = {}

    #: Optional name for this config
    name: str | None
    func: Callable
    config: dict[str, Any] | None = None

    @classmethod
    def register(cls, name: str, *args, **kwargs) -> Self:
        """Create a new instance and add it to the registry."""
        if name in cls.registry:
            raise NameError(f"MarkdownPlugin {name} has already been registered")
        obj = cls(name, *args, **kwargs)
        cls.registry[name] = obj
        return obj


@dataclass
class MarkdownConfig:
    """Markdown processor with custom configuration, with a registry."""

    #: Registry of named instances
    registry: ClassVar[dict[str, MarkdownConfig]] = {}

    #: Optional name for this config, for adding to the registry
    name: str | None = None

    #: Markdown-it preset configuration
    preset: Literal[
        'default', 'zero', 'commonmark', 'js-default', 'gfm-like'
    ] = 'commonmark'
    #: Updated options against the preset
    options_update: Mapping | None = None
    #: Allow only inline rules (skips all block rules)?
    inline: bool = False

    #: Use these plugins
    plugins: Iterable[str | MarkdownPlugin] = ()
    #: Enable these rules (provided by plugins)
    enable_rules: set[str] | None = None
    #: Disable these rules
    disable_rules: set[str] | None = None

    #: If linkify is enabled, apply to fuzzy links too?
    linkify_fuzzy_link: bool = False
    #: If linkify is enabled, make email links too?
    linkify_fuzzy_email: bool = False

    def __post_init__(self) -> None:
        try:
            self.plugins = [
                MarkdownPlugin.registry[plugin] if isinstance(plugin, str) else plugin
                for plugin in self.plugins
            ]
        except KeyError as exc:
            raise TypeError(f"Unknown Markdown plugin {exc.args[0]}") from None

    @classmethod
    def register(cls, name: str, *args, **kwargs) -> Self:
        """Create a new instance and add it to the registry."""
        if name in cls.registry:
            raise NameError(f"MarkdownConfig {name} has already been registered")
        obj = cls(name, *args, **kwargs)
        cls.registry[name] = obj
        return obj

    @overload
    def render(self, text: None) -> None:
        ...

    @overload
    def render(self, text: str) -> Markup:
        ...

    def render(self, text: str | None) -> Markup | None:
        """Parse and render Markdown using markdown-it-py with the selected config."""
        if text is None:
            return None

        # Recast MarkdownString as a plain string and normalize all space chars
        text = normalize_spaces_multiline(str(text))
        # XXX: this also replaces a tab with a single space. This will be a problem if
        # the tab char has semantic meaning, such as in an embedded code block for a
        # tab-sensitive syntax like a Makefile

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


MarkdownPlugin.register('abbr', abbr_plugin)
MarkdownPlugin.register('deflists', deflist.deflist_plugin)
MarkdownPlugin.register('footnote', footnote.footnote_plugin)
MarkdownPlugin.register(
    'heading_anchors',
    anchors.anchors_plugin,
    {
        'min_level': 1,
        'max_level': 6,
        'slug_func': lambda x: 'h:' + make_name(x),
        'permalink': True,
        'permalinkSymbol': '#',
        'permalinkSpace': False,
    },
)
# The heading_anchors_fix plugin modifies the token stream output of heading_anchors
# plugin to make the heading a permalink instead of a separate permalink. It eliminates
# the extra character and strips any links inside the heading that may have been
# introduced by the author.
MarkdownPlugin.register('heading_anchors_fix', heading_anchors_fix_plugin)

MarkdownPlugin.register(
    'tasklists',
    tasklists.tasklists_plugin,
    {'enabled': True, 'label': True, 'label_after': False},
)
MarkdownPlugin.register('ins', ins_plugin)
MarkdownPlugin.register('del', del_plugin)
MarkdownPlugin.register('sub', sub_plugin)
MarkdownPlugin.register('sup', sup_plugin)
MarkdownPlugin.register('mark', mark_plugin)

MarkdownPlugin.register(
    'tab_container',
    container.container_plugin,
    {'name': 'tab', 'marker': ':', 'render': render_tab},
)
MarkdownPlugin.register('markmap', embeds_plugin, {'name': 'markmap'})
MarkdownPlugin.register('vega_lite', embeds_plugin, {'name': 'vega-lite'})
MarkdownPlugin.register('mermaid', embeds_plugin, {'name': 'mermaid'})
MarkdownPlugin.register('block_code_ext', block_code_extend_plugin)
MarkdownPlugin.register('footnote_ext', footnote_extend_plugin)
# The TOC plugin isn't yet working
# MarkdownPlugin.register('toc', toc_plugin)

# --- Markdown configurations ----------------------------------------------------------

markdown_basic = MarkdownConfig.register(
    name='basic',
    options_update={'html': False, 'breaks': True},
    plugins=['block_code_ext'],
)

markdown_document = MarkdownConfig.register(
    name='document',
    preset='gfm-like',
    options_update={
        'html': False,
        'linkify': True,
        'typographer': True,
        'breaks': True,
    },
    plugins=[
        'tab_container',
        'abbr',
        'block_code_ext',
        'deflists',
        'footnote',
        'footnote_ext',  # Must be after 'footnote' to take effect
        'heading_anchors',
        'heading_anchors_fix',  # Must be after 'heading_anchors' to take effect
        'tasklists',
        'ins',
        'del',
        'sub',
        'sup',
        'mark',
        'markmap',
        'vega_lite',
        'mermaid',
        # 'toc',
    ],
    enable_rules={'smartquotes'},
)

markdown_mailer = MarkdownConfig.register(
    name='mailer',
    preset='gfm-like',
    options_update={
        'html': True,
        'linkify': True,
        'typographer': True,
        'breaks': True,
    },
    plugins=markdown_document.plugins,
    enable_rules={'smartquotes'},
    linkify_fuzzy_email=True,
)

#: This profile is meant for inline fields (like Title) and allows for only inline
#: visual markup: emphasis, code, ins/underline, del/strikethrough, superscripts,
#: subscripts and smart quotes. It does not allow hyperlinks, images or HTML tags.
#: Text in these fields will also have to be presented raw for embeds and other third
#: party uses. We have considered using an alternative "plaintext" renderer that uses
#: Unicode characters for bold/italic/sub/sup, but found this unsuitable as these
#: character ranges are not comprehensive. Instead, plaintext use will include the
#: Markdown formatting characters as-is.
markdown_inline = MarkdownConfig.register(
    name='inline',
    preset='zero',
    options_update={'html': False, 'breaks': False, 'typographer': True},
    plugins=['ins', 'del', 'sup', 'sub'],
    inline=True,
    enable_rules={'emphasis', 'backticks', 'escape', 'smartquotes'},
)
