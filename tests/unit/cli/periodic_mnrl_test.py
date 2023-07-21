"""Tests for the periodic CLI stats commands."""
# pylint: disable=redefined-outer-name

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from click.testing import CliRunner
from respx import MockRouter

from funnel.cli.periodic import mnrl as cli_mnrl, periodic

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


# --- CLI interface


@pytest.mark.mock_config('app', {'MNRL_API_KEY': ...})
def test_cli_mnrl_needs_api_key() -> None:
    """CLI command requires API key in config."""
    runner = CliRunner()
    result = runner.invoke(periodic, ['mnrl'])
    assert "App config is missing `MNRL_API_KEY`" in result.output
    assert result.exit_code == 2


@pytest.mark.mock_config('app', {'MNRL_API_KEY': '12345'})
def test_cli_mnrl_accepts_api_key() -> None:
    """CLI command runs if an API key is present."""
    with patch('funnel.cli.periodic.mnrl.process_mnrl', return_value=None) as mock:
        runner = CliRunner()
        runner.invoke(periodic, ['mnrl'])
        assert mock.called
