import pytest
import io
from PIL import Image

from funnel.views.thumbnails import render_project_preview_image

@pytest.mark.usefixtures('project_expo2011', 'all_fixtures')
def test_preview_image_jobs(project_expo2011) -> None:
    assert project_expo2011.preview_image is None
    render_project_preview_image(project_id=project_expo2011.id)
    assert project_expo2011.preview_image is not None

@pytest.mark.usefixtures('project_expo2011', 'all_fixtures')
def test_preview_image_size(project_expo2011) -> None:
    render_project_preview_image(project_id=project_expo2011.id)
    preview_image = Image.open(io.BytesIO(project_expo2011.preview_image))
    assert preview_image.size == (1280, 720)
    assert preview_image.format is 'PNG'
