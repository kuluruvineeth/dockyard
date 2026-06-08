async def test_ping(client):
    response = await client.get("/api/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}
