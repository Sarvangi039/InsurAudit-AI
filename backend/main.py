import os
import shutil
import uuid
import re
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import (
    init_db, get_all_claims, get_claim_details, create_claim, 
    add_document, update_claim_profile, update_document_details,
    save_audit_flags, log_decision, update_claim_status
)
from backend.pipeline import (
    convert_pdf_to_images, extract_structured_data, 
    merge_document_profiles, generate_ai_explanation
)
from backend.rules import run_audit_rules, calculate_risk_score
from backend.schemas import ClaimProfile, ClaimUpdateInput, AuditorDecisionInput

# Initialize DB on startup
init_db()

app = FastAPI(
    title="Insurance Claim Auditor AI API",
    description="Local MVP for Vision OCR & Rules-Based Claims Auditing",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to check allowed extensions
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}

def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()

@app.post("/api/claims/upload")
async def upload_claims(files: List[UploadFile] = File(...)):
    """Uploads claim documents, registers the bundle, and schedules ingestion."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
        
    claim_id = str(uuid.uuid4())
    upload_path = os.path.join("data", "uploads", claim_id)
    processed_path = os.path.join("data", "processed", claim_id)
    
    os.makedirs(upload_path, exist_ok=True)
    os.makedirs(processed_path, exist_ok=True)
    
    registered_docs = []
    total_billed_amount_estimate = 0.0
    
    for upload_file in files:
        ext = get_file_extension(upload_file.filename)
        if ext not in ALLOWED_EXTENSIONS:
            continue
            
        doc_id = str(uuid.uuid4())
        dest_filename = f"{doc_id}{ext}"
        dest_path = os.path.join(upload_path, dest_filename)
        
        # Save file to upload directory
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        # Standardize: convert PDF to images or copy image pages
        pages_images = []
        if ext == ".pdf":
            pages_images = convert_pdf_to_images(dest_path, claim_id, doc_id)
        else:
            # For direct image uploads, copy to processed path as a single-page document
            page_filename = f"{doc_id}_page_1{ext}"
            page_dest = os.path.join(processed_path, page_filename)
            shutil.copy(dest_path, page_dest)
            pages_images = [page_dest]
            
        # Add document metadata to DB
        add_document(
            doc_id=doc_id,
            claim_id=claim_id,
            file_name=upload_file.filename,
            file_path=dest_path,
            pages_count=len(pages_images)
        )
        
        registered_docs.append({
            "doc_id": doc_id,
            "filename": upload_file.filename,
            "pages_count": len(pages_images)
        })
        
    # Create main claim placeholder
    create_claim(
        claim_id=claim_id,
        patient_name="Awaiting Processing...",
        policy_number="N/A",
        total_claimed=0.0
    )
    
    return {
        "claim_id": claim_id,
        "message": "Claim documents uploaded successfully.",
        "documents": registered_docs
    }

@app.post("/api/claims/{claim_id}/process")
async def process_claim(claim_id: str, x_gemini_api_key: str = Header(None)):
    """Executes the complete pipeline: PDF render, Gemini Vision OCR, extraction, rules checks, and explanations."""
    claim = get_claim_details(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    processed_path = os.path.join("data", "processed", claim_id)
    extracted_docs = []
    
    # Process each document in the claim
    for doc in claim["documents"]:
        doc_id = doc["id"]
        file_path = doc["file_path"]
        ext = get_file_extension(doc["file_name"])
        
        # Gather all pages for this document
        pages_prefix = f"{doc_id}_page_"
        page_files = [f for f in os.listdir(processed_path) if f.startswith(pages_prefix)]
        page_files.sort(key=lambda x: int(re.search(r'_page_(\d+)', x).group(1)))
        
        doc_ocr_text = []
        doc_type = "Unknown"
        doc_confidence = 1.0
        doc_extracted_fields = {}
        
        # Analyze each page
        for page_file in page_files:
            page_path = os.path.join(processed_path, page_file)
            page_result = extract_structured_data(page_path, api_key=x_gemini_api_key)
            
            # Aggregate text and fields
            doc_ocr_text.append(page_result.get("raw_ocr_summary", ""))
            doc_type = page_result.get("document_type", "Unknown")
            doc_confidence = min(doc_confidence, page_result.get("confidence", 1.0))
            
            # Merge fields from pages
            fields = page_result.get("extracted_fields", {})
            for k, v in fields.items():
                if isinstance(v, list) and k in doc_extracted_fields:
                    doc_extracted_fields[k].extend(v)
                else:
                    doc_extracted_fields[k] = v
                    
        # Clean list duplicates if list of codes, procedures, etc.
        for k in ["icd_codes", "procedures", "medicines_prescribed"]:
            if k in doc_extracted_fields and isinstance(doc_extracted_fields[k], list):
                doc_extracted_fields[k] = list(set(doc_extracted_fields[k]))
                
        # Save OCR and classification to DB
        combined_ocr = "\n--- PAGE BREAK ---\n".join(doc_ocr_text)
        update_document_details(doc_id, doc_type, doc_confidence, combined_ocr)
        
        extracted_docs.append({
            "document_id": doc_id,
            "document_type": doc_type,
            "extracted_fields": doc_extracted_fields,
            "raw_ocr_summary": combined_ocr
        })
        
    # Merge documents to claim profile
    profile = merge_document_profiles(extracted_docs)
    
    # Evaluate audit rules
    flags = run_audit_rules(profile, extracted_docs)
    risk_score = calculate_risk_score(flags)
    
    # Generate AI auditor narrative explanation
    explanation = generate_ai_explanation(profile, flags, risk_score, api_key=x_gemini_api_key)
    
    # Persist back to DB
    update_claim_profile(
        claim_id=claim_id,
        patient_name=profile.patient_name or "Unknown Patient",
        policy_number=profile.policy_number or "N/A",
        admission_date=profile.admission_date,
        discharge_date=profile.discharge_date,
        total_claimed=profile.total_billed_amount,
        profile_json=profile.dict(),
        risk_score=risk_score,
        summary=explanation
    )
    
    save_audit_flags(claim_id, flags)
    
    return get_claim_details(claim_id)

@app.post("/api/claims/{claim_id}/update")
async def update_claim_data(claim_id: str, payload: ClaimUpdateInput, x_gemini_api_key: str = Header(None)):
    """Allows manual override of claim data from the UI and dynamically re-runs rules evaluation."""
    claim = get_claim_details(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    # Merge existing profile JSON with manual updates
    profile_dict = claim.get("profile", {})
    
    # Update properties
    update_data = payload.dict(exclude_unset=True)
    for k, v in update_data.items():
        profile_dict[k] = v
        
    # Recalculate derived fields
    if profile_dict.get("admission_date") and profile_dict.get("discharge_date"):
        try:
            from datetime import datetime
            ad = datetime.strptime(profile_dict["admission_date"], "%Y-%m-%d")
            dd = datetime.strptime(profile_dict["discharge_date"], "%Y-%m-%d")
            profile_dict["length_of_stay"] = max((dd - ad).days, 0)
        except:
            profile_dict["length_of_stay"] = None

    profile = ClaimProfile(**profile_dict)
    
    # Gather document extractions from db for re-running rules (mocking the pipeline structure)
    document_extractions = []
    for doc in claim["documents"]:
        document_extractions.append({
            "document_type": doc["doc_type"],
            "extracted_fields": {
                "patient_name": doc["doc_type"] != "Policy document" and doc.get("patient_name") or None
            }
        })
        
    # Re-run rule engine
    flags = run_audit_rules(profile, document_extractions)
    risk_score = calculate_risk_score(flags)
    
    # Re-generate explanation
    explanation = generate_ai_explanation(profile, flags, risk_score, api_key=x_gemini_api_key)
    
    # Update DB
    update_claim_profile(
        claim_id=claim_id,
        patient_name=profile.patient_name or "Unknown Patient",
        policy_number=profile.policy_number or "N/A",
        admission_date=profile.admission_date,
        discharge_date=profile.discharge_date,
        total_claimed=profile.total_billed_amount,
        profile_json=profile.dict(),
        risk_score=risk_score,
        summary=explanation
    )
    
    save_audit_flags(claim_id, flags)
    
    return get_claim_details(claim_id)

@app.get("/api/claims")
def list_claims():
    """Retrieves list of all claims with flags count and status."""
    return get_all_claims()

@app.get("/api/claims/{claim_id}")
def retrieve_claim(claim_id: str):
    """Retrieves full claim details."""
    claim = get_claim_details(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@app.post("/api/claims/{claim_id}/decision")
def submit_decision(claim_id: str, payload: AuditorDecisionInput):
    """Submits auditor decision, updating status and logging decision in immutable audit trail."""
    claim = get_claim_details(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    log_decision(
        claim_id=claim_id,
        auditor_id=payload.auditor_id,
        decision=payload.decision,
        comments=payload.comments
    )
    return {"message": f"Claim status successfully updated to {payload.decision}."}

# Mount data files and static frontend directories
os.makedirs("data", exist_ok=True)
app.mount("/data", StaticFiles(directory="data"), name="data")

# Create the frontend folder if not exists
os.makedirs("frontend", exist_ok=True)
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
import re # Make sure regex is imported for order checks
