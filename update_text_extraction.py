import re

def update_pipeline():
    with open('d:/7th sem/summer internship/OCR/backend/pipeline.py', 'r') as f:
        content = f.read()
    
    new_functions = """
def extract_text_locally(file_path: str) -> str:
    \"\"\"Extracts raw text from a PDF or image file locally using PyMuPDF.\"\"\"
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\\n"
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
    return text.strip()

def extract_structured_data_from_text(text: str) -> dict:
    \"\"\"Calls Gemini with raw text instead of images to extract structured fields in JSON.\"\"\"
    if not API_KEY or API_KEY == "your_gemini_api_key_here":
        return get_mock_extraction("mock.pdf")
        
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f\"\"\"
        Analyze this document text and return a JSON object with:
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
           - Itemized charges list (itemized_charges) - list of objects with {{"description": str, "unit_rate": float, "quantity": int, "amount": float}}
           - Medicines prescribed (medicines_prescribed) - list of strings
        4. "raw_ocr_summary": A brief text summary of key paragraphs/text for keyword search.

        Return ONLY a raw JSON object matching this schema. Do not enclose it in markdown ```json blocks.
        
        Document Text to Analyze:
        '''
        {text}
        '''
        \"\"\"
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        data = json.loads(response.text)
        return data
        
    except Exception as e:
        print(f"Gemini API error during text extraction: {e}")
        from backend.pipeline import get_mock_extraction
        return get_mock_extraction("mock.pdf")
"""
    
    content = content.replace("def merge_document_profiles(documents_data: list) -> ClaimProfile:", new_functions + "\\ndef merge_document_profiles(documents_data: list) -> ClaimProfile:")
    
    with open('d:/7th sem/summer internship/OCR/backend/pipeline.py', 'w') as f:
        f.write(content)
        
    print("pipeline.py updated successfully")

def update_main():
    with open('d:/7th sem/summer internship/OCR/backend/main.py', 'r') as f:
        content = f.read()
    
    content = content.replace("from backend.pipeline import (", "from backend.pipeline import (\\n    extract_text_locally, extract_structured_data_from_text,")
    
    old_loop = \"\"\"        # Gather all pages for this document
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
            page_result = extract_structured_data(page_path)
            
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
        combined_ocr = "\\n--- PAGE BREAK ---\\n".join(doc_ocr_text)\"\"\"
        
    new_loop = \"\"\"        
        # 1. Extract text locally from the original document
        doc_ocr_text = extract_text_locally(file_path)
        
        doc_type = "Unknown"
        doc_confidence = 1.0
        doc_extracted_fields = {}
        combined_ocr = ""
        
        if doc_ocr_text:
            # 2. If we found text, make 1 single API call to Gemini with the full text payload
            page_result = extract_structured_data_from_text(doc_ocr_text)
            
            # Aggregate text and fields
            combined_ocr = page_result.get("raw_ocr_summary", doc_ocr_text[:500] + "...")
            doc_type = page_result.get("document_type", "Unknown")
            doc_confidence = page_result.get("confidence", 1.0)
            doc_extracted_fields = page_result.get("extracted_fields", {})
            
        else:
            # 3. Fallback: No local text found (image or scanned PDF). 
            print(f"No text extracted locally for {file_path}. Skipping image upload to save tokens.")
            from backend.pipeline import get_mock_extraction
            mock = get_mock_extraction(file_path)
            
            combined_ocr = "No text found locally. Direct image API upload disabled by user to save quotas. Fallback mock used."
            doc_type = mock.get("document_type", "Unknown")
            doc_confidence = mock.get("confidence", 0.5)
            doc_extracted_fields = mock.get("extracted_fields", {})
            
        # Clean list duplicates if list of codes, procedures, etc.
        for k in ["icd_codes", "procedures", "medicines_prescribed"]:
            if k in doc_extracted_fields and isinstance(doc_extracted_fields[k], list):
                doc_extracted_fields[k] = list(set(doc_extracted_fields[k]))\"\"\"

    if old_loop in content:
        content = content.replace(old_loop, new_loop)
        with open('d:/7th sem/summer internship/OCR/backend/main.py', 'w') as f:
            f.write(content)
        print("main.py updated successfully")
    else:
        print("Could not find loop pattern in main.py")

update_pipeline()
update_main()
