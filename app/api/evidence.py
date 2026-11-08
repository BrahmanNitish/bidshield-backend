from fastapi import APIRouter, Depends, HTTPException
from pgvector.sqlalchemy import Vector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CompanyEvidence
from app.schemas import EvidenceCreate, EvidenceResponse
from app.services.embedding import generate_embedding
import shutil
import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import CompanyEvidence
from app.services.evidence_loader import process_policy_pdf

router = APIRouter(prefix="/evidence", tags=["Company Evidence"])


@router.post("/", response_model=EvidenceResponse)
async def create_evidence(
    payload: EvidenceCreate, db: AsyncSession = Depends(get_db)
):
    # Text ka embedding generate karo
    vector = generate_embedding(payload.content)

    evidence = CompanyEvidence(
        title=payload.title,
        category=payload.category,
        content=payload.content,
        embedding=vector,
    )
    db.add(evidence)
    await db.commit()
    await db.refresh(evidence)
    return evidence


@router.get("/", response_model=list[EvidenceResponse])
async def list_evidence(
    limit: int = 50, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(CompanyEvidence)
        .order_by(CompanyEvidence.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/search", response_model=list[EvidenceResponse])
async def search_evidence(
    query: str, limit: int = 3, db: AsyncSession = Depends(get_db)
):
    query_vector = generate_embedding(query)

    # pgvector cosine distance search (<=> operator)
    stmt = (
        select(CompanyEvidence)
        .order_by(CompanyEvidence.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
@router.post("/upload-pdf")
async def upload_evidence_pdf(
    title: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    os.makedirs("uploads/evidence", exist_ok=True)
    temp_path = f"uploads/evidence/{uuid.uuid4()}_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Offload CPU-bound chunking and embedding to thread
        records = await asyncio.to_thread(
            process_policy_pdf, temp_path, category, title
        )

        for rec in records:
            item = CompanyEvidence(
                title=rec["title"],
                category=rec["category"],
                content=rec["content"],
                embedding=rec["embedding"]
            )
            db.add(item)

        await db.commit()
        return {
            "status": "success",
            "message": f"Successfully parsed and indexed {len(records)} knowledge chunks.",
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)