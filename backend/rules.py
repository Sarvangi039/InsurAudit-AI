import re
import difflib
from datetime import datetime
from typing import List, Dict, Any
from backend.schemas import ClaimProfile

# Mock Blacklists for Fraud Detection
FRAUDULENT_HOSPITALS = [
    "apex healthcare clinic", 
    "fake city hospital", 
    "metro health center trust",
    "shanti nursing home (blacklisted)"
]

FRAUDULENT_DOCTORS = [
    "dr. john quack",
    "dr. fraudster",
    "dr. fake name"
]

def fuzzy_string_match(str1: str, str2: str) -> float:
    """Calculates the similarity ratio between two strings."""
    if not str1 or not str2:
        return 0.0
    str1 = str1.strip().lower()
    str2 = str2.strip().lower()
    # Remove common prefixes/suffixes
    str1 = re.sub(r'^(mr\.|ms\.|mrs\.|dr\.)\s+', '', str1)
    str2 = re.sub(r'^(mr\.|ms\.|mrs\.|dr\.)\s+', '', str2)
    return difflib.SequenceMatcher(None, str1, str2).ratio()

def parse_date(date_str: str) -> datetime:
    """Safely parses standard ISO date format."""
    if not date_str:
        return None
    try:
        # Support both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS
        clean_date = date_str.split("T")[0]
        return datetime.strptime(clean_date, "%Y-%m-%d")
    except Exception:
        return None

def run_audit_rules(profile: ClaimProfile, document_extractions: list) -> List[Dict[str, Any]]:
    """Runs a suite of deterministic audit rules against the claim profile and document extractions."""
    flags = []

    # ==========================================
    # 1. IDENTITY CHECKS
    # ==========================================

    # Rule: Patient name consistency across all extracted documents
    main_name = profile.patient_name
    if main_name:
        for doc in document_extractions:
            doc_fields = doc.get("extracted_fields", {})
            doc_name = doc_fields.get("patient_name")
            doc_type = doc.get("document_type", "Document")
            
            if doc_name and doc_type != "Policy document":
                similarity = fuzzy_string_match(main_name, doc_name)
                if 0.0 < similarity < 0.85:
                    flags.append({
                        "rule_id": "ID_NAME_CONSISTENCY",
                        "category": "Identity",
                        "severity": "HIGH",
                        "message": f"Patient name mismatch between profile ({main_name}) and {doc_type} ({doc_name}). Similarity score: {similarity:.2f}",
                        "evidence": f"Main: {main_name} vs {doc_type}: {doc_name}"
                    })

    # Rule: Policy eligibility on admission
    if profile.admission_date and profile.policy_start_date and profile.policy_end_date:
        ad = parse_date(profile.admission_date)
        ps = parse_date(profile.policy_start_date)
        pe = parse_date(profile.policy_end_date)
        
        if ad and ps and pe:
            if ad < ps or ad > pe:
                flags.append({
                    "rule_id": "ID_POLICY_ELIGIBILITY",
                    "category": "Identity",
                    "severity": "CRITICAL",
                    "message": f"Treatment admission date ({profile.admission_date}) is outside active policy period ({profile.policy_start_date} to {profile.policy_end_date}).",
                    "evidence": f"Admission: {profile.admission_date} (Policy: {profile.policy_start_date} to {profile.policy_end_date})"
                })

    # Rule: ID-to-policy linkage name verification
    # Find ID Proof doc
    id_name = None
    for doc in document_extractions:
        if doc.get("document_type") == "ID proof":
            id_name = doc.get("extracted_fields", {}).get("patient_name")
            break
            
    if id_name and profile.policyholder_name:
        similarity = fuzzy_string_match(id_name, profile.policyholder_name)
        if 0.0 < similarity < 0.85:
            flags.append({
                "rule_id": "ID_POLICY_LINKAGE",
                "category": "Identity",
                "severity": "HIGH",
                "message": f"Patient identity proof name ({id_name}) does not match Policyholder record name ({profile.policyholder_name}).",
                "evidence": f"ID Proof: {id_name} vs Policy: {profile.policyholder_name}"
            })

    # Rule: Doctor registration format check
    if profile.doctor_registration:
        # Standard registration numbers should be alphanumeric and not extremely short
        reg_num = profile.doctor_registration.strip()
        if len(reg_num) < 3 or not re.search(r'\d', reg_num):
            flags.append({
                "rule_id": "ID_DOCTOR_REGISTRATION",
                "category": "Identity",
                "severity": "MED",
                "message": f"Doctor registration number '{profile.doctor_registration}' seems invalid or empty.",
                "evidence": f"Doctor Registration: {profile.doctor_registration}"
            })
    else:
        flags.append({
            "rule_id": "ID_DOCTOR_REGISTRATION_MISSING",
            "category": "Identity",
            "severity": "MED",
            "message": "No doctor registration number extracted from bills, prescriptions, or discharge summaries.",
            "evidence": "doctor_registration field is null"
        })


    # ==========================================
    # 2. DATE & TIMELINE CHECKS
    # ==========================================

    # Rule: Admission date <= discharge date
    if profile.admission_date and profile.discharge_date:
        ad = parse_date(profile.admission_date)
        dd = parse_date(profile.discharge_date)
        
        if ad and dd:
            if ad > dd:
                flags.append({
                    "rule_id": "DATE_ADMISSION_BEFORE_DISCHARGE",
                    "category": "Date & Timeline",
                    "severity": "CRITICAL",
                    "message": f"Critical date logic error: Admission date ({profile.admission_date}) is after discharge date ({profile.discharge_date}).",
                    "evidence": f"Admission: {profile.admission_date} > Discharge: {profile.discharge_date}"
                })
            
            # Rule: Length of stay plausibility vs diagnosis
            los = (dd - ad).days
            diagnosis = (profile.diagnosis or "").lower()
            
            # Check for appendectomy / appendicitis
            if "append" in diagnosis and los > 4:
                flags.append({
                    "rule_id": "DATE_LOS_PLAUSIBILITY",
                    "category": "Date & Timeline",
                    "severity": "MED",
                    "message": f"Length of stay ({los} days) is high for laparoscopic appendectomy procedure, which typically requires 1-3 days.",
                    "evidence": f"LOS: {los} days for diagnosis: {profile.diagnosis}"
                })
            # Check for cataract
            elif "cataract" in diagnosis and los > 1:
                flags.append({
                    "rule_id": "DATE_LOS_PLAUSIBILITY",
                    "category": "Date & Timeline",
                    "severity": "MED",
                    "message": f"Length of stay ({los} days) is excessive for cataract surgery, which is typically a daycare procedure (0-1 days).",
                    "evidence": f"LOS: {los} days for diagnosis: {profile.diagnosis}"
                })
            # Exceptionally long stays (> 30 days) should trigger warning
            elif los > 30:
                flags.append({
                    "rule_id": "DATE_LOS_EXCESSIVE",
                    "category": "Date & Timeline",
                    "severity": "HIGH",
                    "message": f"Length of stay ({los} days) is exceptionally high. Requires manual validation of ICU sheets and case sheets.",
                    "evidence": f"LOS: {los} days"
                })

    # Rule: Prescription Date Alignment
    # Check if prescription dates match the stay window (should be before or within stay)
    for doc in document_extractions:
        if doc.get("document_type") == "Prescription":
            pres_date_str = doc.get("extracted_fields", {}).get("date")
            if pres_date_str and profile.admission_date:
                pd = parse_date(pres_date_str)
                ad = parse_date(profile.admission_date)
                dd = parse_date(profile.discharge_date) if profile.discharge_date else ad
                
                if pd and ad and dd:
                    # Allow prescription to be up to 7 days before admission
                    days_before = (ad - pd).days
                    days_after = (pd - dd).days
                    if days_before > 7 or days_after > 1:
                        flags.append({
                            "rule_id": "DATE_PRESCRIPTION_ALIGNMENT",
                            "category": "Date & Timeline",
                            "severity": "MED",
                            "message": f"Prescription date ({pres_date_str}) is not aligned with hospital admission timeline ({profile.admission_date} to {profile.discharge_date}).",
                            "evidence": f"Prescription Date: {pres_date_str} vs Stay: {profile.admission_date} to {profile.discharge_date}"
                        })


    # ==========================================
    # 3. BILLING CHECKS
    # ==========================================

    # Rule: Duplicate bill line item detection
    if profile.itemized_charges:
        seen_items = {}
        for item in profile.itemized_charges:
            key = (item.description.strip().lower(), item.amount)
            if key in seen_items:
                seen_items[key] += 1
            else:
                seen_items[key] = 1
                
        duplicates = [desc for (desc, amt), count in seen_items.items() if count > 1]
        if duplicates:
            flags.append({
                "rule_id": "BILL_DUPLICATE_ITEMS",
                "category": "Billing",
                "severity": "CRITICAL",
                "message": f"Duplicate line items detected in hospital bill: {', '.join(duplicates[:2])} appeared multiple times with identical descriptions and amounts.",
                "evidence": f"Duplicates: {duplicates}"
            })

    # Rule: Itemized sum vs total billed mismatch
    if profile.itemized_charges and profile.total_billed_amount > 0:
        sum_items = sum(item.amount for item in profile.itemized_charges)
        mismatch_pct = abs(sum_items - profile.total_billed_amount) / profile.total_billed_amount
        
        if mismatch_pct > 0.01:  # More than 1% mismatch
            flags.append({
                "rule_id": "BILL_SUM_MISMATCH",
                "category": "Billing",
                "severity": "HIGH",
                "message": f"Hospital bill summary total (Rs. {profile.total_billed_amount:,.2f}) does not match the sum of itemized charges (Rs. {sum_items:,.2f}). Mismatch of {mismatch_pct*100:.1f}%.",
                "evidence": f"Billed Total: {profile.total_billed_amount} vs Itemized Sum: {sum_items}"
            })

    # Rule: Room rent limits breach
    # Standard check: if policy room rent limit is present and actual room rate exceeds it
    if profile.room_charges_total and profile.length_of_stay and profile.length_of_stay > 0:
        actual_room_rate = profile.room_charges_total / profile.length_of_stay
        if profile.policy_room_rent_limit and actual_room_rate > profile.policy_room_rent_limit:
            flags.append({
                "rule_id": "BILL_ROOM_RENT_LIMIT_EXCEEDED",
                "category": "Billing",
                "severity": "HIGH",
                "message": f"Daily room rent rate (Rs. {actual_room_rate:,.2f}) exceeds policy daily allowance limit (Rs. {profile.policy_room_rent_limit:,.2f}).",
                "evidence": f"Actual daily rate: Rs. {actual_room_rate:,.2f} vs Policy Limit: Rs. {profile.policy_room_rent_limit:,.2f}"
            })


    # ==========================================
    # 4. FRAUD INDICATORS
    # ==========================================

    # Rule: Known fraudulent/blacklisted provider list
    if profile.hospital_name:
        hname = profile.hospital_name.lower().strip()
        for b_hospital in FRAUDULENT_HOSPITALS:
            if b_hospital in hname or fuzzy_string_match(hname, b_hospital) > 0.85:
                flags.append({
                    "rule_id": "FRAUD_BLACKLIST_PROVIDER",
                    "category": "Fraud",
                    "severity": "CRITICAL",
                    "message": f"Hospital '{profile.hospital_name}' matches a known blacklisted/high-risk healthcare provider list.",
                    "evidence": f"Matched hospital: {profile.hospital_name} against blacklist"
                })
                break

    # Rule: Known fraudulent/blacklisted doctor list
    if profile.attending_doctor:
        dname = profile.attending_doctor.lower().strip()
        for b_doc in FRAUDULENT_DOCTORS:
            if b_doc in dname or fuzzy_string_match(dname, b_doc) > 0.85:
                flags.append({
                    "rule_id": "FRAUD_BLACKLIST_DOCTOR",
                    "category": "Fraud",
                    "severity": "CRITICAL",
                    "message": f"Attending Physician '{profile.attending_doctor}' matches a known blacklisted/suspicious medical practitioner registry.",
                    "evidence": f"Matched doctor: {profile.attending_doctor} against blacklist"
                })
                break

    # Rule: Round-number billing checks
    total_val = profile.total_billed_amount
    if total_val > 0:
        # Check if the number ends with multiple zeros, e.g., 50000, 100000, 150000
        if total_val % 10000 == 0:
            flags.append({
                "rule_id": "FRAUD_ROUND_BILLING",
                "category": "Fraud",
                "severity": "LOW",
                "message": f"Suspiciously round claimed billing amount (Rs. {total_val:,.2f}). Medical claims are rarely exact multiples of 10,000.",
                "evidence": f"Claimed total: {total_val}"
            })

    # Rule: Impossible Length of Stay (LOS) / Negative Stay
    if profile.admission_date and profile.discharge_date:
        ad = parse_date(profile.admission_date)
        dd = parse_date(profile.discharge_date)
        if ad and dd:
            los = (dd - ad).days
            if los < 0 or los > 365:
                flags.append({
                    "rule_id": "FRAUD_IMPOSSIBLE_LOS",
                    "category": "Fraud",
                    "severity": "CRITICAL",
                    "message": f"Impossible length of stay ({los} days). Discharge date cannot occur before admission, and stays exceeding 365 days are flag indicators.",
                    "evidence": f"LOS calculated: {los} days"
                })

    return flags

def calculate_risk_score(flags: list) -> int:
    """Calculates a composite risk score (0-100) based on weighted flags."""
    if not flags:
        return 0
        
    severity_weights = {
        "CRITICAL": 45,
        "HIGH": 25,
        "MED": 12,
        "LOW": 5
    }
    
    score = 0
    # De-duplicate rule counts to prevent double-penalizing the same rule trigger type
    triggered_rules = set()
    
    for flag in flags:
        rule_id = flag.get("rule_id")
        severity = flag.get("severity", "LOW")
        
        if rule_id not in triggered_rules:
            triggered_rules.add(rule_id)
            score += severity_weights.get(severity, 5)
            
    # Cap score at 100
    return min(score, 100)
