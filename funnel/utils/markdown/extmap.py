"""Extension map for markdown-it-py to be used by markdown parser."""

from typing import Dict

from mdit_py_plugins import anchors, footnote, tasklists

from coaster.utils import make_name

from .helpers import MDExtension

MDExtMap: Dict[str, MDExtension] = {}

MDExtMap['footnote'] = MDExtension(footnote.footnote_plugin)

MDExtMap['heading_anchors'] = MDExtension(anchors.anchors_plugin, use_with_html=False)
MDExtMap['heading_anchors'].set_config(
    'default',
    {
        'min_level': 1,
        'max_level': 3,
        'slug_func': lambda x, **options: 'h:' + make_name(x, **options),
        'permalink': True,
    },
)


MDExtMap['tasklists'] = MDExtension(tasklists.tasklists_plugin, use_with_html=False)
MDExtMap['tasklists'].set_config(
    'default', {'enabled': False, 'label': False, 'label_after': False}
)
