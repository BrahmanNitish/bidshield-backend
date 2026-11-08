import asyncio
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ProcurementTender, TenderBid
from app.services.bid_doc_ai import extract_bid_data_from_pdf
from app.services.collusion import scan_bids_for_collusion
from app.services.rules_engine import (
    verify_mii_local_content,
    verify_temporal_validity,
    verify_turnover,
    verify_udin_format,
)
from app.services.tender_doc_ai import extract_tender_criteria_from_pdf
from fastapi.responses import Response

router = APIRouter()


@router.get("/tenders")
async def list_tenders(db: AsyncSession = Depends(get_db)):
  stmt = select(ProcurementTender).options(
      selectinload(ProcurementTender.bids)
  )
  res = await db.execute(stmt)
  return res.scalars().all()


@router.post("/tenders/upload-pdf")
async def upload_tender_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    os.makedirs("uploads/tenders", exist_ok=True)
    temp_path = f"uploads/tenders/{uuid.uuid4()}_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        criteria = await asyncio.to_thread(extract_tender_criteria_from_pdf, temp_path)

        # Check if tender_no already exists
        stmt = select(ProcurementTender).where(ProcurementTender.tender_no == criteria.tender_no)
        res = await db.execute(stmt)
        existing_tender = res.scalar_one_or_none()

        if existing_tender:
            # Update existing tender criteria
            existing_tender.title = criteria.title
            existing_tender.department = criteria.department
            existing_tender.estimated_value_cr = criteria.estimated_value_cr
            existing_tender.submission_deadline = criteria.submission_deadline
            existing_tender.min_turnover_cr = criteria.min_turnover_cr
            existing_tender.min_local_content_pct = criteria.min_local_content_pct
            await db.commit()
            await db.refresh(existing_tender)
            return existing_tender

        # Insert new tender if not exists
        tender = ProcurementTender(
            tender_no=criteria.tender_no,
            title=criteria.title,
            department=criteria.department,
            estimated_value_cr=criteria.estimated_value_cr,
            submission_deadline=criteria.submission_deadline,
            min_turnover_cr=criteria.min_turnover_cr,
            min_local_content_pct=criteria.min_local_content_pct
        )
        db.add(tender)
        await db.commit()
        await db.refresh(tender)
        return tender
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.post("/tenders/{tender_id}/bids/upload-pdf")
async def upload_bid_document(
    tender_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    tender = await db.get(ProcurementTender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    os.makedirs("uploads/bids", exist_ok=True)
    temp_path = f"uploads/bids/{uuid.uuid4()}_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        dossier, meta = await asyncio.to_thread(extract_bid_data_from_pdf, temp_path)

        # 1. Deterministic Checks
        t_audit = verify_turnover(dossier.turnover_years, tender.min_turnover_cr)
        t_audit["source_page"] = dossier.turnover_source_page

        m_audit = verify_mii_local_content(dossier.declared_local_content, tender.min_local_content_pct)
        m_audit["source_page"] = dossier.mii_source_page

        d_audit = verify_temporal_validity(dossier.cert_expiry_date, tender.submission_deadline)
        d_audit["certificate_name"] = dossier.certificate_name
        d_audit["source_page"] = dossier.cert_source_page

        u_audit = verify_udin_format(dossier.udin_number)
        u_audit["source_page"] = dossier.udin_source_page

        failures = [r for r in [t_audit, m_audit, d_audit, u_audit] if r["status"] in ["NON_COMPLIANT", "EXPIRED", "INVALID_FORMAT"]]
        
        # Base Statutory Score (25% each)
        base_score = ((4 - len(failures)) / 4) * 100.0
        verdict = "DISQUALIFIED" if len(failures) > 0 else "QUALIFIED"

        bid = TenderBid(
            tender_id=tender_id,
            bidder_name=dossier.bidder_name,
            bid_amount_cr=dossier.bid_amount_cr,
            turnover_history=dossier.turnover_years,
            declared_local_content=dossier.declared_local_content,
            udin_number=dossier.udin_number,
            cert_expiry_date=dossier.cert_expiry_date,
            registered_address=dossier.registered_address,
            pdf_author=meta.get("author", ""),
            pdf_creator=meta.get("creator", ""),
            compliance_score=round(base_score, 1),
            verdict=verdict,
            audit_breakdown={
                "turnover": t_audit,
                "make_in_india": m_audit,
                "temporal_validity": d_audit,
                "udin": u_audit,
                "filename": file.filename
            }
        )
        db.add(bid)
        await db.commit()
        await db.refresh(bid)
        return bid
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.get("/tenders/{tender_id}/evaluation")
async def get_tender_evaluation(
    tender_id: str, db: AsyncSession = Depends(get_db)
):
  stmt = (
      select(ProcurementTender)
      .where(ProcurementTender.id == tender_id)
      .options(selectinload(ProcurementTender.bids))
  )
  res = await db.execute(stmt)
  tender = res.scalar_one_or_none()
  if not tender:
    raise HTTPException(status_code=404, detail="Tender not found")

  bids_dict = [
      {
          "bid_id": b.id,
          "bidder_name": b.bidder_name,
          "bid_amount": b.bid_amount_cr,
          "registered_address": b.registered_address,
          "pdf_author": b.pdf_author,
          "pdf_creator": b.pdf_creator,
          "proposal_sample": "",
      }
      for b in tender.bids
  ]
  collusion_risks = (
      scan_bids_for_collusion(bids_dict) if len(bids_dict) > 1 else []
  )

  # Calculate specific penalty per bidder based on signal count & severity
  penalties = {}
  for c in collusion_risks:
    # 8% penalty per detected signal
    penalty = len(c["signals"]) * 8.0
    penalties[c["source"]] = penalties.get(c["source"], 0) + penalty
    penalties[c["target"]] = penalties.get(c["target"], 0) + penalty

  response_bids = []
  for b in tender.bids:
    base_score = b.compliance_score
    penalty = min(penalties.get(b.bidder_name, 0.0), 45.0)  # Max 45% cap
    final_score = max(round(base_score - penalty, 1), 10.0)

    is_collusion_risk = b.bidder_name in penalties

    response_bids.append({
        "id": b.id,
        "bidder_name": b.bidder_name,
        "bid_amount_cr": b.bid_amount_cr,
        "compliance_score": final_score,
        "collusion_penalty": penalty,
        "verdict": b.verdict,
        "is_collusion_risk": is_collusion_risk,
        "declared_local_content": b.declared_local_content,
        "udin_number": b.udin_number,
        "registered_address": b.registered_address,
        "audit_breakdown": b.audit_breakdown,
    })

  return {
      "tender": tender,
      "bids": response_bids,
      "collusion_clusters": collusion_risks,
  }

@router.get("/tenders/{tender_id}/export-report")
async def export_procurement_report(tender_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ProcurementTender).where(ProcurementTender.id == tender_id).options(selectinload(ProcurementTender.bids))
    res = await db.execute(stmt)
    tender = res.scalar_one_or_none()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    bids_dict = [
        {
            "bid_id": b.id,
            "bidder_name": b.bidder_name,
            "bid_amount": b.bid_amount_cr,
            "registered_address": b.registered_address,
            "pdf_author": b.pdf_author,
            "pdf_creator": b.pdf_creator,
            "proposal_sample": ""
        }
        for b in tender.bids
    ]
    collusion_risks = scan_bids_for_collusion(bids_dict) if len(bids_dict) > 1 else []

    # Audit Report Text formatting
    report = []
    report.append("=" * 80)
    report.append("GOVERNMENT PROCUREMENT AUDIT & STATUTORY COMPLIANCE REPORT")
    report.append("=" * 80)
    report.append(f"Tender Reference   : {tender.tender_no}")
    report.append(f"Project Title      : {tender.title}")
    report.append(f"Procuring Dept     : {tender.department}")
    report.append(f"Submission Deadline: {tender.submission_deadline}")
    report.append(f"Baseline Thresholds: Min Turnover ₹{tender.min_turnover_cr} Cr | MII Local Content ≥ {tender.min_local_content_pct}%")
    report.append("-" * 80)
    report.append("")

    report.append("SECTION 1: COLLUSION & COVER BIDDING SCREENING RADAR")
    report.append("-" * 50)
    if collusion_risks:
        for c in collusion_risks:
            report.append(f"ALERT: Potential relationship cluster detected between '{c['source']}' and '{c['target']}'")
            for sig in c["signals"]:
                report.append(f"  • {sig}")
    else:
        report.append("No suspicious inter-bidder relationships or metadata overlaps detected.")
    report.append("")

    report.append("SECTION 2: BIDDER EVALUATION MATRIX")
    report.append("-" * 80)
    for b in tender.bids:
        report.append(f"Bidder Name     : {b.bidder_name}")
        report.append(f"Quoted Price    : ₹{b.bid_amount_cr} Cr")
        report.append(f"Final Verdict   : {b.verdict}")
        report.append(f"Compliance Score: {b.compliance_score}%")
        report.append(f"Turnover Audit  : {b.audit_breakdown.get('turnover', {}).get('status')} ({b.audit_breakdown.get('turnover', {}).get('formula', '')})")
        report.append(f"MII Content     : {b.declared_local_content}% ({b.audit_breakdown.get('make_in_india', {}).get('status')})")
        report.append(f"Temporal Check  : {b.audit_breakdown.get('temporal_validity', {}).get('status')} (Expiry: {b.cert_expiry_date})")
        report.append(f"UDIN Format     : {b.audit_breakdown.get('udin', {}).get('status')} ({b.udin_number})")
        report.append("-" * 40)

    report_content = "\n".join(report)
    
    return Response(
        content=report_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=Procurement_Audit_{tender.tender_no.replace('/', '_')}.txt"
        }
    )