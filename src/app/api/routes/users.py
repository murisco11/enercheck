from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.app.dependencies import get_user_service
from src.modules.users.application.use_cases import UserService
from src.modules.users.domain.models import (
    UserCreate,
    UserListResponse,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/v1/users", tags=["users"])
user_service_dependency = Depends(get_user_service)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,    
    service: UserService = user_service_dependency,
) -> UserRead:
    try:
        return service.create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=UserListResponse)
def list_users(service: UserService = user_service_dependency) -> UserListResponse:
    return UserListResponse(items=service.list_users())


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, service: UserService = user_service_dependency) -> UserRead:
    try:
        return service.get_user(user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    service: UserService = user_service_dependency,
) -> UserRead:
    try:
        return service.update_user(user_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, service: UserService = user_service_dependency) -> Response:
    try:
        service.delete_user(user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
