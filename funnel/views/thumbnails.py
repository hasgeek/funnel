"""View for autogenerating thumbnail previews."""

from __future__ import annotations

import os
import tempfile

from flask import render_template
from html2image import Html2Image

from ..models import Project, db
from ..signals import project_data_change
from .jobs import rqjob


@project_data_change.connect
def redo_project_preview_image(project: Project) -> None:
    render_project_preview_image.queue(project_id=project.id)


@rqjob()
def render_project_preview_image(project_id: int) -> None:
    """Generate a project preview image."""
    project = Project.query.get(project_id)
    if project is None:
        return

    fd, temp_filepath = tempfile.mkstemp('.png')
    os.close(fd)
    temp_dir, temp_filename = os.path.split(temp_filepath)
    hti = Html2Image(size=(320, 180), output_path=temp_dir)
    html_src = render_template('preview/project.html.jinja2', project=project)
    screenshot_files = hti.screenshot(html_str=html_src, save_as=temp_filename)

    if screenshot_files:
        with open(screenshot_files[0], mode='rb') as file:
            project.preview_image = file.read()
        db.session.commit()

    for each_screenshot in screenshot_files:
        os.remove(each_screenshot)
