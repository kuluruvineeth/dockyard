class TestDockerImageSearch:
    async def test_search_docker_images(self, auth_client):
        response = await auth_client.get(
            "/api/docker/image-search/", params={"q": "caddy"}
        )
        assert response.status_code == 200
        images = response.json().get("images")
        assert images is not None
        assert images[0]["full_image"] == "caddy"
        assert images[1]["full_image"] == "siwecos/caddy"

    async def test_search_query_empty(self, auth_client):
        response = await auth_client.get("/api/docker/image-search/")
        assert response.status_code == 400

    async def test_requires_auth(self, client):
        response = await client.get("/api/docker/image-search/", params={"q": "x"})
        assert response.status_code == 401
