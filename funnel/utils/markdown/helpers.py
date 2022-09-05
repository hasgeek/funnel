"""Helper for markdown parser."""

from copy import deepcopy
from typing import Any, Dict, List

from markdown_it import MarkdownIt
from typing_extensions import Protocol

from coaster.utils.text import VALID_TAGS

MARKDOWN_HTML_TAGS = deepcopy(VALID_TAGS)


class MDITPluginType(Protocol):
    """Typing protocol for callable to initilize markdown-it-py plugin."""

    def __call__(self, md: MarkdownIt, **options) -> None:
        ...


MDConfigType = Dict[str, Any]


class MDExtension:
    """
    Markdown Extension.

    Class to maintain data about a markdown extension, including the markdown-it-py
    plugin to be used, pre-defined configurations available, default configuration to
    be used and whether it is expected to be used when the parser accepts and parses
    HTML
    """

    ext: MDITPluginType
    configs: Dict[str, MDConfigType]
    _default_config: str = 'default'
    _use_with_html: bool

    def __init__(self, ext: MDITPluginType, use_with_html: bool = True):
        self.ext = ext
        self._use_with_html = use_with_html
        self.configs = {'default': {}}

    def set_config(self, k: str, v: MDConfigType) -> None:
        """Add/update a configuration for the extension."""
        self.configs[k] = v

    def config(self, k: str) -> MDConfigType:
        """Get a configuration by key. If key does not exist, return default config."""
        return self.configs[k] if k in self.configs else self.default_config

    def set_default_config(self, default: str) -> None:
        """Set the default configuration for the extension."""
        if default in self.configs:
            self._default_config = default

    def when_html(self, is_set: bool) -> bool:
        """Return a flag indicating if extension can be used when html is enabled."""
        return not is_set or (is_set and self._use_with_html)

    @property
    def default_config(self) -> MDConfigType:
        return self.configs[self._default_config]


MDExtDefaults: List[str] = ['ins', 'footnote', 'heading_anchors', 'tasklists']

MD_CONFIGS: Dict[str, MDConfigType] = {'default': {'extensions': MDExtDefaults}}

MD_CONFIGS['html'] = deepcopy(MD_CONFIGS['default'])
MD_CONFIGS['html'].update({'html': True})
MD_CONFIGS['no_ext'] = {'extensions': []}
MD_CONFIGS['html_no_ext'] = {'html': True, 'extensions': []}
