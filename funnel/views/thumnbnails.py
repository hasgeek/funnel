"""View for autogenerating thumbnail previews."""

from __future__ import annotations

from ..models import Project
from ..signals import project_data_change


@project_data_change.connect
def generate_thumbnail_image(project: Project) -> None:
    render_thumbnail_image(project=project)


def render_thumbnail_image(project: Project) -> None:
    """Render the thumbnail image and cache the file using a background task"""
