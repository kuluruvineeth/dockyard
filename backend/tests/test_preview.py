from sqlalchemy import select

from app.models import (
    Environment,
    PreviewEnvTemplate,
    Project,
    Service,
)
from app.services.clone import create_preview_environment


class TestCreatePreviewEnvironment:
    async def test_creates_preview_env_with_metadata(self, auth_client, session):
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
                select(Environment).where(
                    Environment.project_id == project.id,
                    Environment.name == "production",
                )
            )
        ).scalar_one()

        template = PreviewEnvTemplate(
            project_id=project.id,
            slug="default",
            base_environment_id=prod.id,
            auto_teardown=True,
            is_default=True,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        preview = await create_preview_environment(
            session,
            template,
            None,
            "feature/login",
            "https://github.com/o/r.git",
            pr_number=42,
        )

        assert preview.is_preview is True
        assert preview.name == "preview-42"
        assert preview.preview_metadata is not None
        assert preview.preview_metadata.pr_number == 42
        assert preview.preview_metadata.branch_name == "feature/login"
        assert preview.preview_metadata.deploy_state == "APPROVED"
        assert preview.preview_metadata.auto_teardown is True

        cloned = (
            (
                await session.execute(
                    select(Service).where(Service.environment_id == preview.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(cloned) == 1
        assert cloned[0].slug == "web"

    async def test_preview_env_name_from_branch_when_no_pr(self, auth_client, session):
        await auth_client.post("/api/projects/", json={"slug": "p2"})
        project = (
            await session.execute(select(Project).where(Project.slug == "p2"))
        ).scalar_one()
        prod = (
            await session.execute(
                select(Environment).where(Environment.project_id == project.id)
            )
        ).scalar_one()
        template = PreviewEnvTemplate(
            project_id=project.id,
            slug="default",
            base_environment_id=prod.id,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        preview = await create_preview_environment(
            session, template, None, "feat/x", "https://github.com/o/r.git"
        )
        assert preview.name == "preview-feat-x"
        assert preview.preview_metadata.pr_number is None
