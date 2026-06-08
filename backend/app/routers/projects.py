from faker import Faker
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.constants import PRODUCTION_ENV_NAME
from app.dependencies import CurrentUser, DBSession
from app.errors import NotFound, ResourceConflict
from app.models import Environment, Project
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
    return [ProjectSchema.from_project(project) for project in projects]


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
    return ProjectSchema.from_project(project)


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
