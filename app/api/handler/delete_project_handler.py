from fastapi import Depends
from platform_common.logging.logging import get_logger
from platform_common.utils.service_response import ServiceResponse
from platform_common.errors.base import NotFoundError
from platform_common.db.dependencies.get_dal import get_dal
from platform_common.db.dal.project_dal import ProjectDAL

from app.api.interface.abstract_handler import AbstractHandler

logger = get_logger("delete_project_handler")


class DeleteProjectHandler(AbstractHandler):
    """
    Handler for deleting a project by ID.
    """

    def __init__(self, project_dal: ProjectDAL = Depends(get_dal(ProjectDAL))):
        super().__init__()
        self.project_dal = project_dal

    async def do_process(self, project_id: str) -> ServiceResponse:
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
