from app.models import (
    DeploymentChange,
    Environment,
    Project,
    Service,
    User,
)


async def _service_with_changes(session, changes):
    user = User(username="changes-tester", is_active=True)
    user.set_password("password123")
    session.add(user)
    await session.flush()

    project = Project(owner_id=user.id, slug="proj")
    project.environments = [Environment(name="production")]
    session.add(project)
    await session.flush()

    service = Service(
        slug="svc",
        project_id=project.id,
        environment_id=project.environments[0].id,
    )
    service.urls = []
    service.ports = []
    service.configs = []
    service.volumes = []
    service.env_variables = []
    service.changes = changes
    session.add(service)
    await session.flush()
    return service


class TestApplyPendingChanges:
    async def test_apply_source_change(self, session):
        service = await _service_with_changes(
            session,
            [
                DeploymentChange(
                    type="UPDATE", field="source", new_value={"image": "redis:alpine"}
                )
            ],
        )
        service.apply_pending_changes()
        assert service.image == "redis:alpine"
        assert all(change.applied for change in service.changes)
        assert len(service.unapplied_changes) == 0

    async def test_apply_command_change(self, session):
        service = await _service_with_changes(
            session,
            [DeploymentChange(type="UPDATE", field="command", new_value="npm start")],
        )
        service.apply_pending_changes()
        assert service.command == "npm start"

    async def test_apply_resource_limits(self, session):
        service = await _service_with_changes(
            session,
            [
                DeploymentChange(
                    type="UPDATE",
                    field="resource_limits",
                    new_value={"cpus": 1, "memory": {"value": 512}},
                )
            ],
        )
        service.apply_pending_changes()
        assert service.resource_limits == {"cpus": 1, "memory": {"value": 512}}

    async def test_apply_healthcheck(self, session):
        service = await _service_with_changes(
            session,
            [
                DeploymentChange(
                    type="UPDATE",
                    field="healthcheck",
                    new_value={"type": "PATH", "value": "/health"},
                )
            ],
        )
        service.apply_pending_changes()
        assert service.healthcheck is not None
        assert service.healthcheck.value == "/health"
        assert service.healthcheck.timeout_seconds == 60

    async def test_apply_env_add_then_delete(self, session):
        add = DeploymentChange(
            type="ADD", field="env_variables", new_value={"key": "FOO", "value": "bar"}
        )
        service = await _service_with_changes(session, [add])
        service.apply_pending_changes()
        assert len(service.env_variables) == 1
        assert service.env_variables[0].key == "FOO"
        assert add.item_id == service.env_variables[0].id

        delete = DeploymentChange(
            type="DELETE", field="env_variables", item_id=add.item_id
        )
        service.changes.append(delete)
        service.apply_pending_changes()
        assert len(service.env_variables) == 0

    async def test_apply_url_add(self, session):
        service = await _service_with_changes(
            session,
            [
                DeploymentChange(
                    type="ADD",
                    field="urls",
                    new_value={"domain": "app.dky.local", "base_path": "/"},
                )
            ],
        )
        service.apply_pending_changes()
        assert len(service.urls) == 1
        assert service.urls[0].domain == "app.dky.local"

    async def test_apply_port_add(self, session):
        service = await _service_with_changes(
            session,
            [
                DeploymentChange(
                    type="ADD", field="ports", new_value={"forwarded": 8080}
                )
            ],
        )
        service.apply_pending_changes()
        assert len(service.ports) == 1
        assert service.ports[0].forwarded == 8080

    async def test_apply_config_update_bumps_version(self, session):
        add = DeploymentChange(
            type="ADD",
            field="configs",
            new_value={"name": "cfg", "mount_path": "/c", "contents": "a"},
        )
        service = await _service_with_changes(session, [add])
        service.apply_pending_changes()
        assert service.configs[0].version == 1

        update = DeploymentChange(
            type="UPDATE",
            field="configs",
            item_id=add.item_id,
            new_value={"contents": "b"},
        )
        service.changes.append(update)
        service.apply_pending_changes()
        assert service.configs[0].version == 2
        assert service.configs[0].contents == "b"


class TestAddChange:
    async def test_collapses_single_value_fields(self, session):
        service = await _service_with_changes(session, [])
        service.add_change(
            DeploymentChange(type="UPDATE", field="source", new_value={"image": "a"})
        )
        service.add_change(
            DeploymentChange(type="UPDATE", field="source", new_value={"image": "b"})
        )
        source_changes = [c for c in service.unapplied_changes if c.field == "source"]
        assert len(source_changes) == 1
        assert source_changes[0].new_value["image"] == "b"

    async def test_keeps_multi_value_fields(self, session):
        service = await _service_with_changes(session, [])
        service.add_change(
            DeploymentChange(
                type="ADD", field="env_variables", new_value={"key": "A", "value": "1"}
            )
        )
        service.add_change(
            DeploymentChange(
                type="ADD", field="env_variables", new_value={"key": "B", "value": "2"}
            )
        )
        env_changes = [
            c for c in service.unapplied_changes if c.field == "env_variables"
        ]
        assert len(env_changes) == 2
