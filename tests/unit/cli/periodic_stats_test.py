"""Tests for the periodic CLI stats commands."""
# pylint: disable=redefined-outer-name

from __future__ import annotations

from typing import Dict, List, Optional, Union

from respx import MockRouter
import httpx
import pytest

from funnel.cli.periodic import stats as cli_stats

MATOMO_URL = 'https://matomo.test/'


@pytest.fixture(scope='module')
def matomo_sample_response() -> List[Dict[str, Union[str, int]]]:
    """Sample response for method=Referrers.getSocials."""
    return [
        {
            "label": "LinkedIn",
            "nb_uniq_visitors": 4,
            "nb_visits": 4,
            "nb_actions": 21,
            "nb_users": 0,
            "max_actions": 18,
            "sum_visit_length": 550,
            "bounce_count": 3,
            "nb_visits_converted": 0,
            "url": "linkedin.com",
            "logo": "plugins/Morpheus/icons/dist/socials/linkedin.com.png",
            "idsubdatatable": 2,
        },
        {
            "label": "Twitter",
            "nb_uniq_visitors": 2,
            "nb_visits": 2,
            "nb_actions": 4,
            "nb_users": 0,
            "max_actions": 3,
            "sum_visit_length": 92,
            "bounce_count": 1,
            "nb_visits_converted": 0,
            "url": "twitter.com",
            "logo": "plugins/Morpheus/icons/dist/socials/twitter.com.png",
            "idsubdatatable": 3,
        },
        {
            "label": "GitHub",
            "nb_uniq_visitors": 1,
            "nb_visits": 1,
            "nb_actions": 1,
            "nb_users": 0,
            "max_actions": 1,
            "sum_visit_length": 0,
            "bounce_count": 1,
            "nb_visits_converted": 0,
            "url": "github.com",
            "logo": "plugins/Morpheus/icons/dist/socials/github.com.png",
            "idsubdatatable": 1,
        },
    ]


def test_trend_symbol() -> None:
    """Test trend symbol given current and previous values."""
    assert cli_stats.trend_symbol(3, 1) == '⏫'
    assert cli_stats.trend_symbol(3, 2) == '🔼'
    assert cli_stats.trend_symbol(3, 3) == '⏸️'
    assert cli_stats.trend_symbol(2, 3) == '🔽'
    assert cli_stats.trend_symbol(1, 3) == '⏬'


def test_resourcestats_trend_symbol() -> None:
    r = cli_stats.ResourceStats(
        day=1,
        week=2,
        month=3,
        day_before=3,
        weekday_before=0,
        week_before=2,
        month_before=1,
    )
    r.set_trend_symbols()
    assert r.day_trend == '⏬'
    assert r.weekday_trend == '⏫'
    assert r.week_trend == '⏸️'
    assert r.month_trend == '⏫'


@pytest.mark.asyncio()
async def test_matomo_response_json_error(respx_mock: MockRouter) -> None:
    async with httpx.AsyncClient() as client:
        respx_mock.get(MATOMO_URL).mock(return_value=httpx.Response(500))
        assert await cli_stats.matomo_response_json(client, MATOMO_URL) == []


@pytest.mark.asyncio()
async def test_matomo_response_json_valid(
    respx_mock: MockRouter, matomo_sample_response: List[Dict[str, Union[str, int]]]
) -> None:
    async with httpx.AsyncClient() as client:
        respx_mock.get(MATOMO_URL).mock(
            return_value=httpx.Response(200, json=matomo_sample_response)
        )
        assert await cli_stats.matomo_response_json(client, MATOMO_URL) == [
            cli_stats.MatomoResponse(
                label='LinkedIn', nb_visits=4, nb_uniq_visitors=4, url='linkedin.com'
            ),
            cli_stats.MatomoResponse(
                label='Twitter', nb_visits=2, nb_uniq_visitors=2, url='twitter.com'
            ),
            cli_stats.MatomoResponse(
                label='GitHub', nb_visits=1, nb_uniq_visitors=1, url='github.com'
            ),
        ]


@pytest.mark.parametrize(
    ('jsondata', 'url'),
    [
        (
            {'label': 'LinkedIn', 'nb_visits': 0, 'url': 'linkedin.com'},
            'https://linkedin.com',
        ),
        (
            {
                'label': 'login',
                'nb_visits': 0,
                "url": "http://funnel.test/login",
                "segment": "pageUrl==http%253A%252F%252Ffunnel.test%252Fignored",
            },
            'http://funnel.test/login',
        ),
        (
            {
                'label': 'account',
                'nb_visits': 0,
                "segment": "pageUrl==http%253A%252F%252Ffunnel.test%252Faccount",
            },
            'http://funnel.test/account',
        ),
        ({'label': 'path', 'nb_visits': 0, 'url': '/login'}, '/login'),
        ({'label': 'no-url', 'nb_visits': 0}, None),
    ],
)
def test_matomo_response_url(jsondata: dict, url: Optional[str]) -> None:
    """Parse a valid URL from Matomo response data."""
    assert cli_stats.MatomoResponse.from_dict(jsondata).get_url() == url


@pytest.mark.asyncio()
@pytest.mark.mock_config('app', {'MATOMO_URL': None})
async def test_matomo_data_noconfig() -> None:
    """Matomo stats returns an empty result when there's no config."""
    assert await cli_stats.matomo_stats() == cli_stats.MatomoData(
        referrers=[], socials=[], pages=[]
    )
