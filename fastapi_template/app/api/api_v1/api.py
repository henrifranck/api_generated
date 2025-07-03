from fastapi import APIRouter

from app.api.api_v1.endpoints import (  # drive_action,
    roles,
    users,
    login
)

api_router = APIRouter()
# api_router.include_router(socket.router, prefix="/socket", tags=["socket"])
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
# api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
