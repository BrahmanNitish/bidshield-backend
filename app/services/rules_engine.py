from datetime import datetime


def verify_turnover(
    turnover_list: list[float], required_turnover: float
) -> dict:
  avg_turnover = sum(turnover_list) / len(turnover_list) if turnover_list else 0
  is_compliant = avg_turnover >= required_turnover
  return {
      "metric": "Average Annual Turnover",
      "required": required_turnover,
      "found": round(avg_turnover, 2),
      "difference": round(avg_turnover - required_turnover, 2),
      "status": "COMPLIANT" if is_compliant else "NON_COMPLIANT",
      "risk": "LOW" if is_compliant else "HIGH",
      "formula": (
          f"({' + '.join([str(x) for x in turnover_list])}) /"
          f" {len(turnover_list)} = ₹{round(avg_turnover, 2)} Cr"
      ),
  }


def verify_mii_local_content(
    declared_percentage: float, required_percentage: float = 50.0
) -> dict:
  is_compliant = declared_percentage >= required_percentage
  return {
      "metric": "Make in India (Class-I Local Supplier)",
      "required": f"{required_percentage}%",
      "found": f"{declared_percentage}%",
      "status": "COMPLIANT" if is_compliant else "NON_COMPLIANT",
      "risk": "LOW" if is_compliant else "CRITICAL",
  }


def verify_temporal_validity(
    cert_expiry_date: str, submission_date: str
) -> dict:
  expiry = datetime.strptime(cert_expiry_date, "%Y-%m-%d")
  sub = datetime.strptime(submission_date, "%Y-%m-%d")
  is_valid = expiry >= sub
  return {
      "metric": "Certificate Temporal Validity at Tender Submission",
      "expiry_date": cert_expiry_date,
      "submission_date": submission_date,
      "status": "VALID" if is_valid else "EXPIRED",
      "risk": "LOW" if is_valid else "HIGH",
  }


def verify_udin_format(udin: str) -> dict:
  is_valid = len(udin) == 18 and udin.isalnum()
  return {
      "metric": "ICAI UDIN Format Verification",
      "udin": udin,
      "status": "VERIFIED" if is_valid else "INVALID_FORMAT",
      "risk": "LOW" if is_valid else "CRITICAL",
  }