import logging

import docker.errors
from faker import Faker
from fastapi import APIRouter, Response
from sqlalchemy import and_, case, func, select
from sqlalchemy.exc import IntegrityError

from app import docker_helpers
from app.constants import PRODUCTION_ENV_NAME
from app.dependencies import CurrentUser, DBSession
from app.errors import NotFound, ResourceConflict
from app.models import (
    Deployment,
    DeploymentStatus,
    Environment,
    Project,
    Service,
    SharedEnvVariable,
    WorkspaceMembership,
)
from app.schemas.projects import (
    CreateEnvironmentRequest,
    ProjectCreateRequest,
    ProjectSchema,
    ProjectUpdateRequest,
    SharedEnvVariableRequest,
    SharedEnvVariableSchema,
    SimpleEnvironmentSchema,
)
from app.services import networks, proxy
from app.services.clone import clone_environment
from app.services.workspaces import get_current_workspace
from app.temporal.client import schedule_create_project_resources

_logger = logging.getLogger("dockyard.projects")

router = APIRouter()
fake = Faker()


def accessible_projects_filter(user):
    return Project.workspace_id.in_(
        select(WorkspaceMembership.workspace_id).where(
            WorkspaceMembership.user_id == user.id
        )
    )


async def _service_counts(db, project_ids):
    if not project_ids:
        return {}

    is_regular = Service.compose_stack_id.is_(None)
    is_stack = Service.compose_stack_id.is_not(None)
    is_healthy = Deployment.status == DeploymentStatus.HEALTHY.value

    query = (
        select(
            Service.project_id,
            func.sum(case((is_regular, 1), else_=0)),
            func.sum(case((and_(is_regular, is_healthy), 1), else_=0)),
            func.sum(case((is_stack, 1), else_=0)),
            func.sum(case((and_(is_stack, is_healthy), 1), else_=0)),
        )
        .select_from(Service)
        .outerjoin(
            Deployment,
            and_(
                Deployment.service_id == Service.id,
                Deployment.is_current_production.is_(True),
            ),
        )
        .where(Service.project_id.in_(project_ids))
        .group_by(Service.project_id)
    )

    result = await db.execute(query)
    return {
        row[0]: {
            "total_services": row[1] or 0,
            "healthy_services": row[2] or 0,
            "total_stack_services": row[3] or 0,
            "healthy_stack_services": row[4] or 0,
        }
        for row in result.all()
    }


@router.get("/api/projects/", response_model=list[ProjectSchema])
async def list_projects(
    user: CurrentUser,
    db: DBSession,
    slug: str | None = None,
    sort_by: str | None = None,
):
    query = select(Project).where(accessible_projects_filter(user))
    if slug:
        query = query.where(Project.slug.icontains(slug))
    if sort_by == "slug":
        query = query.order_by(Project.slug)
    else:
        query = query.order_by(Project.updated_at.desc())

    result = await db.execute(query)
    projects = result.scalars().all()
    counts = await _service_counts(db, [project.id for project in projects])
    return [
        ProjectSchema.from_project(project, **counts.get(project.id, {}))
        for project in projects
    ]


@router.post("/api/projects/", status_code=201, response_model=ProjectSchema)
async def create_project(body: ProjectCreateRequest, user: CurrentUser, db: DBSession):
    slug = (body.slug or fake.slug() or "project").lower()

    workspace = await get_current_workspace(db, user)
    project = Project(
        owner_id=user.id,
        workspace_id=workspace.id if workspace is not None else None,
        slug=slug,
        description=body.description,
    )
    project.environments = [Environment(name=PRODUCTION_ENV_NAME)]
    db.add(project)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(f"A project with the slug `{slug}` already exists.")

    result = await db.execute(select(Project).where(Project.id == project.id))
    project = result.scalar_one()
    if project.production_env is not None:
        await schedule_create_project_resources(project.id, project.production_env.id)
    return ProjectSchema.from_project(project)


async def _get_project_or_404(db, user, slug: str) -> Project:
    result = await db.execute(
        select(Project).where(Project.slug == slug, accessible_projects_filter(user))
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFound(f"A project with the slug `{slug}` does not exist.")
    return project


@router.get("/api/projects/{slug}/", response_model=ProjectSchema)
async def get_project(slug: str, user: CurrentUser, db: DBSession):
    project = await _get_project_or_404(db, user, slug)
    counts = await _service_counts(db, [project.id])
    return ProjectSchema.from_project(project, **counts.get(project.id, {}))


@router.put("/api/projects/{slug}/", response_model=ProjectSchema)
async def update_project(
    slug: str, body: ProjectUpdateRequest, user: CurrentUser, db: DBSession
):
    project = await _get_project_or_404(db, user, slug)

    if body.slug is not None:
        project.slug = body.slug.lower()
    if body.description is not None:
        project.description = body.description

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"The slug `{body.slug}` is already used by another project."
        )

    result = await db.execute(select(Project).where(Project.id == project.id))
    return ProjectSchema.from_project(result.scalar_one())


@router.delete("/api/projects/{slug}/", status_code=204)
async def archive_project(slug: str, user: CurrentUser, db: DBSession):
    project = await _get_project_or_404(db, user, slug)

    services = (
        (await db.execute(select(Service).where(Service.project_id == project.id)))
        .scalars()
        .all()
    )

    client = docker_helpers.get_docker_client()
    for service in services:
        for deployment in service.deployments:
            swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
                deployment.unprefixed_hash, project.id, service.id
            )
            try:
                client.services.get(swarm_name).remove()
            except docker.errors.NotFound:
                pass
            except Exception as error:  # noqa: BLE001
                _logger.warning("could not remove swarm service: %s", error)
        try:
            proxy.unexpose_service_from_http(service)
        except Exception as error:  # noqa: BLE001
            _logger.warning("could not unexpose service: %s", error)

    try:
        networks.remove_project_networks(project.id)
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not remove project networks: %s", error)

    await db.delete(project)
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/api/projects/{project_slug}/environments/",
    status_code=201,
    response_model=SimpleEnvironmentSchema,
)
async def create_environment(
    project_slug: str,
    body: CreateEnvironmentRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await _get_project_or_404(db, user, project_slug)
    name = body.name.lower()

    environment = Environment(name=name, project_id=project.id)
    db.add(environment)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"An environment with the name `{name}` already exists in this project."
        )

    await db.refresh(environment, ["created_at"])
    try:
        networks.create_environment_network(environment.id, project.id)
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not create environment network: %s", error)

    return SimpleEnvironmentSchema.from_environment(environment)


@router.post(
    "/api/projects/{project_slug}/environments/{env_slug}/clone/",
    status_code=201,
    response_model=SimpleEnvironmentSchema,
)
async def clone_environment_view(
    project_slug: str,
    env_slug: str,
    body: CreateEnvironmentRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await _get_project_or_404(db, user, project_slug)
    base_env = await _get_environment_or_404(db, project, env_slug)
    new_name = body.name.lower()

    try:
        new_env = await clone_environment(db, base_env, new_name, project)
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"An environment with the name `{new_name}` already exists in this project."
        )

    await db.refresh(new_env, ["created_at"])
    try:
        networks.create_environment_network(new_env.id, project.id)
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not create environment network: %s", error)

    return SimpleEnvironmentSchema.from_environment(new_env)


@router.delete("/api/projects/{project_slug}/environments/{env_slug}/", status_code=204)
async def delete_environment(
    project_slug: str, env_slug: str, user: CurrentUser, db: DBSession
):
    project = await _get_project_or_404(db, user, project_slug)

    result = await db.execute(
        select(Environment).where(
            Environment.project_id == project.id,
            Environment.name == env_slug.lower(),
        )
    )
    environment = result.scalar_one_or_none()
    if environment is None:
        raise NotFound(
            f"An environment with the name `{env_slug}` does not exist in this project."
        )
    if environment.name == PRODUCTION_ENV_NAME:
        raise ResourceConflict("You cannot delete the production environment.")

    try:
        networks.delete_environment_network(environment.id, project.id)
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not delete environment network: %s", error)

    await db.delete(environment)
    await db.commit()
    return Response(status_code=204)


async def _get_environment_or_404(db, project, env_slug):
    result = await db.execute(
        select(Environment).where(
            Environment.project_id == project.id,
            Environment.name == env_slug.lower(),
        )
    )
    environment = result.scalar_one_or_none()
    if environment is None:
        raise NotFound(
            f"An environment with the name `{env_slug}` does not exist in this project."
        )
    return environment


@router.get(
    "/api/projects/{project_slug}/environments/{env_slug}/variables/",
    response_model=list[SharedEnvVariableSchema],
)
async def list_environment_variables(
    project_slug: str, env_slug: str, user: CurrentUser, db: DBSession
):
    project = await _get_project_or_404(db, user, project_slug)
    environment = await _get_environment_or_404(db, project, env_slug)
    return [SharedEnvVariableSchema.from_variable(v) for v in environment.variables]


@router.post(
    "/api/projects/{project_slug}/environments/{env_slug}/variables/",
    status_code=201,
    response_model=SharedEnvVariableSchema,
)
async def create_environment_variable(
    project_slug: str,
    env_slug: str,
    body: SharedEnvVariableRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await _get_project_or_404(db, user, project_slug)
    environment = await _get_environment_or_404(db, project, env_slug)

    variable = SharedEnvVariable(
        key=body.key, value=body.value, environment_id=environment.id
    )
    db.add(variable)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"A variable with the key `{body.key}` already exists in this environment."
        )
    await db.refresh(variable)
    return SharedEnvVariableSchema.from_variable(variable)


@router.delete(
    "/api/projects/{project_slug}/environments/{env_slug}/variables/{variable_id}/",
    status_code=204,
)
async def delete_environment_variable(
    project_slug: str,
    env_slug: str,
    variable_id: str,
    user: CurrentUser,
    db: DBSession,
):
    project = await _get_project_or_404(db, user, project_slug)
    environment = await _get_environment_or_404(db, project, env_slug)

    variable = next((v for v in environment.variables if v.id == variable_id), None)
    if variable is None:
        raise NotFound(
            f"A variable with the id `{variable_id}` does not exist in this environment."
        )
    await db.delete(variable)
    await db.commit()
    return Response(status_code=204)
