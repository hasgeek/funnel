"""Test sessions"""
from datetime import datetime, timedelta
from types import SimpleNamespace

from pytz import utc
import pytest

from funnel.models import Project, Session


@pytest.fixture(scope='module')
def block_of_sessions(test_db_structure, create_project):
    db = test_db_structure
    project = create_project

    # DocType HTML5's schedule, but using UTC to simplify testing
    # https://hasgeek.com/doctypehtml5/bangalore/schedule
    session1 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 9, 0, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 10, 0, tzinfo=utc),
        title="Registration",
        is_break=True,
    )
    session2 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 10, 0, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 10, 15, tzinfo=utc),
        title="Introduction",
    )
    session3 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 10, 15, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 11, 15, tzinfo=utc),
        title="Business Case for HTML5",
    )
    session4 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 11, 15, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 12, 15, tzinfo=utc),
        title="New Ideas in HTML5",
    )
    session5 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 12, 15, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 12, 30, tzinfo=utc),
        title="Tea & Coffee Break",
        is_break=True,
    )
    session6 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 12, 30, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 13, 30, tzinfo=utc),
        title="CSS3 and Presentation",
    )
    # Deliberately leave out lunch break at session 7 to break the block
    session8 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 14, 30, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 14, 45, tzinfo=utc),
        title="Quiz",
    )
    session9 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 14, 45, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 15, 45, tzinfo=utc),
        title="Multimedia Kit",
    )
    session10 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 15, 45, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 16, 0, tzinfo=utc),
        title="Tea & Coffee Break",
        is_break=True,
    )
    session11 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 16, 0, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 17, 0, tzinfo=utc),
        title="Location, Offline and Mobile",
    )
    session12 = Session(
        project=project,
        start_at=datetime(2010, 10, 9, 17, 0, tzinfo=utc),
        end_at=datetime(2010, 10, 9, 17, 15, tzinfo=utc),
        title="Closing Remarks",
    )

    refresh_attrs = [attr for attr in locals().values() if isinstance(attr, db.Model)]
    db.session.add_all(refresh_attrs)
    db.session.commit()

    def refresh():
        for attr in refresh_attrs:
            db.session.add(attr)

    return SimpleNamespace(**locals())


def test_project_starting_at(db_transaction, block_of_sessions):
    block_of_sessions.refresh()

    # Loop through the day at 5 min intervals from 8 AM, looking for start time
    starting_times = [
        datetime(2010, 10, 9, 8, 0, tzinfo=utc) + timedelta(minutes=5) * multipler
        for multipler in range(100)
    ]

    # Keep the timestamps at which projects were found, plus the project. Criteria:
    # starts in range timestamp + up to 5 minutes, gap of 1 hour from prior sessions
    found_projects = {
        timestamp: found
        for timestamp, found in {
            timestamp: Project.starting_at(
                timestamp, timedelta(minutes=5), timedelta(minutes=60)
            ).all()
            for timestamp in starting_times
        }.items()
        if found
    }

    # Confirm we found two starting times at 9 AM and 2:30 PM
    assert found_projects == {
        datetime(2010, 10, 9, 9, 0, tzinfo=utc): [block_of_sessions.project],
        datetime(2010, 10, 9, 14, 30, tzinfo=utc): [block_of_sessions.project],
    }

    # Confirm we can retrieve the session as well
    found_sessions = {
        timestamp: [project.next_session_from(timestamp) for project in project_list]
        for timestamp, project_list in found_projects.items()
    }
    assert found_sessions == {
        datetime(2010, 10, 9, 9, 0, tzinfo=utc): [block_of_sessions.session1],
        datetime(2010, 10, 9, 14, 30, tzinfo=utc): [block_of_sessions.session8],
    }

    # Repeat search with 120 minute gap requirement instead of 60. Now we find a single
    # match
    found_projects = {
        timestamp: found
        for timestamp, found in {
            timestamp: Project.starting_at(
                timestamp, timedelta(minutes=5), timedelta(minutes=120)
            ).all()
            for timestamp in starting_times
        }.items()
        if found
    }

    # Confirm we found a single starting time at 9 AM
    assert found_projects == {
        datetime(2010, 10, 9, 9, 0, tzinfo=utc): [block_of_sessions.project],
    }
