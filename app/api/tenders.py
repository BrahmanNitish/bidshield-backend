import asyncio
import os
import shutil
import traceback
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models import Tender, Requirement
from app.schemas import TenderResponse, TenderStatusResponse
from app.services.parser import extract_text_from_pdf, extract_requirements_from_text
from app.services.embedding import generate_embedding
from app.services.auditor import (
    audit_requirement_against_evidence,
    generate_compliant_response,
)
from app.models import CompanyEvidence
from fastapi.responses import StreamingResponse
from app.services.exporter import build_bid_proposal_docx
from app.services.auditor import audit_single_requirement
from app.models import Requirement
from app.services.auditor import audit_single_requirement

router = APIRouter(prefix="/tenders", tags=["Tenders"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def process_tender_background(tender_id: str, file_path: str):
    async with AsyncSessionLocal() as db:
        try:
            # 1. Read PDF text
            text = extract_text_from_pdf(file_path)

            # 2. Extract with LLM
            extracted = extract_requirements_from_text(text)

            # 3. Store extracted requirements
            for item in extracted:
                req = Requirement(
                    tender_id=tender_id,
                    section_ref=item.section_ref,
                    requirement_text=item.requirement_text,
                    is_mandatory=item.is_mandatory,
                    word_limit=item.word_limit,
                    weight=item.weight,
                    evaluator_fear=item.evaluator_fear,
                )
                db.add(req)

            # 4. Update tender status
            stmt = select(Tender).where(Tender.id == tender_id)
            res = await db.execute(stmt)
            tender = res.scalar_one_or_none()
            if tender:
                tender.status = "PARSED"
            
            await db.commit()
        except Exception as e:
            print(f"[-] ERROR processing tender {tender_id}: {e}")
            traceback.print_exc()
            try:
                async with AsyncSessionLocal() as db:
                    stmt = select(Tender).where(Tender.id == tender_id)
                    res = await db.execute(stmt)
                    tender = res.scalar_one_or_none()
                    if tender:
                        # Safe truncation to fit VARCHAR(50)
                        err_msg = str(e).replace("\n", " ")[:40]
                        tender.status = f"FAILED: {err_msg}"
                        await db.commit()
            except Exception as db_err:
                print(f"[-] Critical DB error: {db_err}")

@router.post("/upload", response_model=TenderStatusResponse)
async def upload_tender(
    title: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    tender = Tender(
        id=file_id,
        title=title,
        file_path=file_path,
        status="PROCESSING",
    )
    db.add(tender)
    await db.commit()

    # Trigger background parsing
    background_tasks.add_task(process_tender_background, file_id, file_path)

    return TenderStatusResponse(id=tender.id, title=tender.title, status=tender.status)


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender_details(tender_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Tender)
        .where(Tender.id == tender_id)
        .options(selectinload(Tender.requirements))
    )
    res = await db.execute(stmt)
    tender = res.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found.")
    return tender



@router.post("/{tender_id}/audit")
async def audit_tender_requirements(
    tender_id: str, db: AsyncSession = Depends(get_db)
):
    # 1. Fetch requirements
    stmt = select(Requirement).where(Requirement.tender_id == tender_id)
    res = await db.execute(stmt)
    requirements = res.scalars().all()

    if not requirements:
        raise HTTPException(
            status_code=404,
            detail="No requirements found for this tender. Has it finished parsing?",
        )

    for req in requirements:
        # 2. Vector search: Find top 3 relevant evidence pieces
        query_vector = generate_embedding(req.requirement_text)
        ev_stmt = (
            select(CompanyEvidence)
            .order_by(CompanyEvidence.embedding.cosine_distance(query_vector))
            .limit(3)
        )
        ev_res = await db.execute(ev_stmt)
        matched_evidences = ev_res.scalars().all()

        evidence_snippets = [
            f"[{e.category}] {e.title}: {e.content}"
            for e in matched_evidences
        ]

        # 3. Audit scoring
        audit_res = await asyncio.to_thread(
            audit_requirement_against_evidence,
            req.requirement_text,
            evidence_snippets,
        )

        req.evaluator_fear = audit_res.evaluator_fear
        req.audit_score = audit_res.audit_score
        req.gap_analysis = audit_res.gap_analysis

    # 4. Update tender status
    t_stmt = select(Tender).where(Tender.id == tender_id)
    t_res = await db.execute(t_stmt)
    tender = t_res.scalar_one_or_none()
    if tender:
        tender.status = "AUDITED"

    await db.commit()
    return {
        "status": "success",
        "message": f"Audited {len(requirements)} requirements.",
    }


@router.post("/{tender_id}/generate-responses")
async def generate_tender_responses(
    tender_id: str, db: AsyncSession = Depends(get_db)
):
    stmt = select(Requirement).where(Requirement.tender_id == tender_id)
    res = await db.execute(stmt)
    requirements = res.scalars().all()

    if not requirements:
        raise HTTPException(status_code=404, detail="Requirements not found.")

    for req in requirements:
        # Fetch relevant evidence
        query_vector = generate_embedding(req.requirement_text)
        ev_stmt = (
            select(CompanyEvidence)
            .order_by(CompanyEvidence.embedding.cosine_distance(query_vector))
            .limit(3)
        )
        ev_res = await db.execute(ev_stmt)
        matched_evidences = ev_res.scalars().all()

        evidence_snippets = [
            f"[{e.category}] {e.title}: {e.content}"
            for e in matched_evidences
        ]

        # Generate compliant draft
        draft = await asyncio.to_thread(
            generate_compliant_response,
            req.requirement_text,
            req.evaluator_fear or "Non-compliance risk",
            req.word_limit,
            evidence_snippets,
        )
        req.generated_response = draft

    await db.commit()
    return {
        "status": "success",
        "message": f"Generated responses for {len(requirements)} clauses.",
    }
@router.get("/{tender_id}/export")
async def export_tender_docx(
    tender_id: str, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Tender)
        .where(Tender.id == tender_id)
        .options(selectinload(Tender.requirements))
    )
    res = await db.execute(stmt)
    tender = res.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found.")

    stream = await asyncio.to_thread(
        build_bid_proposal_docx, tender.title, tender.requirements
    )

    filename = f"BidShield_{tender.title.replace(' ', '_')}.docx"

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
@router.get("/{tender_id}/analytics")
async def get_tender_analytics(
    tender_id: str, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Tender)
        .where(Tender.id == tender_id)
        .options(selectinload(Tender.requirements))
    )
    res = await db.execute(stmt)
    tender = res.scalar_one_or_none()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found.")

    reqs = tender.requirements
    total_clauses = len(reqs)

    if total_clauses == 0:
        return {
            "tender_id": tender_id,
            "status": tender.status,
            "message": "No requirements extracted yet.",
        }

    strong_count = sum(1 for r in reqs if r.audit_score == "Strong")
    partial_count = sum(1 for r in reqs if r.audit_score == "Partial")
    weak_count = sum(1 for r in reqs if r.audit_score == "Weak")

    # Critical risk: mandatory clause with weak/missing evidence
    critical_disqualification_risks = [
        {
            "clause_id": r.id,
            "section_ref": r.section_ref,
            "requirement_text": r.requirement_text,
            "evaluator_fear": r.evaluator_fear,
            "gap": r.gap_analysis,
        }
        for r in reqs
        if r.is_mandatory and r.audit_score in ["Weak", None]
    ]

    # Readiness percentage calculation
    # Strong = 100%, Partial = 50%, Weak = 0%
    readiness_score = round(
        ((strong_count * 1.0 + partial_count * 0.5) / total_clauses) * 100, 2
    )

    verdict = (
        "HIGH_RISK_DISQUALIFICATION"
        if len(critical_disqualification_risks) > 0
        else "BID_READY"
        if readiness_score >= 80
        else "NEEDS_EVIDENCE_REVISION"
    )

    return {
        "tender_id": tender.id,
        "tender_title": tender.title,
        "status": tender.status,
        "verdict": verdict,
        "readiness_score_pct": readiness_score,
        "summary": {
            "total_clauses": total_clauses,
            "strong": strong_count,
            "partial": partial_count,
            "weak": weak_count,
        },
        "critical_disqualification_risks": critical_disqualification_risks,
    }
@router.post("/{tender_id}/clauses/{clause_id}/re-audit")
async def reaudit_single_clause(
    tender_id: str, clause_id: str, db: AsyncSession = Depends(get_db)
):
  stmt = select(Requirement).where(
      Requirement.id == clause_id, Requirement.tender_id == tender_id
  )
  res = await db.execute(stmt)
  req = res.scalar_one_or_none()

  if not req:
    raise HTTPException(status_code=404, detail="Clause requirement not found.")

  updated_req = await audit_single_requirement(req, db)
  await db.commit()
  await db.refresh(updated_req)

  return {
      "status": "success",
      "clause_id": updated_req.id,
      "section_ref": updated_req.section_ref,
      "new_score": updated_req.audit_score,
      "gap_analysis": updated_req.gap_analysis,
      "generated_response": updated_req.generated_response,
  }