from fastapi import Request, Depends
from platform_common.db.dal.project_dal import ProjectDAL
from app.api.interface.abstract_handler import AbstractHandler
from platform_common.utils.service_response import ServiceResponse
from platform_common.logging.logging import get_logger
from platform_common.models.project import Project
from platform_common.db.dependencies.get_dal import get_dal
from platform_common.errors.base import BadRequestError

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
        try:
            payload = await request.json()
            payload["owner_id"] = request.state.user_id
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
