"""View for autogenerating thumbnail previews."""

from __future__ import annotations

import tempfile
import os

from flask import Response, render_template
from html2image import Html2Image

from ..models import Project, db
from ..signals import project_data_change
from .jobs import rqjob

@project_data_change.connect
def generate_thumbnail_image(project: Project) -> None:
    render_thumbnail_image.queue(project=project)


@rqjob()
def render_thumbnail_image(project: Project) -> Response:
    """Render the thumbnail image and cache the file using a background task"""

    thumbnail = Html2Image(size=(640, 360))
    image_html = render_template('thumbnail_preview.html.jinja2', project=project)
    thumbnail_image, temp_filepath = tempfile.mkstemp()
    os.close(thumbnail_image)

    temp_dir = os.path.split(temp_filepath)
    thumbnail.output_path = temp_dir[0]
    thumbnail.screenshot(
        html_str=image_html, save_as='thumbnail_image.png', size=(640, 360)
    )

    with open(os.path.join(temp_dir[0],'thumbnail_image.png'), mode='rb') as file:
        thumbnail_data = bytearray(file.read())
        project.thumbnail_image = thumbnail_data
        print(thumbnail_data)
        db.session.add(project)

    db.session.commit()

    response = Response(
        status=200,
        headers=[
            ('Cache-Control', 'non-cache, no-store, max-age=0, must-revalidate'),
            ('Pragma', 'no-cahce'),
        ],
    )
    return response
