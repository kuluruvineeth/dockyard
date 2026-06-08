from faker import Faker
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.constants import PRODUCTION_ENV_NAME
from app.dependencies import CurrentUser, DBSession
from app.errors import ResourceConflict
from app.models import Environment, Project
from app.schemas.projects import ProjectCreateRequest, ProjectSchema

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
    return ProjectSchema.from_project(result.scalar_one())
