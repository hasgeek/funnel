"""Tests for the periodic CLI stats commands."""
# pylint: disable=redefined-outer-name

from __future__ import annotations

import httpx
import pytest
from respx import MockRouter

from funnel.cli.periodic import mnrl as cli_mnrl

MNRL_FILES_URL = 'https://mnrl.trai.gov.in/api/mnrl/files/{apikey}'
MNRL_JSON_URL = 'https://mnrl.trai.gov.in/api/mnrl/json/{filename}/{apikey}'


@pytest.fixture(scope='module')
def mnrl_files_response() -> bytes:
    """Sample response for MNRL files API."""
    return b''


@pytest.fixture(scope='module')
def mnrl_json_response() -> bytes:
    """Sample response for MNRL JSON API."""
    return (
        b'{"status":200,"file_name":"test.json",'
        b'"payload":[{"n":"1111111111"},{"n":"2222222222"},{"n":"3333333333"}]}'
    )


@pytest.mark.asyncio()
@pytest.mark.mock_config('app', {'MNRL_API_KEY': '12345'})
async def test_mnrl_file_numbers(
    respx_mock: MockRouter, mnrl_json_response: bytes
) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        respx_mock.get(MNRL_JSON_URL.format(apikey='12345', filename='test.json')).mock(
            return_value=httpx.Response(200, content=mnrl_json_response)
        )
        assert await cli_mnrl.get_mnrl_json_file_numbers(
            client, apikey='12345', filename='test.json'
        ) == ('test.json', {'1111111111', '2222222222', '3333333333'})
