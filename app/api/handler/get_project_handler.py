from fastapi import Request, Depends
from platform_common.db.dal.project_dal import ProjectDAL
from app.api.interface.abstract_handler import AbstractHandler
from platform_common.utils.service_response import ServiceResponse
from platform_common.logging.logging import get_logger
from platform_common.errors.base import NotFoundError, BadRequestError
from platform_common.db.dependencies.get_dal import get_dal

logger = get_logger("get_project_handler")


class GetProjectHandler(AbstractHandler):
    """
    Handler for retrieving a project by ID.
    """

    def __init__(self, project_dal: ProjectDAL = Depends(get_dal(ProjectDAL))):
        super().__init__()
        self.project_dal = project_dal

    async def do_process(self, request: Request) -> ServiceResponse:

        project_id = request.query_params.get("project_id")
        id = request.query_params.get("id")

        if not project_id and not id:
            raise BadRequestError(
                message="Either project_id or id must be provided",
                code="PROJECT_ID_REQUIRED",
            )

        project = await self.project_dal.get_by_id(project_id or id)

        if not project:
            raise NotFoundError(message="Project not found", code="PROJECT_NOT_FOUND")

        return ServiceResponse(
            message="Project retrieved successfully",
            status_code=200,
            data=project.dict(),
        )
