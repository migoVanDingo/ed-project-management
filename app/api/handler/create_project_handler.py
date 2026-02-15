from fastapi import Request, Depends
from pydantic import ValidationError
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
            owner_type = str(payload.get("owner_type", "user")).lower()
            if owner_type == "organization":
                owner_type = "org"
            if owner_type not in {"user", "org"}:
                raise BadRequestError(
                    message="owner_type must be either 'user' or 'org'",
                    code="INVALID_OWNER_TYPE",
                )

            payload["owner_id"] = user_id
            payload["owner_type"] = owner_type

            if owner_type == "org":
                organization_id = payload.get("organization_id")
                if not organization_id:
                    raise BadRequestError(
                        message="organization_id is required when owner_type is 'org'",
                        code="ORGANIZATION_ID_REQUIRED",
                    )
                await require_org_perm_by_id(
                    session=self.project_dal.session,
                    user_id=user_id,
                    organization_id=organization_id,
                    perm_bit=ORG_CREATE_PROJECT,
                )
            else:
                # Ensure user-scoped project creation never triggers org checks by accident.
                payload["organization_id"] = None
            project = Project(**payload)
        except BadRequestError:
            raise
        except (TypeError, ValidationError) as e:
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
