import pypdf
from pydantic import BaseModel, Field
from app.services.llm import instructor_client, GROQ_MODEL

class ExtractedTenderCriteria(BaseModel):
    tender_no: str = Field(description="Official tender or RFP reference number")
    title: str = Field(description="Concise tender project title")
    department: str = Field(description="Procuring authority or ministry name")
    estimated_value_cr: float = Field(description="Estimated value in Crores, default 10.0 if not specified")
    submission_deadline: str = Field(description="Deadline date in YYYY-MM-DD format")
    min_turnover_cr: float = Field(description="Minimum average annual turnover required in INR Crores")
    min_local_content_pct: float = Field(description="Minimum local content percentage required under Make in India policy")
    requires_udin: bool = Field(default=True, description="Whether CA certificates require UDIN verification")

def extract_tender_criteria_from_pdf(pdf_path: str) -> ExtractedTenderCriteria:
    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages[:8]:
        full_text += (page.extract_text() or "") + "\n"

    prompt = f"""
    You are a Senior Government Procurement Auditor.
    Extract the statutory qualification rules and baseline tender metadata from this Tender Document text:

    {full_text[:12000]}
    """

    return instructor_client.chat.completions.create(
        model=GROQ_MODEL,
        response_model=ExtractedTenderCriteria,
        messages=[
            {"role": "system", "content": "Extract structured procurement rules from tender documents strictly adhering to the schema."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )