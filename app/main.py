from fastapi import FastAPI

from app.api.controller.health_check import router as health_router
from app.api.router.project_router import router as project_router
from platform_common.middleware.request_id_middleware import RequestIDMiddleware
from platform_common.middleware.auth_middleware import AuthMiddleware
from fastapi.middleware.cors import CORSMiddleware
from platform_common.exception_handling.handlers import add_exception_handlers
from strawberry.fastapi import GraphQLRouter

app = FastAPI(title="Core Service")
origins = [
    "http://localhost:5173",  # common React dev port
    "http://127.0.0.1:5173",
    # "https://my-production-domain.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # <-- your list here
    allow_credentials=True,  # <-- whether to expose cookies/auth headers
    allow_methods=["*"],  # <-- GET, POST, PUT, DELETE, etc
    allow_headers=["*"],  # <-- allow all headers (Authorization, Content-Type…)
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)
add_exception_handlers(app)

# REST endpoints
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(project_router, prefix="/api/project", tags=["Project"])
