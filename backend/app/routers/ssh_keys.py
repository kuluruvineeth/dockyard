from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, DBSession
from app.errors import NotFound, ResourceConflict
from app.models import SSHKey
from app.models.base import generate_id
from app.schemas.ssh_keys import SSHKeyCreateRequest, SSHKeySchema

router = APIRouter()


@router.get("/api/ssh-keys/", response_model=list[SSHKeySchema])
async def list_ssh_keys(user: CurrentUser, db: DBSession):
    result = await db.execute(select(SSHKey).order_by(SSHKey.created_at.desc()))
    return [SSHKeySchema.from_ssh_key(k) for k in result.scalars()]


@router.post("/api/ssh-keys/", status_code=201, response_model=SSHKeySchema)
async def create_ssh_key(body: SSHKeyCreateRequest, user: CurrentUser, db: DBSession):
    public_key, private_key = SSHKey.create_key_pair()
    key = SSHKey(
        id=generate_id("ssh_"),
        slug=body.slug,
        user=body.user,
        public_key=public_key,
        private_key=private_key,
        fingerprint=SSHKey.generate_fingerprint(public_key),
    )
    db.add(key)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"An SSH key with the slug `{body.slug}` already exists."
        )
    await db.refresh(key)
    return SSHKeySchema.from_ssh_key(key)


@router.delete("/api/ssh-keys/{slug}/", status_code=204)
async def delete_ssh_key(slug: str, user: CurrentUser, db: DBSession):
    result = await db.execute(select(SSHKey).where(SSHKey.slug == slug))
    key = result.scalar_one_or_none()
    if key is None:
        raise NotFound(f"An SSH key with the slug `{slug}` does not exist.")
    await db.delete(key)
    await db.commit()
    return Response(status_code=204)
