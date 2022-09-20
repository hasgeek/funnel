"""Config profiles for markdown parser."""

from typing import Any, Callable, Dict

from mdit_py_plugins import anchors, footnote, tasklists

from coaster.utils import make_name

__all__ = ['profiles', 'plugins', 'plugin_configs']

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

default_funnel_options = {
    'html': False,
    'linkify': True,
    'typographer': True,
    'breaks': True,
}
default_funnel_args = ('gfm-like', default_funnel_options)
default_funnel_config: Dict = {}
default_plugins = [
    'footnote',
    'heading_anchors',
    'tasklists',
]

profiles: Dict[str, Dict[str, Any]] = {
    """
    Config profiles.

    Format: {
        'args': (
            config: str | preset.make(),
            options_update: Mapping | None
        ),
        'funnel_config' : { # Optional
            'enable': [],
            'disable': [],
            'renderInline': False
        }
    }
    """
    'comment': {
        'args': ('commonmark', default_funnel_options),
        'funnel_config': default_funnel_config,
        'plugins': ['footnote'],
    },
    'profile': {
        'args': default_funnel_args,
        'funnel_config': default_funnel_config,
        'plugins': default_plugins,
    },
    'project': {
        'args': default_funnel_args,
        'funnel_config': default_funnel_config,
        'plugins': default_plugins,
    },
    'proposal': {
        'args': default_funnel_args,
        'funnel_config': default_funnel_config,
        'plugins': default_plugins,
    },
    'session': {
        'args': default_funnel_args,
        'funnel_config': default_funnel_config,
        'plugins': default_plugins,
    },
    'update': {
        'args': ('commonmark', default_funnel_options),
        'funnel_config': default_funnel_config,
        'plugins': [],
    },
    'venue': {
        'args': ('commonmark', default_funnel_options),
        'funnel_config': default_funnel_config,
        'plugins': [],
    },
    'single-line': {
        'args': ('zero', {}),
        'funnel_config': {'enable': ['emphasize', 'backticks'], 'renderInline': True},
    },
}
