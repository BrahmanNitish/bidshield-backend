import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

os.makedirs("demo_documents", exist_ok=True)

def create_tender_rfp():
    path = "demo_documents/TENDER_RFP_CPCL_2026_001.pdf"
    c = canvas.Canvas(path, pagesize=letter)
    
    # Page 1: Cover Page
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, 720, "CHENNAI PETROLEUM CORPORATION LIMITED (CPCL)")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 690, "GLOBAL COMPETITIVE BIDDING - TENDER INVITATION")
    c.setLineWidth(1)
    c.line(60, 680, 550, 680)
    
    c.setFont("Helvetica", 10)
    c.drawString(60, 650, "Tender Reference Number: CPCL/2026/001")
    c.drawString(60, 630, "Project Title: Industrial Heavy Equipment & Pumping Machinery Supply")
    c.drawString(60, 610, "Procuring Authority: Chennai Petroleum Corporation Limited")
    c.drawString(60, 590, "Estimated Contract Value: INR 25.00 Crores")
    c.drawString(60, 570, "Tender Submission Deadline: 2026-10-15")
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 530, "SECTION II: STATUTORY MINIMUM ELIGIBILITY CRITERIA")
    c.setFont("Helvetica", 10)
    c.drawString(60, 505, "1. Commercial Turnover: Bidder must possess an average annual financial turnover")
    c.drawString(75, 490, "of minimum INR 10.00 Crores over the preceding three audited financial years.")
    c.drawString(60, 465, "2. Make in India (MII) Preference: Strictly Class-I Local Suppliers having minimum")
    c.drawString(75, 450, "Local Content of at least 50% are eligible for preferential evaluation.")
    c.drawString(60, 425, "3. CA Certification & UDIN Mandate: All audited figures must be certified by a")
    c.drawString(75, 410, "practicing Chartered Accountant bearing a verifiable 18-character ICAI UDIN.")
    c.drawString(60, 385, "4. Certificate Temporal Validity: All statutory clearance documents, authorizations")
    c.drawString(75, 370, "and certificates must remain fully valid as on the tender submission deadline date.")
    
    c.drawString(60, 100, "Page 1 of 15")
    c.showPage()
    
    # Fill remaining pages to simulate a full 15-page enterprise RFP
    for i in range(2, 16):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, 720, f"CPCL/2026/001 - Technical & Governance Specifications (Part {i})")
        c.setFont("Helvetica", 9)
        c.drawString(60, 680, "General conditions of contract, anti-bribery policies, liquidated damages,")
        c.drawString(60, 665, "dispute resolution procedures and technical equipment tolerance thresholds.")
        c.drawString(60, 100, f"Page {i} of 15")
        c.showPage()
        
    c.save()
    print(f"Generated: {path}")

def create_bid_dossier(filename, bidder_name, bid_cr, turnovers, mii_pct, expiry_date, udin, address, author):
    path = f"demo_documents/{filename}"
    c = canvas.Canvas(path, pagesize=letter)
    
    # Inject metadata for collusion detection
    c.setAuthor(author)
    c.setCreator(author)
    
    # Page 1: Commercial Letter & Metadata
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, 720, "FORM-A: BID SUBMISSION DOSSIER")
    c.setFont("Helvetica", 10)
    c.drawString(60, 690, f"Bidder Legal Entity: {bidder_name}")
    c.drawString(60, 670, f"Registered Corporate Address: {address}")
    c.drawString(60, 650, f"Quoted Commercial Proposal Amount: INR {bid_cr} Crores")
    
    c.line(60, 635, 550, 635)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 610, "SCHEDULE B: STATUTORY CHARTERED ACCOUNTANT CERTIFICATE")
    c.setFont("Helvetica", 10)
    c.drawString(60, 580, f"This is to certify that the annual turnover figures of M/s {bidder_name} are as follows:")
    
    t_str = ", ".join([f"INR {t} Cr" for t in turnovers])
    c.drawString(75, 555, f"• Preceding Three Financial Years Turnover: {t_str}")
    c.drawString(75, 535, f"• Make in India Certified Domestic Local Content: {mii_pct}%")
    c.drawString(75, 515, f"• Statutory Compliance Certificate Expiry Date: {expiry_date}")
    c.drawString(75, 495, f"• Official ICAI Chartered Accountant UDIN: {udin}")
    
    c.drawString(60, 440, "Authorized Signatory & Seal")
    c.drawString(60, 100, "Page 1 of 5")
    c.showPage()
    
    for i in range(2, 6):
        c.setFont("Helvetica", 9)
        c.drawString(60, 720, f"Technical Datasheets, Machinery Compliance & Delivery Schedules - Page {i}")
        c.drawString(60, 100, f"Page {i} of 5")
        c.showPage()
        
    c.save()
    print(f"Generated: {path}")

if __name__ == "__main__":
    create_tender_rfp()
    
    # Bid 1: Clean Winner
    create_bid_dossier(
        "BID_01_Apex_Engineering_Compliant.pdf",
        bidder_name="Apex Engineering Systems Ltd",
        bid_cr=10.01,
        turnovers=[11.2, 12.5, 10.8],
        mii_pct=65.0,
        expiry_date="2026-12-31",
        udin="24078912AB12345678",
        address="Plot 42, Okhla Phase-3, New Delhi",
        author="Sharma_Consultancy_Word2019"
    )

    # Bid 2: Collusion Signal (Identical Author & Address, Close Price)
    create_bid_dossier(
        "BID_02_Bharat_Heavy_Collusion_Flag.pdf",
        bidder_name="Bharat Heavy Infra Corp",
        bid_cr=10.02,
        turnovers=[10.5, 11.1, 10.9],
        mii_pct=58.0,
        expiry_date="2026-11-30",
        udin="24078912AB12345679",
        address="Plot 42, Okhla Phase-3, New Delhi",
        author="Sharma_Consultancy_Word2019"
    )

    # Bid 3: Turnover Failure (Avg 9.77 Cr < 10.0 Cr) & MII Fail (42% < 50%)
    create_bid_dossier(
        "BID_03_Delta_Automation_Turnover_Fail.pdf",
        bidder_name="Delta Automation Ltd",
        bid_cr=12.80,
        turnovers=[8.4, 11.2, 9.7],
        mii_pct=42.0,
        expiry_date="2026-11-15",
        udin="24078912AB12345680",
        address="Sector 62, Electronic City, Noida",
        author="Delta_InHouse_Legal"
    )

    # Bid 4: Expired Certificate (2025-06-30 < 2026-10-15)
    create_bid_dossier(
        "BID_04_Vanguard_Tools_Temporal_Fail.pdf",
        bidder_name="Vanguard Precision Tools",
        bid_cr=11.45,
        turnovers=[13.0, 14.2, 12.8],
        mii_pct=52.0,
        expiry_date="2025-06-30",
        udin="24078912AB12345681",
        address="MIDC Industrial Area, Pune",
        author="Vanguard_Admin_Acrobat"
    )