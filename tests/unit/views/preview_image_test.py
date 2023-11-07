import pytest

from funnel.views.thumbnails import render_project_preview_image

@pytest.mark.usefixtures('app_context', 'new_project')
@pytest.fixture()
def add_tasks_to_queue(new_project):
    render_project_preview_image.queue(project_id=new_project.id, job_id=new_project.id)

@pytest.mark.usefixtures('add_tasks_to_queue', 'project_expo2011', 'project_ai1',
                         'project_ai2')
def test_preview_image_jobs():
    add_tasks_to_queue(project_expo2011)
    add_tasks_to_queue(project_ai1)
    add_tasks_to_queue(project_ai2)
    pass
