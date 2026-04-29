from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.app.dependencies import (
    get_ai_demo_service,
    get_current_user,
    get_enqueue_ai_demo_job_use_case,
)
from src.modules.ai_demo.application.use_cases import (
    AIDemoService,
    EnqueueAIDemoJobUseCase,
)
from src.modules.ai_demo.domain.models import (
    AIDemoJobCreatedResponse,
    AIDemoRequest,
    AIDemoResponse,
)
from src.modules.users.application.use_cases import AuthenticatedUser

router = APIRouter(prefix="/v1/ai-demo", tags=["ai-demo"])
ai_demo_service_dependency = Depends(get_ai_demo_service)
enqueue_ai_demo_job_dependency = Depends(get_enqueue_ai_demo_job_use_case)
current_user_dependency = Depends(get_current_user)

@router.post("/respond", response_model=AIDemoResponse)
async def respond(
    payload: AIDemoRequest,
    _: Annotated[AuthenticatedUser, current_user_dependency],
    service: AIDemoService = ai_demo_service_dependency,
) -> AIDemoResponse:
    return await service.respond(payload.message)


@router.post(
    "/jobs",
    response_model=AIDemoJobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_job(
    payload: AIDemoRequest,
    _: Annotated[AuthenticatedUser, current_user_dependency],
    use_case: EnqueueAIDemoJobUseCase = enqueue_ai_demo_job_dependency,
) -> AIDemoJobCreatedResponse:
    return await use_case.execute(payload.message)
