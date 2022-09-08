"""Helper for markdown parser."""

from typing import Any, Dict, List

from markdown_it import MarkdownIt
from typing_extensions import Protocol


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

    def __init__(self, ext: MDITPluginType):
        self.ext = ext
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

    @property
    def default_config(self) -> MDConfigType:
        return self.configs[self._default_config]


MDExtDefaults: List[str] = ['footnote', 'heading_anchors', 'tasklists']

MD_CONFIGS: Dict[str, MDConfigType] = {'default': {}}

MD_CONFIGS['no_ext'] = {'extensions': []}
