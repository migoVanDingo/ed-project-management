from fastapi import Request, Depends
from app.api.interface.abstract_handler import AbstractHandler
from platform_common.utils.service_response import ServiceResponse
from platform_common.logging.logging import get_logger
from platform_common.errors.base import BadRequestError, NotFoundError
from platform_common.db.dependencies.get_dal import get_dal
from platform_common.db.dal.project_dal import ProjectDAL

logger = get_logger("update_project_handler")


class UpdateProjectHandler(AbstractHandler):
    """
    Handler for updating project information.
    """

    def __init__(self, project_dal: ProjectDAL = Depends(get_dal(ProjectDAL))):
        super().__init__()
        self.project_dal = project_dal

    async def do_process(self, request: Request, project_id: str) -> ServiceResponse:

        update_data = await request.json()

        if not update_data:
            raise BadRequestError(message="Missing update data", code="NO_UPDATE_DATA")

        project = await self.project_dal.get_by_id(project_id)
        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        updated_project = await self.project_dal.update(project_id, update_data)

        return ServiceResponse(
            message="Project updated successfully",
            status_code=200,
            data=updated_project.dict(),
        )
