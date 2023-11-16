import pytest
from io import BytesIO
from magic import from_buffer
from PIL import Image

from funnel.views.thumbnails import render_project_preview_image


@pytest.mark.usefixtures('project_expo2011', 'all_fixtures')
def test_preview_image_jobs(project_expo2011) -> None:
    assert project_expo2011.preview_image is None
    render_project_preview_image(project_id=project_expo2011.id)
    assert project_expo2011.preview_image is not None


@pytest.mark.usefixtures('project_expo2011', 'all_fixtures')
def test_preview_image_size_mimeytpe(project_expo2011) -> None:
    render_project_preview_image(project_id=project_expo2011.id)
    with Image.open(BytesIO(project_expo2011.preview_image)) as preview_image:
        assert preview_image.size == (1280, 720)
    image_mimetype = from_buffer(BytesIO(project_expo2011.preview_image).read(2048), mime=True)
    assert image_mimetype == 'image/png'
