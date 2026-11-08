import pypdf
from pydantic import BaseModel, Field
from app.services.llm import instructor_client, GROQ_MODEL


class ExtractedRequirementSchema(BaseModel):
    section_ref: str | None = Field(default=None)
    requirement_text: str = Field(description="The exact requirement text.")
    is_mandatory: bool = Field(default=False)
    word_limit: int | None = Field(default=None)
    weight: float | None = Field(default=None)
    evaluator_fear: str | None = Field(default=None)


class TenderExtractionBatch(BaseModel):
    requirements: list[ExtractedRequirementSchema]


def extract_text_from_pdf(file_path: str) -> str:
    reader = pypdf.PdfReader(file_path)
    full_text = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            full_text.append(txt)
    return "\n\n".join(full_text)


def extract_requirements_from_text(text_chunk: str) -> list[ExtractedRequirementSchema]:
    prompt = (
        "Extract all bidder requirements, scored criteria, word limits, and risks from this tender:\n\n"
        f"{text_chunk[:6000]}"
    )

    response = instructor_client.chat.completions.create(
        model=GROQ_MODEL,
        response_model=TenderExtractionBatch,
        messages=[
            {
                "role": "system",
                "content": "You extract tender compliance requirements into valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return response.requirements