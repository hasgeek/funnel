"""Helpers for markdown parser."""

from copy import deepcopy
from typing import Any, Dict, List

from markdown_it import MarkdownIt
from typing_extensions import Protocol, TypedDict

from coaster.utils.text import VALID_TAGS

MARKDOWN_HTML_TAGS = deepcopy(VALID_TAGS)


class MarkdownItPluginProtocol(Protocol):
    """Typing protocol for callable to initilize markdown-it-py plugin."""

    def __call__(self, md: MarkdownIt, **options) -> None:
        ...


EXT_CONFIG_TYPE = Dict[str, Any]
EXT_TYPE = MarkdownItPluginProtocol


class MDITExtensionType(TypedDict):
    ext: EXT_TYPE
    configs: Dict[str, EXT_CONFIG_TYPE]
    default_config: str
    when_html: bool


DEFAULT_MD_EXT: List[str] = ['footnote', 'heading_anchors', 'tasklists']

MD_CONFIGS: Dict[str, EXT_CONFIG_TYPE] = {'default': {'extensions': DEFAULT_MD_EXT}}

MD_CONFIGS['default_with_html'] = deepcopy(MD_CONFIGS['default'])
MD_CONFIGS['default_with_html'].update({'html': True})
