import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

DIR_NAME = "live_jury_demo"
os.makedirs(DIR_NAME, exist_ok=True)

def create_drdo_tender_rfp():
    path = os.path.join(DIR_NAME, "DRDO_TENDER_RFP_2026_DRONE_SURVEILLANCE.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    
    # Page 1: Official Ministry / DRDO Tender Cover
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, 730, "DEFENCE RESEARCH & DEVELOPMENT ORGANISATION (DRDO)")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 705, "DIRECTORATE OF AERONAUTICAL SURVEILLANCE SYSTEMS")
    c.setLineWidth(1)
    c.line(50, 695, 560, 695)
    
    c.setFont("Helvetica", 10)
    c.drawString(50, 665, "Tender Reference Number : DRDO/AERO/2026/092")
    c.drawString(50, 645, "Project Title            : Tactical Autonomous Surveillance UAV Systems")
    c.drawString(50, 625, "Procuring Entity         : DRDO Ministry of Defence, New Delhi")
    c.drawString(50, 605, "Estimated Contract Value : INR 40.00 Crores")
    c.drawString(50, 585, "Tender Submission Deadline: 2026-11-20")
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 545, "STATUTORY COMMERCIAL & TECHNICAL MANDATES (ZERO-TOLERANCE)")
    c.setFont("Helvetica", 10)
    c.drawString(50, 520, "1. Financial Turnover: Average audited annual turnover of preceding 3 financial")
    c.drawString(65, 505, "years must not be less than INR 15.00 Crores.")
    c.drawString(50, 480, "2. Make in India (MII) Preference: Strictly Class-I Local Suppliers (minimum 50%")
    c.drawString(65, 465, "domestic value addition) eligible under Public Procurement Order.")
    c.drawString(50, 440, "3. Chartered Accountant Certification: Must bear valid 18-digit ICAI UDIN.")
    c.drawString(50, 415, "4. Temporal Validity: Statutory security & OEM clearance certificates must remain")
    c.drawString(65, 400, "strictly valid as on the date of submission deadline (2026-11-20).")
    
    c.drawString(50, 60, "Official Tender Document - Page 1 of 15")
    c.showPage()
    
    # Fill remaining pages for a 15-page tender
    for i in range(2, 16):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 730, f"DRDO/AERO/2026/092 - Technical & Operational Protocols (Sheet {i})")
        c.setFont("Helvetica", 9)
        c.drawString(50, 690, "Military spec MIL-STD-810H environmental testing, encrypted datalinks (AES-256),")
        c.drawString(50, 675, "fail-safe dual redundant avionics, and flight endurance standards.")
        c.drawString(50, 60, f"Official Tender Document - Page {i} of 15")
        c.showPage()
        
    c.save()
    print(f"Generated: {path}")

def create_jury_bid(filename, bidder, bid_cr, turnovers, mii_pct, expiry_date, udin, address, author):
    path = os.path.join(DIR_NAME, filename)
    c = canvas.Canvas(path, pagesize=letter)
    
    # Metadata Injection (For Collusion Scanner)
    c.setAuthor(author)
    c.setCreator(author)
    
    # Page 1: Commercial & Statutory CA Declaration
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 730, "BIDDER COMMERCIAL & STATUTORY SUBMISSION DOSSIER")
    c.setFont("Helvetica", 10)
    c.drawString(50, 700, f"Bidder Legal Entity Name    : {bidder}")
    c.drawString(50, 680, f"Registered Operational Facility: {address}")
    c.drawString(50, 660, f"Commercial Bid Quoted Value   : INR {bid_cr} Crores")
    c.line(50, 645, 560, 645)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 620, "AUDITED STATUTORY FINANCIALS & REGULATORY ATTESTATION")
    c.setFont("Helvetica", 10)
    c.drawString(50, 590, f"Certified that books of accounts for M/s {bidder} reflect:")
    
    t_str = ", ".join([f"INR {t} Cr" for t in turnovers])
    c.drawString(65, 565, f"• Audited Financial Turnovers (Past 3 Years): {t_str}")
    c.drawString(65, 545, f"• Declared Make In India (MII) Local Content : {mii_pct}%")
    c.drawString(65, 525, f"• Statutory Defence Clearance Certificate Expiry: {expiry_date}")
    c.drawString(65, 505, f"• Official ICAI Chartered Accountant UDIN       : {udin}")
    
    c.drawString(50, 440, "Authorized Signatory & CA Stamp")
    c.drawString(50, 60, "Bid Submission Dossier - Page 1 of 6")
    c.showPage()
    
    for i in range(2, 7):
        c.setFont("Helvetica", 9)
        c.drawString(50, 730, f"Avionics Specifications & Radar Calibration Sheets - Page {i}")
        c.drawString(50, 60, f"Bid Submission Dossier - Page {i} of 6")
        c.showPage()
        
    c.save()
    print(f"Generated: {path}")

if __name__ == "__main__":
    # 1. Tender
    create_drdo_tender_rfp()
    
    # 2. Bid 1: Clean Compliant
    create_jury_bid(
        "BID_01_Garuda_Dynamics_Compliant.pdf",
        bidder="Garuda Dynamics Aerospace Ltd",
        bid_cr=38.40,
        turnovers=[16.5, 18.2, 17.1],     # Avg 17.26 Cr > 15 Cr (Pass)
        mii_pct=68.0,                     # > 50% (Pass)
        expiry_date="2027-03-31",         # Valid
        udin="26099124AB98765431",
        address="Sector 18, Electronic Complex, Bengaluru",
        author="Kapadia_Aerospace_Legal"
    )

    # 3. Bid 2: Collusion Cover Bidding against Garuda Dynamics
    create_jury_bid(
        "BID_02_Trishul_Aero_Collusion_Cover.pdf",
        bidder="Trishul Aero Systems Pvt Ltd",
        bid_cr=38.48,                     # 0.2% variance with Garuda
        turnovers=[15.8, 16.2, 15.5],     # Avg 15.83 Cr > 15 Cr (Pass)
        mii_pct=62.0,                     # > 50% (Pass)
        expiry_date="2027-01-15",         # Valid
        udin="26099124AB98765432",
        address="Sector 18, Electronic Complex, Bengaluru", # Identical address
        author="Kapadia_Aerospace_Legal"  # Identical author & metadata
    )

    # 4. Bid 3: Make In India Violation (Non-Local / High Import Content)
    create_jury_bid(
        "BID_03_Zenith_Robotics_MII_Fail.pdf",
        bidder="Zenith Robotics Technologies",
        bid_cr=41.20,
        turnovers=[22.0, 24.5, 21.8],     # High turnover
        mii_pct=38.0,                     # 38% < 50% (Fails MII)
        expiry_date="2026-12-31",
        udin="26099124AB98765433",
        address="MIDC Industrial Zone, Pune",
        author="Zenith_InHouse_Legal"
    )

    # 5. Bid 4: Turnover Shortfall Disqualification (Deterministic Math)
    create_jury_bid(
        "BID_04_Falcon_Sensors_Turnover_Fail.pdf",
        bidder="Falcon Sensors India Ltd",
        bid_cr=39.90,
        turnovers=[12.5, 16.8, 14.2],     # Avg = 14.50 Cr < 15.0 Cr (Fail)
        mii_pct=55.0,
        expiry_date="2026-12-15",
        udin="26099124AB98765434",
        address="Balanagar Industrial Estate, Hyderabad",
        author="Falcon_Compliance_Desk"
    )