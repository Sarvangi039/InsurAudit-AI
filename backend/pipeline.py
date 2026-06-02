import os
import json
import uuid
import re
from PIL import Image
import fitz  # PyMuPDF
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
from backend.schemas import ClaimProfile, ItemizedCharge

load_dotenv()

# Configure Google Generative AI
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY and API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=API_KEY)
else:
    # We will still allow the app to run and show a configuration warning
    print("WARNING: GEMINI_API_KEY not configured or is placeholder. AI steps will be mocked/bypassed.")

# Set folders
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "uploads"))
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))

def convert_pdf_to_images(pdf_path: str, claim_id: str, doc_id: str) -> list:
    """Converts each page of a PDF to a PNG image locally without poppler."""
    os.makedirs(os.path.join(PROCESSED_DIR, claim_id), exist_ok=True)
    image_paths = []
    
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Render at 150 DPI for good OCR quality
            pix = page.get_pixmap(dpi=150)
            img_filename = f"{doc_id}_page_{page_num + 1}.png"
            img_path = os.path.join(PROCESSED_DIR, claim_id, img_filename)
            pix.save(img_path)
            # Store path relative to the app root or as a relative web path
            image_paths.append(img_path)
    except Exception as e:
        print(f"Error converting PDF {pdf_path}: {e}")
        
    return image_paths

def extract_structured_data(image_path: str, api_key: str = None) -> dict:
    """Calls Gemini Vision to classify the document and extract structured fields in JSON."""
    active_key = api_key or API_KEY
    if not active_key or active_key == "your_gemini_api_key_here":
        return get_mock_extraction(image_path)
        
    try:
        # Re-configure if a custom key is provided at runtime
        if api_key:
            genai.configure(api_key=api_key)
        else:
            genai.configure(api_key=API_KEY)
            
        model = genai.GenerativeModel("gemini-2.5-flash")
        img = Image.open(image_path)
        
        system_instruction = (
            "You are an expert AI Insurance Claim Document Auditor. Your task is to perform optical character "
            "recognition (OCR), classify the document type, and extract structured data fields from the medical claim document."
        )
        
        prompt = """
        Analyze this claim document page and return a JSON object with:
        1. "document_type": Classify into exactly one of: 
           "Claim form", "Hospital bill", "Discharge summary", "Lab report", "Prescription", "Diagnostic report", "Pharmacy bill", "Doctor notes", "Policy document", "ID proof", "KYC docs", or "Unknown"
        2. "confidence": A float confidence score between 0.0 and 1.0 for the classification.
        3. "extracted_fields": A dictionary of fields found. Only extract what is present in the document.
           Include fields from the list below if applicable to this document type:
           - Patient name (patient_name)
           - Policy number (policy_number)
           - Primary Policyholder name (policyholder_name)
           - Patient DOB (patient_dob)
           - Patient ID Number / Aadhar / PAN (patient_id_number)
           - Admission date (admission_date) (format YYYY-MM-DD)
           - Discharge date (discharge_date) (format YYYY-MM-DD)
           - Diagnosis text (diagnosis)
           - ICD codes (icd_codes) (list of strings, e.g. ["K35.8"])
           - Procedures/Treatments (procedures) (list of strings)
           - Attending doctor (attending_doctor)
           - Doctor registration number (doctor_registration)
           - Hospital name (hospital_name)
           - Hospital tier (hospital_tier) (NABH or non-NABH)
           - Policy start date (policy_start_date) (format YYYY-MM-DD)
           - Policy end date (policy_end_date) (format YYYY-MM-DD)
           - Sum insured (policy_sum_insured)
           - Policy room rent limit per day (policy_room_rent_limit)
           - Total room rent charged (room_charges_total)
           - Total ICU charges (icu_charges_total)
           - Total pharmacy charges (pharmacy_charges_total)
           - Total lab/diagnostic charges (investigation_charges_total)
           - Total consultation charges (consultation_charges_total)
           - Other charges (other_charges_total)
           - Total billed amount (total_billed_amount)
           - Itemized charges list (itemized_charges) - list of objects with {"description": str, "unit_rate": float, "quantity": int, "amount": float}
           - Medicines prescribed (medicines_prescribed) - list of strings
        4. "raw_ocr_summary": A brief text summary of key paragraphs/text on the page for keyword search.

        Return ONLY a raw JSON object matching this schema. Do not enclose it in markdown ```json blocks.
        """
        
        response = model.generate_content(
            [prompt, img],
            generation_config={"response_mime_type": "application/json"}
        )
        
        data = json.loads(response.text)
        return data
        
    except Exception as e:
        print(f"Gemini API error during extraction: {e}")
        # Return fallback mock parsing
        return get_mock_extraction(image_path)

def merge_document_profiles(documents_data: list) -> ClaimProfile:
    """Combines fields from multiple document extractions into a single canonical ClaimProfile."""
    # Priority order for fields:
    # patient_name: Discharge summary > Claim form > Hospital bill > Prescriptions > ID proof
    # policy_number: Policy document > Claim form > Hospital bill
    # admission_date / discharge_date: Discharge summary > Claim form > Hospital bill
    # diagnosis: Discharge summary > Claim form > Doctor notes
    # hospital_name: Hospital bill > Discharge summary > Claim form
    
    merged = {}
    
    # Track sources to resolve conflicts
    sources = {
        "patient_name": ("Discharge summary", "Claim form", "Hospital bill", "ID proof"),
        "policy_number": ("Policy document", "Claim form", "Hospital bill"),
        "admission_date": ("Discharge summary", "Claim form", "Hospital bill"),
        "discharge_date": ("Discharge summary", "Claim form", "Hospital bill"),
        "diagnosis": ("Discharge summary", "Claim form", "Doctor notes"),
        "hospital_name": ("Hospital bill", "Discharge summary", "Claim form"),
        "attending_doctor": ("Prescription", "Discharge summary", "Hospital bill"),
        "doctor_registration": ("Prescription", "Discharge summary", "Hospital bill")
    }
    
    extracted_by_type = {}
    for doc in documents_data:
        dtype = doc.get("document_type")
        fields = doc.get("extracted_fields", {})
        if dtype not in extracted_by_type:
            extracted_by_type[dtype] = []
        extracted_by_type[dtype].append(fields)
        
    # Helper to resolve field value by document type priority
    def resolve_field(field_name: str, fallback_value=None):
        priority_types = sources.get(field_name, [])
        # Check priority document types first
        for ptype in priority_types:
            if ptype in extracted_by_type:
                for doc_fields in extracted_by_type[ptype]:
                    val = doc_fields.get(field_name)
                    if val:
                        return val
        # Check all other document types
        for dtype, docs in extracted_by_type.items():
            for doc_fields in docs:
                val = doc_fields.get(field_name)
                if val:
                    return val
        return fallback_value

    # Extract single-value fields
    merged["patient_name"] = resolve_field("patient_name")
    merged["policy_number"] = resolve_field("policy_number")
    merged["policyholder_name"] = resolve_field("policyholder_name") or merged["patient_name"]
    merged["patient_dob"] = resolve_field("patient_dob")
    merged["patient_id_number"] = resolve_field("patient_id_number")
    merged["admission_date"] = resolve_field("admission_date")
    merged["discharge_date"] = resolve_field("discharge_date")
    merged["diagnosis"] = resolve_field("diagnosis")
    merged["attending_doctor"] = resolve_field("attending_doctor")
    merged["doctor_registration"] = resolve_field("doctor_registration")
    merged["hospital_name"] = resolve_field("hospital_name")
    merged["hospital_registration"] = resolve_field("hospital_registration")
    merged["hospital_tier"] = resolve_field("hospital_tier", "non-NABH")
    merged["policy_start_date"] = resolve_field("policy_start_date")
    merged["policy_end_date"] = resolve_field("policy_end_date")
    merged["policy_sum_insured"] = resolve_field("policy_sum_insured")
    merged["policy_room_rent_limit"] = resolve_field("policy_room_rent_limit")

    # Combine array fields across all documents
    icd_codes = set()
    procedures = set()
    medicines = set()
    itemized_charges = []
    
    for dtype, docs in extracted_by_type.items():
        for fields in docs:
            # ICD codes
            for code in fields.get("icd_codes", []):
                icd_codes.add(code)
            # Procedures
            for proc in fields.get("procedures", []):
                procedures.add(proc)
            # Medicines
            for med in fields.get("medicines_prescribed", []):
                medicines.add(med)
            # Itemized charges
            for item in fields.get("itemized_charges", []):
                itemized_charges.append(ItemizedCharge(**item))
                
    merged["icd_codes"] = list(icd_codes)
    merged["procedures"] = list(procedures)
    merged["medicines_prescribed"] = list(medicines)
    merged["itemized_charges"] = itemized_charges

    # Aggregate financial totals from hospital bill documents
    room_charges = 0.0
    icu_charges = 0.0
    pharmacy_charges = 0.0
    investigation_charges = 0.0
    consultation_charges = 0.0
    other_charges = 0.0
    total_billed = 0.0

    if "Hospital bill" in extracted_by_type:
        for bill in extracted_by_type["Hospital bill"]:
            room_charges += float(bill.get("room_charges_total", 0.0) or 0.0)
            icu_charges += float(bill.get("icu_charges_total", 0.0) or 0.0)
            pharmacy_charges += float(bill.get("pharmacy_charges_total", 0.0) or 0.0)
            investigation_charges += float(bill.get("investigation_charges_total", 0.0) or 0.0)
            consultation_charges += float(bill.get("consultation_charges_total", 0.0) or 0.0)
            other_charges += float(bill.get("other_charges_total", 0.0) or 0.0)
            total_billed += float(bill.get("total_billed_amount", 0.0) or 0.0)
    else:
        # Fallback to other billing docs if no official hospital bill
        for dtype, docs in extracted_by_type.items():
            if "bill" in dtype.lower() or "invoice" in dtype.lower():
                for bill in docs:
                    total_billed += float(bill.get("total_billed_amount", 0.0) or 0.0)

    # If itemized charges exist but totals are zero, try to categorize and sum them up
    if len(itemized_charges) > 0 and total_billed == 0.0:
        for item in itemized_charges:
            total_billed += item.amount
            desc = item.description.lower()
            if "room" in desc or "rent" in desc or "bed" in desc:
                room_charges += item.amount
            elif "icu" in desc or "intensive care" in desc:
                icu_charges += item.amount
            elif "pharmacy" in desc or "medicine" in desc or "drug" in desc:
                pharmacy_charges += item.amount
            elif "lab" in desc or "test" in desc or "xray" in desc or "mri" in desc or "scans" in desc or "investigation" in desc:
                investigation_charges += item.amount
            elif "consult" in desc or "visit" in desc or "doctor" in desc:
                consultation_charges += item.amount
            else:
                other_charges += item.amount

    merged["room_charges_total"] = room_charges
    merged["icu_charges_total"] = icu_charges
    merged["pharmacy_charges_total"] = pharmacy_charges
    merged["investigation_charges_total"] = investigation_charges
    merged["consultation_charges_total"] = consultation_charges
    merged["other_charges_total"] = other_charges
    merged["total_billed_amount"] = total_billed

    # Calculate derived length of stay
    if merged["admission_date"] and merged["discharge_date"]:
        try:
            ad = datetime.strptime(merged["admission_date"], "%Y-%m-%d")
            dd = datetime.strptime(merged["discharge_date"], "%Y-%m-%d")
            merged["length_of_stay"] = max((dd - ad).days, 0)
        except Exception:
            merged["length_of_stay"] = None

    return ClaimProfile(**merged)

def generate_ai_explanation(profile: ClaimProfile, flags: list, risk_score: int, api_key: str = None) -> str:
    """Uses Gemini to synthesize a 3-5 sentence audit summary of flags and details for the auditor."""
    active_key = api_key or API_KEY
    if not active_key or active_key == "your_gemini_api_key_here":
        return get_mock_explanation(profile, flags, risk_score)
        
    try:
        if api_key:
            genai.configure(api_key=api_key)
        else:
            genai.configure(api_key=API_KEY)
            
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        flags_text = ""
        for i, f in enumerate(flags):
            flags_text += f"{i+1}. [{f['severity']}] {f['category']} - {f['message']} (Evidence: {f.get('evidence')})\n"
            
        prompt = f"""
        You are a senior insurance claims auditor reviewing the findings of an automated audit system.
        Review the following claim data and flag analysis, and write a professional, factual 3-5 sentence summary briefing for the human auditor.
        
        Patient Name: {profile.patient_name}
        Hospital: {profile.hospital_name}
        Admission Date: {profile.admission_date}
        Discharge Date: {profile.discharge_date}
        Total Claimed Amount: Rs. {profile.total_billed_amount:,.2f}
        Risk Score: {risk_score}/100
        
        Triggered Audit Flags:
        {flags_text if flags_text else "No flags triggered."}
        
        Write a concise, professional briefing note. 
        - Cite specific figures, dates, or flag details if relevant.
        - Tone should be neutral, analytic, and objective.
        - End with a clear recommendation (e.g. "Recommend full manual audit due to identity mismatches and policy limit breaches" or "Recommend auto-approval as no critical flags were triggered").
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Gemini API error during summary generation: {e}")
        return get_mock_explanation(profile, flags, risk_score)

# Fallbacks/Mocks when API keys are missing

def get_mock_extraction(image_path: str) -> dict:
    """Generates mock structured parsing based on filename hints for visual testing when Gemini key is missing."""
    fname = os.path.basename(image_path).lower()
    
    # Default fallback skeleton
    result = {
        "document_type": "Unknown",
        "confidence": 0.50,
        "extracted_fields": {},
        "raw_ocr_summary": "Mock OCR extraction fallback for local testing."
    }
    
    # Generate intelligent mocks depending on filename
    if "claim_form" in fname:
        result["document_type"] = "Claim form"
        result["confidence"] = 0.98
        result["extracted_fields"] = {
            "patient_name": "Ramesh Kumar Shah",
            "policy_number": "POL-994821",
            "admission_date": "2026-05-10",
            "discharge_date": "2026-05-15",
            "total_billed_amount": 75000.0,
            "diagnosis": "Acute Appendicitis"
        }
    elif "discharge" in fname:
        result["document_type"] = "Discharge summary"
        result["confidence"] = 0.95
        result["extracted_fields"] = {
            "patient_name": "Ramesh Kumar Shah", # Match
            "admission_date": "2026-05-10",
            "discharge_date": "2026-05-15",
            "diagnosis": "Acute Appendicitis",
            "procedures": ["Laparoscopic Appendectomy"],
            "attending_doctor": "Dr. Sunil Gupta",
            "doctor_registration": "MCI-48291",
            "hospital_name": "City Health Hospital",
            "hospital_tier": "NABH"
        }
    elif "bill" in fname or "invoice" in fname:
        result["document_type"] = "Hospital bill"
        result["confidence"] = 0.92
        result["extracted_fields"] = {
            "patient_name": "Ramesh K. Shah", # Minor mismatch
            "total_billed_amount": 75000.0,
            "hospital_name": "City Health Hospital",
            "room_charges_total": 30000.0,  # 5 days * 6000
            "pharmacy_charges_total": 15000.0,
            "investigation_charges_total": 12000.0,
            "consultation_charges_total": 8000.0,
            "other_charges_total": 10000.0,
            "itemized_charges": [
                {"description": "NABH Single Room Rent - 5 days", "unit_rate": 6000.0, "quantity": 5, "amount": 30000.0},
                {"description": "OT Charges & Consumables", "unit_rate": 10000.0, "quantity": 1, "amount": 10000.0},
                {"description": "Surgeon Consultation Fees", "unit_rate": 8000.0, "quantity": 1, "amount": 8000.0},
                {"description": "Lab Investigations (CBC, LFT, Scan)", "unit_rate": 12000.0, "quantity": 1, "amount": 12000.0},
                {"description": "Pharmacy Medicines & IV fluids", "unit_rate": 15000.0, "quantity": 1, "amount": 15000.0}
            ]
        }
    elif "policy" in fname:
        result["document_type"] = "Policy document"
        result["confidence"] = 0.99
        result["extracted_fields"] = {
            "policyholder_name": "Ramesh Kumar Shah",
            "policy_number": "POL-994821",
            "policy_start_date": "2025-09-01",
            "policy_end_date": "2026-08-31",
            "policy_sum_insured": 500000.0,
            "policy_room_rent_limit": 5000.0 # Will trigger room rent breach rule (6000 > 5000)
        }
    elif "prescription" in fname:
        result["document_type"] = "Prescription"
        result["confidence"] = 0.90
        result["extracted_fields"] = {
            "patient_name": "Ramesh Shah",
            "attending_doctor": "Dr. Sunil Gupta",
            "doctor_registration": "MCI-48291",
            "medicines_prescribed": ["Ciprofloxacin 500mg", "Paracetamol 650mg", "Pantoprazole 40mg"]
        }
    elif "id" in fname or "aadhar" in fname:
        result["document_type"] = "ID proof"
        result["confidence"] = 0.97
        result["extracted_fields"] = {
            "patient_name": "Ramesh Kumar Shah",
            "patient_dob": "1980-04-12",
            "patient_id_number": "1234-5678-9012"
        }
    return result

def get_mock_explanation(profile: ClaimProfile, flags: list, risk_score: int) -> str:
    """Fallback generator for plain-text AI explanation summaries."""
    if not flags:
        return (
            f"The claim for patient {profile.patient_name or 'N/A'} at {profile.hospital_name or 'N/A'} "
            f"for a total amount of Rs. {profile.total_billed_amount:,.2f} is flagged as LOW RISK (Score: {risk_score}/100). "
            f"No policy limits or name consistency rules were breached. Recommend auto-approval."
        )
    
    summary = (
        f"Audit findings for the claim of {profile.patient_name or 'N/A'} (Total Billed: Rs. {profile.total_billed_amount:,.2f}) "
        f"indicate a risk score of {risk_score}/100 (Category: {'HIGH' if risk_score >= 55 else 'MEDIUM'}). "
        f"Key issues flagged include: "
    )
    
    bullet_points = [f"{f['category']}: {f['message']}" for f in flags[:3]]
    summary += "; ".join(bullet_points)
    
    summary += ". "
    if risk_score >= 55:
        summary += "Recommend manual auditor escalation and inquiry into the hospital billing rates and identity discrepancies."
    else:
        summary += "Recommend conditional approval subject to review of itemized room rents."
        
    return summary
