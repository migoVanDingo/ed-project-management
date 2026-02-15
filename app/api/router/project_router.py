from fastapi import APIRouter, Depends, Request
from platform_common.logging.logging import get_logger
from platform_common.utils.service_response import ServiceResponse
from platform_common.middleware.auth_middleware import authenticate_request

from app.api.handler.get_project_list_handler import GetProjectListHandler
from app.api.handler.get_project_handler import GetProjectHandler
from app.api.handler.create_project_handler import CreateProjectHandler
from app.api.handler.update_project_handler import UpdateProjectHandler
from app.api.handler.delete_project_handler import DeleteProjectHandler

router = APIRouter(dependencies=[Depends(authenticate_request)])
logger = get_logger("project")


@router.get("/read/list")
async def get_project_list(
    request: Request, handler: GetProjectListHandler = Depends(GetProjectListHandler)
) -> ServiceResponse:
    return await handler.do_process(request)


@router.get("/read")
async def get_project(
    request: Request, handler: GetProjectHandler = Depends(GetProjectHandler)
) -> ServiceResponse:
    return await handler.do_process(request)


@router.post("/create")
async def create_project(
    request: Request, handler: CreateProjectHandler = Depends(CreateProjectHandler)
) -> ServiceResponse:
    return await handler.do_process(request)


@router.put("/update/{project_id}")
async def update_project(
    project_id: str,
    request: Request,
    handler: UpdateProjectHandler = Depends(UpdateProjectHandler),
) -> ServiceResponse:
    return await handler.do_process(request, project_id)


@router.delete("/delete/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    handler: DeleteProjectHandler = Depends(DeleteProjectHandler),
) -> ServiceResponse:
    return await handler.do_process(request, project_id)
