"""markdown-it-py style presets for funnel."""

from markdown_it.presets import gfm_like

__all__ = []  # type: ignore[var-annotated]


class custom_profile:  # noqa: N801
    @staticmethod
    def make():
        config = gfm_like.make()
        # ... options to process single line
        return config
