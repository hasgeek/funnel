"""Extension map for markdown-it-py to be used by markdown parser."""

from typing import Dict

from mdit_py_plugins import anchors, footnote, tasklists

from coaster.utils import make_name

from .helpers import MDExtension

markdown_extensions: Dict[str, MDExtension] = {}

markdown_extensions['footnote'] = MDExtension(footnote.footnote_plugin)

markdown_extensions['heading_anchors'] = MDExtension(anchors.anchors_plugin)
markdown_extensions['heading_anchors'].set_config(
    'default',
    {
        'min_level': 1,
        'max_level': 3,
        'slug_func': lambda x, **options: 'h:' + make_name(x, **options),
        'permalink': True,
    },
)


markdown_extensions['tasklists'] = MDExtension(tasklists.tasklists_plugin)
markdown_extensions['tasklists'].set_config(
    'default', {'enabled': False, 'label': False, 'label_after': False}
)

# TODO: These plugins will be integrated later with more robust edge-case testing
# markdown_extensions['ins'] = MDExtension(mdit_plugins.ins_plugin)  # type: ignore
# markdown_extensions['del'] = MDExtension(mdit_plugins.del_sub_plugin)
# markdown_extensions['sup'] = MDExtension(mdit_plugins.sup_plugin)
