from datetime import datetime
from pydantic import BaseModel, Field


class EvidenceCreate(BaseModel):
    title: str = Field(..., max_length=255)
    category: str = Field(
        ...,
        description="e.g., 'ISO Certification', 'Case Study', 'Security Policy'",
    )
    content: str = Field(..., min_length=10)


class EvidenceResponse(BaseModel):
    id: str
    title: str
    category: str
    content: str
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class RequirementResponse(BaseModel):
    id: str
    section_ref: str | None
    requirement_text: str
    is_mandatory: bool
    word_limit: int | None
    weight: float | None
    evaluator_fear: str | None
    audit_score: str | None
    gap_analysis: str | None
    generated_response: str | None

    class Config:
        from_attributes = True


class TenderResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    requirements: list[RequirementResponse] = []

    class Config:
        from_attributes = True


class TenderStatusResponse(BaseModel):
    id: str
    title: str
    status: str