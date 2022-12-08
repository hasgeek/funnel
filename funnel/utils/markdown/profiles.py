"""Config profiles for markdown parser."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Tuple, Type, TypedDict

from mdit_py_plugins import anchors, footnote, tasklists
from typing_extensions import NotRequired

from coaster.utils import make_name

from .mdit_plugins import (  # toc_plugin,
    del_plugin,
    embeds_plugin,
    ins_plugin,
    mark_plugin,
    sub_plugin,
    sup_plugin,
)

__all__ = ['plugins', 'plugin_configs', 'MarkdownProfile']

plugins: Dict[str, Callable] = {
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

plugin_configs: Dict[str, Dict[str, Any]] = {
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


class PostConfig(TypedDict):
    disable: NotRequired[List[str]]
    enable: NotRequired[List[str]]
    enableOnly: NotRequired[List[str]]  # noqa: N815


class MarkdownProfile:
    registry: Dict[str, Type[MarkdownProfile]] = {}
    args: Tuple[str, Mapping] = (
        'commonmark',
        {
            'html': False,
            'breaks': True,
        },
    )
    plugins: List[str] = []
    post_config: PostConfig = {}
    render_with: str = 'render'

    def __init_subclass__(cls, name: str) -> None:
        if name in MarkdownProfile.registry:
            raise TypeError(f"MarkdownProfile '{name}' already exists")
        MarkdownProfile.registry[name] = cls
        super().__init_subclass__()


class MarkdownProfileBasic(MarkdownProfile, name='basic'):
    pass


class MarkdownProfileDocument(MarkdownProfile, name='document'):
    args: Tuple[str, Mapping] = (
        'gfm-like',
        {
            'html': False,
            'linkify': True,
            'typographer': True,
            'breaks': True,
        },
    )
    plugins: List[str] = [
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
    ]
    post_config: PostConfig = {'enable': ['smartquotes']}


class MarkdownProfileInline(MarkdownProfile, name='inline'):
    args: Tuple[str, Mapping] = (
        'zero',
        {
            'html': False,
        },
    )
    post_config: PostConfig = {
        'enable': [
            'emphasis',
            'backticks',
        ],
    }
    render_with: str = 'renderInline'
