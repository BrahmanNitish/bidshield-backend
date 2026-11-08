from pydantic import BaseModel, Field
import pypdf
from app.services.llm import instructor_client, GROQ_MODEL

class ExtractedBidDossier(BaseModel):
    bidder_name: str = Field(description="Legal entity name of the bidder")
    bid_amount_cr: float = Field(description="Commercial price quoted in Crores")
    turnover_years: list[float] = Field(description="Turnovers of last 3 financial years in INR Crores")
    turnover_source_page: int = Field(default=1, description="Page number where turnover table was found")
    
    declared_local_content: float = Field(description="Local content percentage declared under Make in India")
    mii_source_page: int = Field(default=1, description="Page number where MII declaration was found")
    
    udin_number: str = Field(description="18-character ICAI UDIN number found on CA certificate")
    udin_source_page: int = Field(default=1, description="Page number where UDIN was found")
    
    certificate_name: str = Field(default="Statutory Compliance Certificate", description="Name of the statutory certificate extracted")
    cert_expiry_date: str = Field(description="Statutory certificate expiry date in YYYY-MM-DD")
    cert_source_page: int = Field(default=1, description="Page number where the expired/valid certificate was found")
    
    registered_address: str = Field(description="Official corporate address")

def extract_bid_data_from_pdf(pdf_path: str) -> tuple[ExtractedBidDossier, dict]:
    reader = pypdf.PdfReader(pdf_path)
    full_text_with_pages = ""
    for idx, page in enumerate(reader.pages[:10]):
        full_text_with_pages += f"\n--- [PAGE {idx + 1}] ---\n" + (page.extract_text() or "")

    raw_meta = reader.metadata or {}
    pdf_meta = {
        "author": str(raw_meta.get("/Author", "Unknown")),
        "creator": str(raw_meta.get("/Creator", "Unknown")),
        "producer": str(raw_meta.get("/Producer", "Unknown"))
    }

    prompt = f"""
    Extract bidder compliance parameters, along with the EXACT PAGE NUMBERS where each claim is found:
    {full_text_with_pages[:14000]}
    """

    extracted = instructor_client.chat.completions.create(
        model=GROQ_MODEL,
        response_model=ExtractedBidDossier,
        messages=[
            {"role": "system", "content": "Extract bidder parameters and pinpoint source page numbers from the provided text markers."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    return extracted, pdf_meta