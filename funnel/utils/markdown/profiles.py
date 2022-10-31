"""Config profiles for markdown parser."""

from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Type, TypedDict

from mdit_py_plugins import anchors, footnote, tasklists
from typing_extensions import NotRequired

from coaster.utils import make_name

__all__ = ['profiles', 'plugins', 'plugin_configs', 'default_markdown_options']

plugins: Dict[str, Callable] = {
    'footnote': footnote.footnote_plugin,
    'heading_anchors': anchors.anchors_plugin,
    'tasklists': tasklists.tasklists_plugin,
}

plugin_configs: Dict[str, Dict[str, Any]] = {
    'heading_anchors': {
        'min_level': 1,
        'max_level': 3,
        'slug_func': lambda x, **options: 'h:' + make_name(x, **options),
        'permalink': True,
    },
    'tasklists': {'enabled': True, 'label': True, 'label_after': False},
}


default_markdown_options = {
    'html': False,
    'linkify': True,
    'typographer': True,
    'breaks': True,
}


class PostConfig(TypedDict):
    disable: NotRequired[List[str]]
    enable: NotRequired[List[str]]
    enableOnly: NotRequired[List[str]]  # noqa: N815


class MarkdownProfile:
    args: Tuple[str, Mapping] = ('gfm-like', default_markdown_options)
    plugins: List[str] = []
    post_config: PostConfig = {}
    render_with: str = 'render'


class MarkdownProfileBasic(MarkdownProfile):
    post_config: PostConfig = {'disable': ['table']}


class MarkdownProfileDocument(MarkdownProfile):
    plugins: List[str] = [
        'footnote',
        'heading_anchors',
        'tasklists',
    ]


class MarkdownProfileTextField(MarkdownProfile):
    args: Tuple[str, Mapping] = ('zero', default_markdown_options)
    post_config: PostConfig = {
        'enable': [
            'emphasis',
            'backticks',
        ],
    }
    render_with: str = 'renderInline'


profiles: Dict[Optional[str], Type[MarkdownProfile]] = {
    None: MarkdownProfileDocument,
    'basic': MarkdownProfileBasic,
    'document': MarkdownProfileDocument,
    'text-field': MarkdownProfileTextField,
}
