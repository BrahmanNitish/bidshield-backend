import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


# --- RAG & Tender Proposal Models ---
class CompanyEvidence(Base):
  __tablename__ = "company_evidence"

  id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
  title = Column(String, nullable=False)
  category = Column(String, nullable=False)
  content = Column(Text, nullable=False)
  embedding = Column(Vector(384))
  created_at = Column(DateTime, default=datetime.utcnow)


class Tender(Base):
  __tablename__ = "tenders"

  id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
  title = Column(String, nullable=False)
  file_path = Column(String, nullable=True)
  status = Column(String, default="PENDING")
  created_at = Column(DateTime, default=datetime.utcnow)

  requirements = relationship(
      "Requirement", back_populates="tender", cascade="all, delete-orphan"
  )


class Requirement(Base):
  __tablename__ = "requirements"

  id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
  tender_id = Column(String, ForeignKey("tenders.id"), nullable=False)
  section_ref = Column(String, nullable=True)
  requirement_text = Column(Text, nullable=False)
  is_mandatory = Column(Boolean, default=False)
  word_limit = Column(Integer, nullable=True)
  weight = Column(Float, nullable=True)
  evaluator_fear = Column(Text, nullable=True)
  audit_score = Column(String, nullable=True)
  gap_analysis = Column(Text, nullable=True)
  generated_response = Column(Text, nullable=True)

  tender = relationship("Tender", back_populates="requirements")


class ProcurementTender(Base):
  __tablename__ = "procurement_tenders"

  id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
  tender_no = Column(String, unique=True, index=True, nullable=False)
  title = Column(String, nullable=False)
  department = Column(String, default="General Procurement")
  estimated_value_cr = Column(Float, nullable=False)
  submission_deadline = Column(String, nullable=False)  

  min_turnover_cr = Column(Float, nullable=False, default=10.0)
  min_local_content_pct = Column(Float, nullable=False, default=50.0)

  created_at = Column(DateTime, default=datetime.utcnow)
  bids = relationship(
      "TenderBid", back_populates="tender", cascade="all, delete-orphan"
  )


class TenderBid(Base):
  __tablename__ = "tender_bids"

  id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
  tender_id = Column(
      String, ForeignKey("procurement_tenders.id"), nullable=False
  )
  bidder_name = Column(String, nullable=False)
  bid_amount_cr = Column(Float, nullable=False)

  turnover_history = Column(JSON, default=list)
  declared_local_content = Column(Float, nullable=False)
  udin_number = Column(String, nullable=False)
  cert_expiry_date = Column(String, nullable=False)  

  registered_address = Column(String, nullable=True)
  pdf_author = Column(String, nullable=True)
  pdf_creator = Column(String, nullable=True)

  compliance_score = Column(Float, default=0.0)
  verdict = Column(String, default="PENDING")
  audit_breakdown = Column(JSON, default=dict)

  created_at = Column(DateTime, default=datetime.utcnow)
  tender = relationship("ProcurementTender", back_populates="bids")