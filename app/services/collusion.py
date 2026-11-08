from difflib import SequenceMatcher


def scan_bids_for_collusion(bids: list[dict]) -> list[dict]:
  signals = []
  n = len(bids)

  for i in range(n):
    for j in range(i + 1, n):
      b1, b2 = bids[i], bids[j]
      detected = []

      if (
          b1.get("pdf_creator")
          and b1.get("pdf_creator") == b2.get("pdf_creator")
          and b1.get("pdf_author") == b2.get("pdf_author")
      ):
        detected.append(
            f"Identical PDF Author & System Metadata: {b1.get('pdf_author')}"
        )

      if (
          b1.get("registered_address")
          and b1.get("registered_address").lower()
          == b2.get("registered_address").lower()
      ):
        detected.append("Shared Physical Registered Address / Facility")

      p1, p2 = b1.get("bid_amount", 0), b2.get("bid_amount", 0)
      if p1 > 0 and p2 > 0:
        variance = abs(p1 - p2) / min(p1, p2)
        if variance < 0.005: 
          detected.append(
              f"Suspicious Close Bid Pricing: ₹{p1} Cr vs ₹{p2} Cr (Variance"
              f" {round(variance*100, 2)}%)"
          )

      t1, t2 = b1.get("proposal_sample", ""), b2.get("proposal_sample", "")
      if t1 and t2:
        ratio = SequenceMatcher(None, t1, t2).ratio()
        if ratio > 0.85:
          detected.append(
              f"Document Formatting & Typo Fingerprint Overlap ({round(ratio*100, 1)}%)"
          )

      if detected:
        signals.append({
            "source": b1["bidder_name"],
            "target": b2["bidder_name"],
            "signals": detected,
            "risk_level": "HIGH" if len(detected) >= 2 else "MEDIUM",
        })

  return signals