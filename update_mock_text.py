import re

file_path = "d:/7th sem/summer internship/OCR/backend/pipeline.py"

with open(file_path, "r") as f:
    content = f.read()

# 1. Update claim_form
content = content.replace(
    '        result["document_type"] = "Claim form"\n        result["confidence"] = 0.98',
    '        result["document_type"] = "Claim form"\n        result["confidence"] = 0.98\n        result["raw_ocr_summary"] = "HEALTH INSURANCE CLAIM FORM Standard Reimbursement Submission. Patient Name: Ramesh Kumar Shah. Policy Number: POL-994821. Patient DOB: 1980-04-12. Admission Date: 2026-05-10. Discharge Date: 2026-05-15. Diagnosis: Acute Appendicitis. Claimed Amount: Rs 75,000.00. Hospital Registration: REG-44912. Date of Filing: 2026-05-20. DECLARATION BY THE CLAIMANT: I hereby declare that the details given in this form are true and correct."'
)

# 2. Update discharge
content = content.replace(
    '        result["document_type"] = "Discharge summary"\n        result["confidence"] = 0.95',
    '        result["document_type"] = "Discharge summary"\n        result["confidence"] = 0.95\n        result["raw_ocr_summary"] = "DISCHARGE SUMMARY. Patient Name: Ramesh Kumar Shah. Age: 46. Sex: Male. Date of Admission: 10-May-2026. Date of Discharge: 15-May-2026. Diagnosis: Acute Appendicitis. Procedure Performed: Laparoscopic Appendectomy. Attending Physician: Dr. Sunil Gupta, MCI-48291. Hospital: City Health Hospital (NABH Accredited). Patient presented with severe right lower quadrant abdominal pain. Surgery was uneventful and patient recovered well. Advised soft diet and follow-up in 7 days."'
)

# 3. Update bill
content = content.replace(
    '        result["document_type"] = "Hospital bill"\n        result["confidence"] = 0.92',
    '        result["document_type"] = "Hospital bill"\n        result["confidence"] = 0.92\n        result["raw_ocr_summary"] = "FINAL HOSPITAL BILL / INVOICE. Patient: Ramesh K. Shah. City Health Hospital. Bill Date: 15-May-2026. Room Rent (Single Room 5 days @ 6000): 30,000. OT Charges: 10,000. Surgeon Fees: 8,000. Investigations: 12,000. Pharmacy: 15,000. Total Billed Amount: Rs 75,000.00. Please pay before discharge."'
)

# 4. Update policy
content = content.replace(
    '        result["document_type"] = "Policy document"\n        result["confidence"] = 0.99',
    '        result["document_type"] = "Policy document"\n        result["confidence"] = 0.99\n        result["raw_ocr_summary"] = "HEALTH INSURANCE POLICY SCHEDULE. Policyholder: Ramesh Kumar Shah. Policy Number: POL-994821. Valid From: 01-Sep-2025 To: 31-Aug-2026. Sum Insured: Rs 5,00,000. Room Rent Limit: Rs 5,000 per day. ICU Limit: Actuals. Maternity coverage: Not included. Pre-existing disease waiting period: 2 years."'
)

# 5. Update prescription
content = content.replace(
    '        result["document_type"] = "Prescription"\n        result["confidence"] = 0.90',
    '        result["document_type"] = "Prescription"\n        result["confidence"] = 0.90\n        result["raw_ocr_summary"] = "PRESCRIPTION. Dr. Sunil Gupta, General Surgeon. Reg No: MCI-48291. Patient: Ramesh Shah. Date: 09-May-2026. Rx: Tab Ciprofloxacin 500mg BD x 5 days, Tab Paracetamol 650mg SOS, Tab Pantoprazole 40mg OD x 5 days. Advise immediate admission for appendectomy."'
)

# 6. Update id
content = content.replace(
    '        result["document_type"] = "ID proof"\n        result["confidence"] = 0.97',
    '        result["document_type"] = "ID proof"\n        result["confidence"] = 0.97\n        result["raw_ocr_summary"] = "This document is an Identity Proof - Aadharcard Schedule. It lists the full name as Ramesh Kumar Shah, date of birth as 1980-04-12, gender as Male, and ID Number / Aadhar as 1234-5678-9012."'
)

with open(file_path, "w") as f:
    f.write(content)

print("backend/pipeline.py successfully updated with rich mock text.")
