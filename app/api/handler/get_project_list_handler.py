from fastapi import Request, Depends
from platform_common.db.dal.project_dal import ProjectDAL
from app.api.interface.abstract_handler import AbstractHandler
from platform_common.utils.service_response import ServiceResponse
from platform_common.logging.logging import get_logger
from platform_common.errors.base import AuthError
from platform_common.db.dependencies.get_dal import get_dal
from platform_common.auth.permissions import PROJECT_VIEW, RESOURCE_TYPE_PROJECT, can

logger = get_logger("get_project_list_handler")


class GetProjectListHandler(AbstractHandler):
    """
    Handler for retrieving a list of projects.
    """

    def __init__(self, project_dal: ProjectDAL = Depends(get_dal(ProjectDAL))):
        super().__init__()
        self.project_dal = project_dal

    async def do_process(self, request: Request) -> ServiceResponse:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise AuthError("Not authenticated")

        organization_id = request.query_params.get("organization_id")

        if organization_id:
            projects = await self.project_dal.list_for_user(
                user_id=user_id, organization_id=organization_id
            )
        else:
            projects = await self.project_dal.get_by_owner(user_id)

        authorized_projects = []
        for project in projects:
            allowed = await can(
                session=self.project_dal.session,
                user_id=user_id,
                perm_bit=PROJECT_VIEW,
                resource_type=RESOURCE_TYPE_PROJECT,
                resource_obj=project,
            )
            if allowed:
                authorized_projects.append(project)

        return ServiceResponse(
            message="Project list retrieved successfully",
            status_code=200,
            data=[project.dict() for project in authorized_projects],
        )
