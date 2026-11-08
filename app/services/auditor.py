from pydantic import BaseModel
from sqlalchemy import select
from app.models import CompanyEvidence, Requirement
from app.services.embedding import generate_embedding
from app.services.llm import GROQ_MODEL, groq_client, instructor_client


class AuditResult(BaseModel):
    evaluator_fear: str
    audit_score: str  # "Strong", "Partial", "Weak"
    gap_analysis: str


async def get_evidence_context(query_text: str, db, limit: int = 3) -> str:
    req_vec = generate_embedding(query_text)
    stmt = (
        select(CompanyEvidence)
        .order_by(CompanyEvidence.embedding.cosine_distance(req_vec))
        .limit(limit)
    )
    res = await db.execute(stmt)
    evidences = res.scalars().all()
    return "\n---\n".join([f"[{e.title}]: {e.content}" for e in evidences])


async def audit_requirement_against_evidence(
    requirement_text: str, is_mandatory: bool, section_ref: str | None, db
) -> AuditResult:
    evidence_context = await get_evidence_context(requirement_text, db)
    audit_prompt = (
        f"Requirement ({section_ref or 'General'}): {requirement_text}\n"
        f"Mandatory: {is_mandatory}\n\n"
        f"Company Evidence:\n{evidence_context}\n\n"
        "Analyze if evidence fulfills requirement. Score as Strong, Partial, or Weak."
    )
    return instructor_client.chat.completions.create(
        model=GROQ_MODEL,
        response_model=AuditResult,
        messages=[
            {"role": "system", "content": "You are a ruthless procurement auditor."},
            {"role": "user", "content": audit_prompt},
        ],
        temperature=0.1,
    )


async def generate_compliant_response(
    requirement_text: str,
    audit_score: str,
    evaluator_fear: str,
    word_limit: int | None,
    db,
) -> str:
    evidence_context = await get_evidence_context(requirement_text, db)
    limit_rule = f"Keep the response strictly under {word_limit} words." if word_limit else ""

    prompt = (
        f"Draft a formal tender proposal response for this requirement:\n{requirement_text}\n\n"
        f"Compliance Score: {audit_score}\n"
        f"Evaluator Fear: {evaluator_fear}\n"
        f"{limit_rule}\n\n"
        f"Company Evidence Base:\n{evidence_context}\n\n"
        "STRICT GROUND-TRUTH RULES:\n"
        "1. Never invent credentials, metrics, or facts not in evidence.\n"
        "2. Address evaluator fears proactively.\n"
        "3. If evidence is missing, insert '[ACTION REQUIRED: <task>]'."
    )
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are an elite proposal defense writer."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return res.choices[0].message.content


async def audit_single_requirement(req: Requirement, db) -> Requirement:
    audit_res = await audit_requirement_against_evidence(
        req.requirement_text, req.is_mandatory, req.section_ref, db
    )
    req.evaluator_fear = audit_res.evaluator_fear
    req.audit_score = audit_res.audit_score
    req.gap_analysis = audit_res.gap_analysis

    req.generated_response = await generate_compliant_response(
        req.requirement_text,
        req.audit_score,
        req.evaluator_fear,
        req.word_limit,
        db,
    )
    return req