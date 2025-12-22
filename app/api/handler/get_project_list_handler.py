from fastapi import Request, Depends
from platform_common.db.dal.project_dal import ProjectDAL
from app.api.interface.abstract_handler import AbstractHandler
from platform_common.utils.service_response import ServiceResponse
from platform_common.logging.logging import get_logger
from platform_common.errors.base import BadRequestError
from platform_common.db.dependencies.get_dal import get_dal

logger = get_logger("get_project_list_handler")


class GetProjectListHandler(AbstractHandler):
    """
    Handler for retrieving a list of projects.
    """

    def __init__(self, project_dal: ProjectDAL = Depends(get_dal(ProjectDAL))):
        super().__init__()
        self.project_dal = project_dal

    async def do_process(self, request: Request) -> ServiceResponse:

        user_id = request.query_params.get("user_id")
        owner_id = request.query_params.get("owner_id")
        organization_id = request.query_params.get("organization_id")

        if user_id and organization_id:
            projects = await self.project_dal.list_for_user(
                user_id=user_id, organization_id=organization_id
            )
        elif organization_id:
            projects = await self.project_dal.get_by_org(organization_id)
        elif user_id:
            projects = await self.project_dal.get_by_owner(user_id)
        elif owner_id:
            projects = await self.project_dal.get_by_owner(owner_id)
        else:
            raise BadRequestError(
                message="user_id or organization_id must be provided",
                code="PROJECT_LIST_SCOPE_REQUIRED",
            )

        return ServiceResponse(
            message="Project list retrieved successfully",
            status_code=200,
            data=[project.dict() for project in projects],
        )
