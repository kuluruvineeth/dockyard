from faker import Faker
from fastapi import APIRouter
from sqlalchemy import and_, case, func, select
from sqlalchemy.exc import IntegrityError

from app.constants import PRODUCTION_ENV_NAME
from app.dependencies import CurrentUser, DBSession
from app.errors import NotFound, ResourceConflict
from app.models import Deployment, DeploymentStatus, Environment, Project, Service
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectSchema,
    ProjectUpdateRequest,
)
from app.temporal.client import schedule_create_project_resources

router = APIRouter()
fake = Faker()


def accessible_projects_filter(user):
    return Project.owner_id == user.id


async def _service_counts(db, project_ids):
    if not project_ids:
        return {}

    is_healthy = Deployment.status == DeploymentStatus.HEALTHY.value

    query = (
        select(
            Service.project_id,
            func.count(Service.id),
            func.sum(case((is_healthy, 1), else_=0)),
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

    project = Project(owner_id=user.id, slug=slug, description=body.description)
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
