"""View for autogenerating thumbnail previews"""

from flask import render_template
from html2image import Html2Image

from ..models import Project
from ..signals import project_data_change
from .jobs import rqjob

thumbnail = Html2Image(size=(1067, 600))


@project_data_change.connect
def generate_thumbnail_image(project=Project) -> None:
    render_thumbnail_image(project=project)


@rqjob()
def render_thumbnail_image(project=Project) -> None:
    """Render the thumbnail image and cache the file using a background task"""

    image_html = render_template('thumbnail_preview.html.jinja2', project=project)

    thumbnail.screenshot(html_str=image_html, save_as='thumbnail.png', size=(1067, 600))
