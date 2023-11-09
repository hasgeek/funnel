import pytest

from funnel.views.thumbnails import render_project_preview_image

@pytest.mark.usefixtures('app_context', 'project_expo2011')
@pytest.fixture()
def add_tasks_to_queue(project_expo2011):
    from funnel import rq
    rq.job_class = 'rq.job.Job'
    rq.queues = ['funnel_testing']
    return render_project_preview_image.queue(project_id=project_expo2011.id)

@pytest.mark.usefixtures('add_tasks_to_queue', 'project_expo2011', 'project_ai1',
                         'all_fixtures')
def test_preview_image_jobs(project_expo2011, project_ai1):
    assert project_expo2011.preview_image is not None
    assert project_ai1.preview_image is None
