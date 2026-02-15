from fastapi import Request, Depends
from platform_common.db.dal.project_dal import ProjectDAL
from app.api.interface.abstract_handler import AbstractHandler
from platform_common.utils.service_response import ServiceResponse
from platform_common.logging.logging import get_logger
from platform_common.models.project import Project
from platform_common.db.dependencies.get_dal import get_dal
from platform_common.errors.base import BadRequestError, AuthError
from platform_common.auth.permissions import ORG_CREATE_PROJECT
from platform_common.auth.guards import require_org_perm_by_id

logger = get_logger("create_project_handler")


class CreateProjectHandler(AbstractHandler):
    """
    Handler for creating a project.
    """

    def __init__(
        self,
        project_dal: ProjectDAL = Depends(get_dal(ProjectDAL)),
    ):
        super().__init__()
        self.project_dal = project_dal

    async def do_process(self, request: Request) -> ServiceResponse:
        """
        Handle the request to create a project.
        """
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise AuthError("Not authenticated")

        try:
            payload = await request.json()
            payload["owner_id"] = user_id
            payload.setdefault("owner_type", "user")

            organization_id = payload.get("organization_id")
            if organization_id:
                await require_org_perm_by_id(
                    session=self.project_dal.session,
                    user_id=user_id,
                    organization_id=organization_id,
                    perm_bit=ORG_CREATE_PROJECT,
                )
            project = Project(**payload)
        except TypeError as e:
            logger.error(f"Error creating project: {e}")
            raise BadRequestError(
                message="Invalid project data", code="INVALID_PAYLOAD"
            )

        created_project = await self.project_dal.create(project)
        logger.info(f"Project created: {created_project.id}")
        return ServiceResponse(
            success=True,
            message="Project created successfully",
            status_code=201,
            data=created_project.dict(),
        )
