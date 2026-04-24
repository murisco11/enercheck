from fastapi import APIRouter, Depends, status

from src.app.dependencies import (
    get_ai_demo_service,
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

router = APIRouter(prefix="/v1/ai-demo", tags=["ai-demo"])
ai_demo_service_dependency = Depends(get_ai_demo_service)
enqueue_ai_demo_job_dependency = Depends(get_enqueue_ai_demo_job_use_case)


@router.post("/respond", response_model=AIDemoResponse)
async def respond(
    payload: AIDemoRequest,
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
    use_case: EnqueueAIDemoJobUseCase = enqueue_ai_demo_job_dependency,
) -> AIDemoJobCreatedResponse:
    return await use_case.execute(payload.message)
