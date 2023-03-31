import pytest


@pytest.mark.asyncio
async def test_ping(api_client, event_loop):
    response = await api_client.get("/ping")
    assert response.status_code == 200
    assert response.text == "pong"


@pytest.mark.asyncio
async def test_deep_ping(api_client, event_loop):
    response = await api_client.get("/deep-ping")
    assert response.status_code == 200
    assert response.text
