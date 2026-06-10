from sqlalchemy import select

from app.models import (
    Environment,
    EnvVariable,
    PortConfiguration,
    Project,
    Service,
)


class TestCloneEnvironment:
    async def test_clone_copies_services_and_config(self, auth_client, session):
        await auth_client.post("/api/projects/", json={"slug": "proj"})
        await auth_client.post(
            "/api/projects/proj/production/create-service/docker/",
            json={"slug": "web", "image": "nginx:latest"},
        )

        project = (
            await session.execute(select(Project).where(Project.slug == "proj"))
        ).scalar_one()
        prod = (
            await session.execute(
                select(Environment).where(Environment.project_id == project.id)
            )
        ).scalar_one()
        svc = (
            await session.execute(
                select(Service).where(Service.environment_id == prod.id)
            )
        ).scalar_one()
        svc.image = "nginx:latest"
        svc.env_variables = [EnvVariable(key="FOO", value="bar")]
        svc.ports = [PortConfiguration(host=8080, forwarded=80)]
        await session.commit()
        old_token = svc.deploy_token

        response = await auth_client.post(
            "/api/projects/proj/environments/production/clone/",
            json={"name": "preview"},
        )
        assert response.status_code == 201
        assert response.json()["name"] == "preview"

        new_env = (
            await session.execute(
                select(Environment).where(
                    Environment.project_id == project.id,
                    Environment.name == "preview",
                )
            )
        ).scalar_one()
        cloned = (
            (
                await session.execute(
                    select(Service).where(Service.environment_id == new_env.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(cloned) == 1
        c = cloned[0]
        assert c.slug == "web"
        assert c.image == "nginx:latest"
        assert c.deploy_token != old_token
        assert {e.key: e.value for e in c.env_variables} == {"FOO": "bar"}
        assert [p.host for p in c.ports] == [8080]
        assert c.urls == []

        # the original environment is untouched
        prod_services = (
            (
                await session.execute(
                    select(Service).where(Service.environment_id == prod.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(prod_services) == 1

    async def test_clone_name_conflict(self, auth_client):
        await auth_client.post("/api/projects/", json={"slug": "p2"})
        response = await auth_client.post(
            "/api/projects/p2/environments/production/clone/",
            json={"name": "production"},
        )
        assert response.status_code == 409
