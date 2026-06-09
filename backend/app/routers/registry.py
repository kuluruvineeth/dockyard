from fastapi import APIRouter, Response
from sqlalchemy import select

from app.dependencies import CurrentUser, DBSession
from app.errors import NotFound, ValidationException
from app.models import RegistryType, SharedRegistryCredentials
from app.schemas.registry import (
    RegistryCredentialsRequest,
    RegistryCredentialsSchema,
)

router = APIRouter()


@router.get(
    "/api/registry-credentials/",
    response_model=list[RegistryCredentialsSchema],
)
async def list_registry_credentials(user: CurrentUser, db: DBSession):
    result = await db.execute(
        select(SharedRegistryCredentials)
        .where(SharedRegistryCredentials.owner_id == user.id)
        .order_by(SharedRegistryCredentials.created_at.desc())
    )
    return [RegistryCredentialsSchema.from_credentials(c) for c in result.scalars()]


@router.post(
    "/api/registry-credentials/",
    status_code=201,
    response_model=RegistryCredentialsSchema,
)
async def create_registry_credentials(
    body: RegistryCredentialsRequest, user: CurrentUser, db: DBSession
):
    if body.registry_type not in {t.value for t in RegistryType}:
        raise ValidationException(
            "registry_type",
            "invalid",
            f"`{body.registry_type}` is not a valid registry type.",
        )

    credentials = SharedRegistryCredentials(
        owner_id=user.id,
        name=body.name,
        url=body.url,
        username=body.username,
        password=body.password,
        registry_type=body.registry_type,
    )
    db.add(credentials)
    await db.commit()
    await db.refresh(credentials)
    return RegistryCredentialsSchema.from_credentials(credentials)


@router.delete("/api/registry-credentials/{credential_id}/", status_code=204)
async def delete_registry_credentials(
    credential_id: str, user: CurrentUser, db: DBSession
):
    result = await db.execute(
        select(SharedRegistryCredentials).where(
            SharedRegistryCredentials.id == credential_id,
            SharedRegistryCredentials.owner_id == user.id,
        )
    )
    credentials = result.scalar_one_or_none()
    if credentials is None:
        raise NotFound(f"Registry credentials with id `{credential_id}` do not exist.")
    await db.delete(credentials)
    await db.commit()
    return Response(status_code=204)
