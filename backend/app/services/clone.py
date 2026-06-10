import secrets

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select

from app.models import (
    Config,
    Environment,
    EnvVariable,
    HealthCheck,
    PortConfiguration,
    PreviewDeployState,
    PreviewEnvMetadata,
    PreviewSourceTrigger,
    Project,
    Service,
    Volume,
)

_SKIP_COLUMNS = {"id", "created_at", "updated_at", "service_id"}


def _clone_row(obj, cls):
    data = {
        c.key: getattr(obj, c.key)
        for c in sa_inspect(cls).column_attrs
        if c.key not in _SKIP_COLUMNS
    }
    return cls(**data)


async def clone_environment(
    db, base_env, new_name, project, is_preview: bool = False
) -> Environment:
    new_env = Environment(name=new_name, project_id=project.id, is_preview=is_preview)
    db.add(new_env)
    await db.flush()

    services = (
        (await db.execute(select(Service).where(Service.environment_id == base_env.id)))
        .scalars()
        .all()
    )

    for svc in services:
        cloned = _clone_row(svc, Service)
        cloned.environment_id = new_env.id
        cloned.project_id = project.id
        cloned.deploy_token = secrets.token_hex(16)
        cloned.ports = [_clone_row(p, PortConfiguration) for p in svc.ports]
        cloned.volumes = [_clone_row(v, Volume) for v in svc.volumes]
        cloned.env_variables = [_clone_row(e, EnvVariable) for e in svc.env_variables]
        cloned.configs = [_clone_row(c, Config) for c in svc.configs]
        cloned.healthcheck = (
            _clone_row(svc.healthcheck, HealthCheck)
            if svc.healthcheck is not None
            else None
        )
        # URLs are intentionally not cloned — they would clash with the originals.
        cloned.urls = []
        cloned.changes = []
        cloned.deployments = []
        db.add(cloned)

    await db.commit()
    return new_env


async def create_preview_environment(
    db,
    template,
    git_app,
    branch_name: str,
    head_repository_url: str,
    pr_number: int | None = None,
    source_trigger: str = PreviewSourceTrigger.PULL_REQUEST.value,
) -> Environment:
    project = await db.get(Project, template.project_id)
    name = (
        (f"preview-{pr_number}" if pr_number is not None else f"preview-{branch_name}")
        .lower()
        .replace("/", "-")
    )

    new_env = await clone_environment(
        db, template.base_environment, name, project, is_preview=True
    )

    metadata = PreviewEnvMetadata(
        environment_id=new_env.id,
        template_id=template.id,
        git_app_id=git_app.id if git_app is not None else None,
        pr_number=pr_number,
        branch_name=branch_name,
        head_repository_url=head_repository_url,
        source_trigger=source_trigger,
        deploy_state=PreviewDeployState.APPROVED.value,
        auto_teardown=template.auto_teardown,
    )
    db.add(metadata)
    await db.commit()
    await db.refresh(new_env)
    return new_env
