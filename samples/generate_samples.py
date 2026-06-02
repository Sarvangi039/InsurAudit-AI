import os
import sys
import subprocess

def create_mock_images():
    """Generates standard textual claim documents as PNG images for testing OCR."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[INFO] Installing Pillow to generate mock sample documents...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
        from PIL import Image, ImageDraw

    os.makedirs("samples", exist_ok=True)
    
    # 1. Claim Form
    img1 = Image.new('RGB', (800, 1100), color='#ffffff')
    d1 = ImageDraw.Draw(img1)
    # Header block
    d1.rectangle([(20, 20), (780, 100)], fill='#1e3a8a')
    d1.text((40, 45), "HEALTH INSURANCE CLAIM FORM", fill='#ffffff')
    d1.text((40, 75), "Standard Reimbursement Submission", fill='#93c5fd')
    # Fields
    fields1 = [
        ("PATIENT NAME:", "Ramesh Kumar Shah"),
        ("POLICY NUMBER:", "POL-994821"),
        ("PATIENT DOB:", "1980-04-12"),
        ("ADMISSION DATE:", "2026-05-10"),
        ("DISCHARGE DATE:", "2026-05-15"),
        ("DIAGNOSIS:", "Acute Appendicitis"),
        ("CLAIMED AMOUNT:", "Rs. 75,000.00"),
        ("HOSPITAL REGISTRATION:", "REG-44912"),
        ("DATE OF FILING:", "2026-05-20"),
    ]
    y = 150
    for label, val in fields1:
        d1.text((50, y), label, fill='#475569')
        d1.text((250, y), val, fill='#0f172a')
        d1.line([(50, y + 25), (750, y + 25)], fill='#cbd5e1')
        y += 50
    
    # Footer notice
    d1.rectangle([(20, 950), (780, 1050)], fill='#f1f5f9')
    d1.text((40, 970), "DECLARATION BY THE CLAIMANT:", fill='#334155')
    d1.text((40, 1000), "I hereby declare that the details given in this form are true and correct.", fill='#64748b')
    img1.save(os.path.join("samples", "claim_form_ramesh.png"))

    # 2. Hospital Bill
    img2 = Image.new('RGB', (800, 1100), color='#ffffff')
    d2 = ImageDraw.Draw(img2)
    d2.rectangle([(20, 20), (780, 100)], fill='#0f172a')
    d2.text((40, 45), "CITY HEALTH HOSPITAL - INVOICE", fill='#ffffff')
    d2.text((40, 75), "NABH Accredited | Hospital Reg No: REG-44912", fill='#94a3b8')
    
    # Header Details
    d2.text((50, 130), "PATIENT: Ramesh K. Shah", fill='#0f172a')
    d2.text((50, 150), "ADMISSION: 2026-05-10", fill='#0f172a')
    d2.text((50, 170), "DISCHARGE: 2026-05-15", fill='#0f172a')
    d2.text((550, 130), "INVOICE NO: INV-2026-88", fill='#0f172a')
    d2.text((550, 150), "BILL DATE: 2026-05-15", fill='#0f172a')
    d2.line([(20, 200), (780, 200)], fill='#0f172a', width=2)
    
    # Table headers
    d2.text((50, 220), "Description", fill='#475569')
    d2.text((380, 220), "Rate", fill='#475569')
    d2.text((480, 220), "Qty", fill='#475569')
    d2.text((600, 220), "Amount", fill='#475569')
    d2.line([(20, 245), (780, 245)], fill='#94a3b8')
    
    # Line items
    items = [
        ("NABH Single Room Rent - 5 days", "6,000.00", "5", "30,000.00"),
        ("OT Charges & Consumables", "10,000.00", "1", "10,000.00"),
        ("Surgeon Consultation Fees", "8,000.00", "1", "8,000.00"),
        ("Lab Investigations (CBC, LFT, Scan)", "12,000.00", "1", "12,000.00"),
        ("Pharmacy Medicines & IV fluids", "15,000.00", "1", "15,000.00"),
    ]
    y = 265
    for desc, rate, qty, amt in items:
        d2.text((50, y), desc, fill='#0f172a')
        d2.text((380, y), rate, fill='#0f172a')
        d2.text((480, y), qty, fill='#0f172a')
        d2.text((600, y), amt, fill='#0f172a')
        d2.line([(20, y + 25), (780, y + 25)], fill='#cbd5e1')
        y += 40
        
    # Total
    d2.line([(20, y), (780, y)], fill='#0f172a', width=2)
    d2.text((450, y + 20), "GRAND TOTAL:", fill='#0f172a')
    d2.text((600, y + 20), "Rs. 75,000.00", fill='#0f172a')
    img2.save(os.path.join("samples", "hospital_bill_ramesh.png"))

    # 3. Discharge Summary
    img3 = Image.new('RGB', (800, 1100), color='#ffffff')
    d3 = ImageDraw.Draw(img3)
    d3.rectangle([(20, 20), (780, 100)], fill='#047857')
    d3.text((40, 45), "CITY HEALTH HOSPITAL - DISCHARGE SUMMARY", fill='#ffffff')
    d3.text((40, 75), "Attending Consultant Case File Record", fill='#a7f3d0')
    
    fields3 = [
        ("PATIENT NAME:", "Ramesh Kumar Shah"),
        ("ADMISSION DATE:", "2026-05-10"),
        ("DISCHARGE DATE:", "2026-05-15"),
        ("DIAGNOSIS:", "Acute Appendicitis"),
        ("PROCEDURE DONE:", "Laparoscopic Appendectomy"),
        ("SURGEON NAME:", "Dr. Sunil Gupta"),
        ("SURGEON REGISTRATION:", "MCI-48291"),
        ("PATIENT CONDITION:", "Stable, discharged with medications"),
    ]
    y = 150
    for label, val in fields3:
        d3.text((50, y), label, fill='#475569')
        d3.text((250, y), val, fill='#0f172a')
        d3.line([(50, y + 25), (750, y + 25)], fill='#cbd5e1')
        y += 50
    img3.save(os.path.join("samples", "discharge_summary_ramesh.png"))

    # 4. Policy Document
    img4 = Image.new('RGB', (800, 1100), color='#ffffff')
    d4 = ImageDraw.Draw(img4)
    d4.rectangle([(20, 20), (780, 100)], fill='#0284c7')
    d4.text((40, 45), "STAR HEALTH INSURANCE POLICY CONTRACT", fill='#ffffff')
    d4.text((40, 75), "Individual Health Cover Schedule", fill='#bae6fd')
    
    fields4 = [
        ("POLICYHOLDER:", "Ramesh Kumar Shah"),
        ("POLICY NUMBER:", "POL-994821"),
        ("SUM INSURED:", "Rs. 5,00,000.00"),
        ("POLICY START DATE:", "2025-09-01"),
        ("POLICY END DATE:", "2026-08-31"),
        ("ROOM RENT ALLOWANCE:", "Rs. 5,000.00 per day"),
        ("CO-PAYMENT CLAUSE:", "Nil"),
        ("GRACE PERIOD FOR FILING:", "90 days post discharge"),
    ]
    y = 150
    for label, val in fields4:
        d4.text((50, y), label, fill='#475569')
        d4.text((250, y), val, fill='#0f172a')
        d4.line([(50, y + 25), (750, y + 25)], fill='#cbd5e1')
        y += 50
    img4.save(os.path.join("samples", "policy_doc_ramesh.png"))

    # 5. ID Proof
    img5 = Image.new('RGB', (800, 600), color='#ffffff')
    d5 = ImageDraw.Draw(img5)
    d5.rectangle([(20, 20), (780, 80)], fill='#b45309')
    d5.text((40, 40), "IDENTITY PROOF - AADHAR CARD SCHEDULE", fill='#ffffff')
    
    fields5 = [
        ("FULL NAME:", "Ramesh Kumar Shah"),
        ("DATE OF BIRTH:", "1980-04-12"),
        ("GENDER:", "Male"),
        ("ID NUMBER / AADHAR:", "1234-5678-9012"),
    ]
    y = 120
    for label, val in fields5:
        d5.text((50, y), label, fill='#475569')
        d5.text((250, y), val, fill='#0f172a')
        d5.line([(50, y + 25), (750, y + 25)], fill='#cbd5e1')
        y += 50
    img5.save(os.path.join("samples", "aadhar_id_ramesh.png"))

    print("[SUCCESS] Successfully generated 5 mock claim documents inside 'samples/' folder!")

if __name__ == "__main__":
    create_mock_images()
