import pytest

from funnel.views.thumbnails import render_project_preview_image

@pytest.mark.usefixtures('project_expo2011', 'all_fixtures')
def test_preview_image_jobs(project_expo2011):
    assert project_expo2011.preview_image is None
    render_project_preview_image(project_id=project_expo2011.id)
    assert project_expo2011.preview_image is not None
