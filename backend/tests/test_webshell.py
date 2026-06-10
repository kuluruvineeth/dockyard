from app.models import SSHKey

SSH = "/api/ssh-keys/"


class TestSSHKeyModel:
    def test_create_key_pair(self):
        public, private = SSHKey.create_key_pair()
        assert public.startswith("ssh-rsa ")
        assert "BEGIN PRIVATE KEY" in private

    def test_generate_fingerprint(self):
        public, _ = SSHKey.create_key_pair()
        fp = SSHKey.generate_fingerprint(public)
        assert fp.startswith("SHA256:")
        # deterministic for the same key
        assert SSHKey.generate_fingerprint(public) == fp


class TestSSHKeyCRUD:
    async def test_create_generates_keypair(self, auth_client):
        response = await auth_client.post(
            SSH, json={"slug": "my-key", "user": "deploy"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-key"
        assert data["public_key"].startswith("ssh-rsa ")
        assert data["fingerprint"].startswith("SHA256:")
        # the private key must never be returned
        assert "private_key" not in data

    async def test_list(self, auth_client):
        await auth_client.post(SSH, json={"slug": "k1", "user": "u"})
        response = await auth_client.get(SSH)
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_slug_conflict(self, auth_client):
        await auth_client.post(SSH, json={"slug": "dup", "user": "u"})
        response = await auth_client.post(SSH, json={"slug": "dup", "user": "u"})
        assert response.status_code == 409

    async def test_delete(self, auth_client):
        await auth_client.post(SSH, json={"slug": "gone", "user": "u"})
        response = await auth_client.delete(f"{SSH}gone/")
        assert response.status_code == 204
        assert len((await auth_client.get(SSH)).json()) == 0

    async def test_delete_nonexistent(self, auth_client):
        response = await auth_client.delete(f"{SSH}nope/")
        assert response.status_code == 404
