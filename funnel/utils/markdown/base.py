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
import re

from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins import anchors, container, deflist, footnote, tasklists
from typing_extensions import Literal

from coaster.utils import make_name
from coaster.utils.text import normalize_spaces_multiline

from .mdit_plugins import (  # toc_plugin,
    block_code_extend_plugin,
    del_plugin,
    embeds_plugin,
    footnote_extend_plugin,
    html_extend_plugin,
    ins_plugin,
    mark_plugin,
    sub_plugin,
    sup_plugin,
)
from .tabs import render_tab

__all__ = ['MarkdownPlugin', 'MarkdownConfig', 'MarkdownString', 'markdown_escape']

# --- Markdown escaper and string ------------------------------------------------------

#: Based on the ASCII punctuation list in the CommonMark spec at
#: https://spec.commonmark.org/0.30/#backslash-escapes
markdown_escape_re = re.compile(r"""([\[\\\]{|}\(\)`~!@#$%^&*=+;:'"<>/,.?_-])""")


def markdown_escape(text: str) -> MarkdownString:
    """
    Escape all Markdown formatting characters and strip whitespace at ends.

    As per the CommonMark spec, all ASCII punctuation can be escaped with a backslash
    and compliant parsers will then render the punctuation mark as a literal character.
    However, escaping any other character will cause the backslash to be rendered. This
    escaper therefore targets only ASCII punctuation characters listed in the spec.

    Edge whitespace is significant in Markdown and must be stripped when escaping:

    * Four spaces at the start will initiate a code block
    * Two spaces at the end will cause a line-break in non-GFM Markdown

    Replacing these spaces with &nbsp; is not suitable because non-breaking spaces
    affect HTML rendering, specifically the CSS ``white-space: normal`` sequence
    collapsing behaviour.

    :returns: Escaped text as an instance of :class:`MarkdownString`, to avoid
        double-escaping
    """
    if hasattr(text, '__markdown__'):
        return MarkdownString(text.__markdown__())
    return MarkdownString(markdown_escape_re.sub(r'\\\1', text).strip())


class MarkdownString(str):
    """Markdown string, implements a __markdown__ method."""

    __slots__ = ()

    def __new__(
        cls, base: Any = '', encoding: Optional[str] = None, errors: str = 'strict'
    ) -> MarkdownString:
        if hasattr(base, '__markdown__'):
            base = base.__markdown__()

        if encoding is None:
            return super().__new__(cls, base)

        return super().__new__(cls, base, encoding, errors)

    def __markdown__(self) -> MarkdownString:
        """Return a markdown source string."""
        return self

    @classmethod
    def escape(cls, text: str) -> MarkdownString:
        """Escape a string."""
        rv = markdown_escape(text)

        if rv.__class__ is not cls:
            return cls(rv)

        return rv

    # TODO: Implement other methods supported by markupsafe


# --- Markdown dataclasses -------------------------------------------------------------

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
        if (
            'html' in self.options_update
            and self.options_update['html']
            and 'html_ext' not in self.plugins
        ):
            raise ValueError(
                'HTML mode is turned on without adding the html_ext plugin'
            )
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

MarkdownPlugin('deflists', deflist.deflist_plugin)
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

MarkdownPlugin(
    'tab_container',
    container.container_plugin,
    {'name': 'tab', 'marker': ':', 'render': render_tab},
)
MarkdownPlugin('markmap', embeds_plugin, {'name': 'markmap'})
MarkdownPlugin('vega-lite', embeds_plugin, {'name': 'vega-lite'})
MarkdownPlugin('mermaid', embeds_plugin, {'name': 'mermaid'})
MarkdownPlugin('block_code_ext', block_code_extend_plugin)
MarkdownPlugin('footnote_ext', footnote_extend_plugin)
MarkdownPlugin('html_ext', html_extend_plugin)
# MarkdownPlugin('toc', toc_plugin)

# --- Markdown configurations ----------------------------------------------------------

MarkdownConfig(
    name='basic',
    options_update={'html': False, 'breaks': True},
    plugins=['block_code_ext'],
)

MarkdownConfig(
    name='document',
    preset='gfm-like',
    options_update={
        'html': True,
        'linkify': True,
        'typographer': True,
        'breaks': True,
    },
    plugins=[
        'tab_container',
        'block_code_ext',
        'html_ext',
        'deflists',
        'footnote',
        'footnote_ext',  # Must be after 'footnote' to take effect
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
    ],
    enable_rules={'smartquotes'},
)

#: This profile is meant for inline fields (like Title) and allows for only inline
#: visual markup: emphasis, code, ins/underline, del/strikethrough, superscripts,
#: subscripts and smart quotes. It does not allow hyperlinks, images or HTML tags.
#: Text in these fields will also have to be presented raw for embeds and other third
#: party uses. We have considered using an alternative "plaintext" renderer that uses
#: Unicode characters for bold/italic/sub/sup, but found this unsuitable as these
#: character ranges are not comprehensive. Instead, plaintext use will include the
#: Markdown formatting characters as-is.
MarkdownConfig(
    name='inline',
    preset='zero',
    options_update={'html': False, 'breaks': False, 'typographer': True},
    plugins=['ins', 'del', 'sup', 'sub'],
    inline=True,
    enable_rules={'emphasis', 'backticks', 'escape', 'smartquotes'},
)
