from fastapi import Depends, Request
from platform_common.logging.logging import get_logger
from platform_common.utils.service_response import ServiceResponse
from platform_common.errors.base import NotFoundError, AuthError
from platform_common.db.dependencies.get_dal import get_dal
from platform_common.db.dal.project_dal import ProjectDAL
from platform_common.auth.permissions import PROJECT_EDIT
from platform_common.auth.guards import require_project_perm_by_id

from app.api.interface.abstract_handler import AbstractHandler

logger = get_logger("delete_project_handler")


class DeleteProjectHandler(AbstractHandler):
    """
    Handler for deleting a project by ID.
    """

    def __init__(self, project_dal: ProjectDAL = Depends(get_dal(ProjectDAL))):
        super().__init__()
        self.project_dal = project_dal

    async def do_process(self, request: Request, project_id: str) -> ServiceResponse:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise AuthError("Not authenticated")

        await require_project_perm_by_id(
            session=self.project_dal.session,
            user_id=user_id,
            project_id=project_id,
            perm_bit=PROJECT_EDIT,
        )

        deleted = await self.project_dal.delete(project_id)

        if not deleted:
            raise NotFoundError(
                message="Project not found or could not be deleted",
                code="PROJECT_NOT_FOUND",
            )

        return ServiceResponse(
            message="Project deleted successfully",
            status_code=200,
            data={"project_id": project_id},
        )
