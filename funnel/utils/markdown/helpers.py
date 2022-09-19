"""Helper for markdown parser."""

from typing import Any, Callable, Dict, Optional

MDConfigType = Dict[str, Any]


class MDExtension:
    """
    Markdown Extension.

    Class to maintain data about a markdown extension, including the markdown-it-py
    plugin to be used, pre-defined configurations available, default configuration to
    be used and whether it is expected to be used when the parser accepts and parses
    HTML
    """

    def __init__(self, ext: Callable[..., None]):
        self.ext = ext
        self.configs: Dict[Optional[str], MDConfigType] = {None: {}}

    def set_config(self, k: Optional[str], v: MDConfigType) -> None:
        """Add/update a configuration for the extension."""
        self.configs[k] = v

    def config(self, k: Optional[str] = None) -> MDConfigType:
        """Get a configuration by key. If key does not exist, return default config."""
        return self.configs[k]

    @property
    def default_config(self) -> MDConfigType:
        return self.configs[None]


MD_CONFIGS: Dict[Optional[str], MDConfigType] = {None: {}, 'no_ext': {'extensions': []}}
