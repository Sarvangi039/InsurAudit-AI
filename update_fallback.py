import os

file_path = "d:/7th sem/summer internship/OCR/backend/pipeline.py"

with open(file_path, "r") as f:
    content = f.read()

# 1. Add groq import
if "import groq" not in content:
    content = content.replace("import google.generativeai as genai", "import google.generativeai as genai\nimport groq")

# 2. Update config loading
old_config = """# Configure Google Generative AI
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY and API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=API_KEY)
else:
    # We will still allow the app to run and show a configuration warning
    print("WARNING: GEMINI_API_KEY not configured or is placeholder. AI steps will be mocked/bypassed.")"""

new_config = """# Configure Google Generative AI & Fallbacks
API_KEY_1 = os.getenv("GEMINI_API_KEY_1")
API_KEY_2 = os.getenv("GEMINI_API_KEY_2")
GROK_API_KEY = os.getenv("GROK_API_KEY")

if not API_KEY_1 and not API_KEY_2 and not GROK_API_KEY:
    print("WARNING: No API keys configured. AI steps will be mocked/bypassed.")

def call_ai_with_fallback(prompt: str, expect_json: bool = True) -> str:
    \"\"\"Rotates through GEMINI_API_KEY_1, GEMINI_API_KEY_2, and GROK_API_KEY.\"\"\"
    errors = []
    
    # Attempt 1: Gemini Key 1
    if API_KEY_1 and API_KEY_1 != "your_gemini_api_key_here":
        try:
            genai.configure(api_key=API_KEY_1)
            model = genai.GenerativeModel("gemini-2.5-flash")
            config = {"response_mime_type": "application/json"} if expect_json else None
            response = model.generate_content(prompt, generation_config=config)
            return response.text
        except Exception as e:
            err_str = str(e).lower()
            errors.append(f"Gemini 1 Error: {e}")
            if "429" not in err_str and "quota" not in err_str:
                raise e # Not a rate limit, raise it
                
    # Attempt 2: Gemini Key 2
    if API_KEY_2 and API_KEY_2 != "your_gemini_api_key_here":
        try:
            print("Fallback: Trying Gemini API Key 2...")
            genai.configure(api_key=API_KEY_2)
            model = genai.GenerativeModel("gemini-2.5-flash")
            config = {"response_mime_type": "application/json"} if expect_json else None
            response = model.generate_content(prompt, generation_config=config)
            return response.text
        except Exception as e:
            err_str = str(e).lower()
            errors.append(f"Gemini 2 Error: {e}")
            if "429" not in err_str and "quota" not in err_str:
                raise e
                
    # Attempt 3: Groq (Llama-3)
    if GROK_API_KEY and GROK_API_KEY != "your_grok_api_key_here":
        try:
            print("Fallback: Trying Groq Llama 3 70B...")
            client = groq.Groq(api_key=GROK_API_KEY)
            
            completion_kwargs = {
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
            if expect_json:
                completion_kwargs["response_format"] = {"type": "json_object"}
                
            completion = client.chat.completions.create(**completion_kwargs)
            return completion.choices[0].message.content
        except Exception as e:
            errors.append(f"Groq Error: {e}")
            
    # If we get here, all attempts failed
    raise Exception(f"All API fallback attempts failed: {errors}")"""

content = content.replace(old_config, new_config)

# 3. Update extract_structured_data_from_text
old_extract = """def extract_structured_data_from_text(text: str) -> dict:
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
        return get_mock_extraction("mock.pdf")"""

new_extract = """def extract_structured_data_from_text(text: str) -> dict:
    \"\"\"Calls AI with raw text instead of images to extract structured fields in JSON.\"\"\"
    if not API_KEY_1 and not API_KEY_2 and not GROK_API_KEY:
        from backend.pipeline import get_mock_extraction
        return get_mock_extraction("mock.pdf")
        
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
    
    try:
        response_text = call_ai_with_fallback(prompt, expect_json=True)
        data = json.loads(response_text)
        return data
    except Exception as e:
        print(f"AI API error during text extraction: {e}")
        from backend.pipeline import get_mock_extraction
        return get_mock_extraction("mock.pdf")"""

content = content.replace(old_extract, new_extract)

# 4. Update generate_ai_explanation
old_generate = """def generate_ai_explanation(profile: ClaimProfile, flags: list, risk_score: int, api_key: str = None) -> str:
    \"\"\"Uses Gemini to synthesize a 3-5 sentence audit summary of flags and details for the auditor.\"\"\"
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
            flags_text += f"{i+1}. [{f['severity']}] {f['category']} - {f['message']} (Evidence: {f.get('evidence')})\\n"
            
        prompt = f\"\"\"
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
        \"\"\"
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Gemini API error during summary generation: {e}")
        return get_mock_explanation(profile, flags, risk_score)"""

new_generate = """def generate_ai_explanation(profile: ClaimProfile, flags: list, risk_score: int) -> str:
    \"\"\"Uses AI to synthesize a 3-5 sentence audit summary of flags and details for the auditor.\"\"\"
    if not API_KEY_1 and not API_KEY_2 and not GROK_API_KEY:
        return get_mock_explanation(profile, flags, risk_score)
        
    flags_text = ""
    for i, f in enumerate(flags):
        flags_text += f"{i+1}. [{f['severity']}] {f['category']} - {f['message']} (Evidence: {f.get('evidence')})\\n"
        
    prompt = f\"\"\"
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
    \"\"\"
    
    try:
        response_text = call_ai_with_fallback(prompt, expect_json=False)
        return response_text.strip()
    except Exception as e:
        print(f"AI API error during summary generation: {e}")
        return get_mock_explanation(profile, flags, risk_score)"""

content = content.replace(old_generate, new_generate)

with open(file_path, "w") as f:
    f.write(content)

print("backend/pipeline.py successfully updated with fallback routing.")
