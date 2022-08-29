"""Helpers for markdown parser."""

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
    ext: MDITPluginType
    configs: Dict[str, MDConfigType]
    _default_config: str = 'default'
    _use_with_html: bool

    def __init__(self, ext: MDITPluginType, use_with_html: bool = True):
        self.ext = ext
        self._use_with_html = use_with_html
        self.configs = {'default': {}}

    def set_config(self, k: str, v: MDConfigType) -> None:
        self.configs[k] = v

    def config(self, k: str) -> MDConfigType:
        return self.configs[k] if k in self.configs else self.default_config

    def set_default_config(self, default: str) -> None:
        if default in self.configs:
            self._default_config = default

    def when_html(self, is_set: bool) -> bool:
        return not is_set or (is_set and self._use_with_html)

    @property
    def default_config(self) -> MDConfigType:
        return self.configs[self._default_config]


MDExtDefaults: List[str] = ['footnote', 'heading_anchors', 'tasklists']

MD_CONFIGS: Dict[str, MDConfigType] = {'default': {'extensions': MDExtDefaults}}

MD_CONFIGS['default_with_html'] = deepcopy(MD_CONFIGS['default'])
MD_CONFIGS['default_with_html'].update({'html': True})
MD_CONFIGS['default_no_extensions'] = {}
MD_CONFIGS['default_no_extensions_with_html'] = {'html': True}
