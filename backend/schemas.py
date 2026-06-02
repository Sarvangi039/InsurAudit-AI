from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ItemizedCharge(BaseModel):
    description: str
    unit_rate: Optional[float] = 0.0
    quantity: Optional[int] = 1
    amount: float

class ClaimProfile(BaseModel):
    """The canonical schema representing a merged, validated claim profile."""
    # Identity Information
    patient_name: Optional[str] = Field(default=None, description="Cleaned full name of the patient")
    policy_number: Optional[str] = Field(default=None, description="Health insurance policy number")
    policyholder_name: Optional[str] = Field(default=None, description="Name of primary policyholder")
    patient_dob: Optional[str] = Field(default=None, description="Date of birth of the patient (YYYY-MM-DD)")
    patient_id_number: Optional[str] = Field(default=None, description="Government or national ID number")
    
    # Dates & Stay Information
    admission_date: Optional[str] = Field(default=None, description="Date of admission (YYYY-MM-DD)")
    discharge_date: Optional[str] = Field(default=None, description="Date of discharge (YYYY-MM-DD)")
    length_of_stay: Optional[int] = Field(default=None, description="Calculated duration of stay in days")
    
    # Medical details
    diagnosis: Optional[str] = Field(default=None, description="Diagnosis text or description")
    icd_codes: List[str] = Field(default_factory=list, description="Extracted ICD-10 medical codes")
    procedures: List[str] = Field(default_factory=list, description="Treatments, operations, or procedures performed")
    attending_doctor: Optional[str] = Field(default=None, description="Attending physician's name")
    doctor_registration: Optional[str] = Field(default=None, description="Medical registration number of the doctor")
    hospital_name: Optional[str] = Field(default=None, description="Name of the treating hospital")
    hospital_registration: Optional[str] = Field(default=None, description="Hospital's business/medical registration number")
    hospital_tier: Optional[str] = Field(default="non-NABH", description="Tier or registration class (e.g., NABH, non-NABH)")
    
    # Policy Parameters (from policy doc if present)
    policy_start_date: Optional[str] = Field(default=None, description="Start date of policy coverage (YYYY-MM-DD)")
    policy_end_date: Optional[str] = Field(default=None, description="End date of policy coverage (YYYY-MM-DD)")
    policy_sum_insured: Optional[float] = Field(default=None, description="Total cover limit of the policy")
    policy_room_rent_limit: Optional[float] = Field(default=None, description="Daily limit for room charges in the policy")
    
    # Billing breakdown
    room_charges_total: Optional[float] = Field(default=0.0, description="Total room rent charges")
    icu_charges_total: Optional[float] = Field(default=0.0, description="Total ICU stay charges")
    pharmacy_charges_total: Optional[float] = Field(default=0.0, description="Total pharmacy/medication charges")
    investigation_charges_total: Optional[float] = Field(default=0.0, description="Total laboratory/diagnostic charges")
    consultation_charges_total: Optional[float] = Field(default=0.0, description="Total doctor consultation charges")
    other_charges_total: Optional[float] = Field(default=0.0, description="Other miscellaneous hospital charges")
    total_billed_amount: Optional[float] = Field(default=0.0, description="Invoice summary total claimed")
    
    # Itemized details
    itemized_charges: List[ItemizedCharge] = Field(default_factory=list, description="Line item details from hospital bills")
    medicines_prescribed: List[str] = Field(default_factory=list, description="Medicines list extracted from prescriptions")

# API Models

class ClaimUpdateInput(BaseModel):
    """Fields that can be updated/corrected manually by the human auditor."""
    patient_name: Optional[str] = None
    policy_number: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    total_billed_amount: Optional[float] = None
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    doctor_registration: Optional[str] = None
    policy_room_rent_limit: Optional[float] = None
    policy_start_date: Optional[str] = None
    policy_end_date: Optional[str] = None

class AuditorDecisionInput(BaseModel):
    auditor_id: str
    decision: str  # 'Approved', 'Rejected', 'Queried'
    comments: str

class AuditFlagSchema(BaseModel):
    rule_id: str
    category: str
    severity: str  # 'LOW', 'MED', 'HIGH', 'CRITICAL'
    message: str
    evidence: Optional[str] = ""

class ClaimResponse(BaseModel):
    id: str
    patient_name: Optional[str]
    policy_number: Optional[str]
    admission_date: Optional[str]
    discharge_date: Optional[str]
    total_claimed: float
    total_approved: Optional[float]
    risk_score: int
    status: str
    summary: Optional[str]
    created_at: str
    updated_at: str
    doc_count: int
    flag_count: int
    profile: Dict[str, Any]
