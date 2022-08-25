"""Extension map for markdown-it-py to be used by markdown parser."""

from typing import Dict

from mdit_py_plugins import anchors, footnote, tasklists

from coaster.utils import make_name

from .helpers import MDITExtensionType

EXT_MAP: Dict[str, MDITExtensionType] = {}

EXT_MAP['footnote'] = {
    'ext': footnote.footnote_plugin,
    'configs': {'default': {}},
    'default_config': 'default',
    'when_html': True,
}

EXT_MAP['heading_anchors'] = {
    'ext': anchors.anchors_plugin,
    'configs': {
        'default': {
            'min_level': 1,
            'max_level': 3,
            'slug_func': lambda x, **options: 'h:' + make_name(x, **options),
            'permalink': True,
        }
    },
    'default_config': 'default',
    'when_html': False,
}

EXT_MAP['tasklists'] = {
    'ext': tasklists.tasklists_plugin,
    'configs': {
        'no_tasklist': {'enabled': False, 'label': False, 'label_after': False}
    },
    'default_config': 'no_tasklist',
    'when_html': False,
}

EXT_LIST = EXT_MAP.keys()
