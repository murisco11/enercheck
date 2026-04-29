from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.app.dependencies import get_current_user, get_user_service, require_admin
from src.modules.users.application.use_cases import AuthenticatedUser, UserService
from src.modules.users.domain.models import UserCreate, UserListResponse, UserRead, UserUpdate

router = APIRouter(prefix="/v1/users", tags=["users"])
user_service_dependency = Depends(get_user_service)
current_user_dependency = Depends(get_current_user)
admin_dependency = Depends(require_admin)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    service: Annotated[UserService, user_service_dependency],
) -> UserRead:
    try:
        return service.create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=UserListResponse)
def list_users(
    _: Annotated[AuthenticatedUser, admin_dependency],
    service: Annotated[UserService, user_service_dependency],
) -> UserListResponse:
    return UserListResponse(items=service.list_users())


@router.get("/me", response_model=UserRead)
def get_my_user(
    current_user: Annotated[AuthenticatedUser, current_user_dependency],
    service: Annotated[UserService, user_service_dependency],
) -> UserRead:
    return service.get_user(current_user.id)


@router.get("/{id}", response_model=UserRead)
def get_user(
    id: int,
    current_user: Annotated[AuthenticatedUser, current_user_dependency],
    service: Annotated[UserService, user_service_dependency],
) -> UserRead:
    if current_user.role != "admin" and current_user.id != id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao pode acessar outro usuario.",
        )

    try:
        return service.get_user(id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{id}", response_model=UserRead)
def update_user(
    id: int,
    payload: UserUpdate,
    current_user: Annotated[AuthenticatedUser, current_user_dependency],
    service: Annotated[UserService, user_service_dependency],
) -> UserRead:
    try:
        return service.update_user(id, payload, actor=current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    id: int,
    current_user: Annotated[AuthenticatedUser, current_user_dependency],
    service: Annotated[UserService, user_service_dependency],
) -> Response:
    try:
        service.delete_user(id, actor=current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
