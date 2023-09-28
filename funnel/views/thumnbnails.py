"""View for autogenerating thumbnail previews."""

from flask import Response
from html2image import Html2Image

from ..models import Project, db
from ..signals import project_data_change
from .jobs import rqjob

thumbnail = Html2Image(size=(640, 360))


@project_data_change.connect
def generate_thumbnail_image(project=Project) -> None:
    render_thumbnail_image(project=project)


@rqjob()
def render_thumbnail_image(project=Project) -> Response:
    """Render the thumbnail image and cache the file using a background task"""

    image_html = render_template('thumbnail_preview.html.jinja2', project=project)

    thumbnail_image = thumbnail.screenshot(
        html_str=image_html, save_as=f'{project.id}_thumbnail.png', size=(640, 360)
    )

    project.thumbnail_image = thumbnail_image
    db.session.add(project)
    db.session.commit()

    response = Response(
        status=200,
        headers=[('Cache-Control', 'non-cache, no-store, max-age=0, must-revalidate'),
                 ('Pragma', 'no-cahce')],
    )
    return response
