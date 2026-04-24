from pydantic import BaseModel, Field


class AIDemoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AIDemoResponse(BaseModel):
    provider: str
    output: str


class AIDemoJobCreatedResponse(BaseModel):
    event_name: str
    job_id: str
    status: str
