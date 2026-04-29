from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.app.dependencies import get_current_user, get_user_service
from src.modules.users.application.use_cases import AuthenticatedUser, UserService
from src.modules.users.domain.models import AuthTokenResponse, LoginRequest

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=AuthTokenResponse)
def login(
    payload: LoginRequest,
    service: Annotated[UserService, Depends(get_user_service)],
) -> AuthTokenResponse:
    try:
        return service.login(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me")
def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> dict[str, int | str]:
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
    }
