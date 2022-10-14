"""Config profiles for markdown parser."""

from typing import Any, Callable, Dict

from mdit_py_plugins import anchors, footnote, tasklists

from coaster.utils import make_name

from .mdit_plugins import ins_plugin, sub_del_plugin, sup_plugin

__all__ = ['profiles', 'plugins', 'plugin_configs', 'default_markdown_options']

plugins: Dict[str, Callable] = {
    'footnote': footnote.footnote_plugin,
    'heading_anchors': anchors.anchors_plugin,
    'tasklists': tasklists.tasklists_plugin,
    'ins': ins_plugin,
    'sub_del': sub_del_plugin,
    'sup': sup_plugin,
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


# Config profiles.
#
# Format: {
#     'args': (
#         config:str | preset.make(),
#         options_update: Mapping | None
#     ),
#     'funnel_config' : { # Optional
#         'enable': List = [],
#         'disable': List = [],
#         'enableOnly': List = [],
#         'render_with': str = 'render'
#     }
# }

profiles: Dict[str, Dict[str, Any]] = {
    'basic': {
        'args': ('gfm-like', default_markdown_options),
        'plugins': [],
        'funnel_config': {'disable': ['table']},
    },
    'document': {
        'args': ('gfm-like', default_markdown_options),
        'plugins': [
            'footnote',
            'heading_anchors',
            'tasklists',
            'ins',
            'sub_del',
            'sup',
        ],
    },
    'text-field': {
        'args': ('zero', {'breaks': False}),
        'funnel_config': {
            'enable': ['emphasis', 'backticks'],
            'render_with': 'renderInline',
        },
    },
}
