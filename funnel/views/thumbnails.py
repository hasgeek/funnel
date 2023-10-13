"""View for autogenerating thumbnail previews."""

from __future__ import annotations

from ..signals import project_data_change


@project_data_change.connect
def generate_thumbnail_image() -> None:
    pass
