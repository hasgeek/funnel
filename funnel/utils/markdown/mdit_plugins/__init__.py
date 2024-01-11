"""Plugins for markdown-it-py."""

# --- Everything below this line is auto-generated using `make initpy` -----------------

from . import (
    abbr,
    block_code_ext,
    del_tag,
    embeds,
    footnote_ext,
    heading_anchors_fix,
    ins_tag,
    mark_tag,
    sub_tag,
    sup_tag,
    toc,
)
from .abbr import abbr_plugin
from .block_code_ext import block_code_extend_plugin
from .del_tag import del_plugin
from .embeds import embeds_plugin
from .footnote_ext import footnote_extend_plugin
from .heading_anchors_fix import heading_anchors_fix_plugin
from .ins_tag import ins_plugin
from .mark_tag import mark_plugin
from .sub_tag import sub_plugin
from .sup_tag import sup_plugin
from .toc import toc_plugin

__all__ = [
    "abbr",
    "abbr_plugin",
    "block_code_ext",
    "block_code_extend_plugin",
    "del_plugin",
    "del_tag",
    "embeds",
    "embeds_plugin",
    "footnote_ext",
    "footnote_extend_plugin",
    "heading_anchors_fix",
    "heading_anchors_fix_plugin",
    "ins_plugin",
    "ins_tag",
    "mark_plugin",
    "mark_tag",
    "sub_plugin",
    "sub_tag",
    "sup_plugin",
    "sup_tag",
    "toc",
    "toc_plugin",
]
