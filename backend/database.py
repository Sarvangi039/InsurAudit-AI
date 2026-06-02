import sqlite3
import json
import os
from datetime import datetime

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DB_PATH = os.path.join(DB_DIR, "claims.db")

def get_db_connection():
    """Establishes a thread-safe connection to the SQLite database."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Claims table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            patient_name TEXT,
            policy_number TEXT,
            admission_date TEXT,
            discharge_date TEXT,
            total_claimed REAL,
            total_approved REAL,
            risk_score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            summary TEXT,
            profile_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # 2. Documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            claim_id TEXT,
            file_name TEXT,
            file_path TEXT,
            doc_type TEXT,
            confidence REAL,
            ocr_text TEXT,
            pages_count INTEGER,
            created_at TEXT,
            FOREIGN KEY (claim_id) REFERENCES claims (id) ON DELETE CASCADE
        )
    """)
    
    # 3. Audit flags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT,
            rule_id TEXT,
            category TEXT,
            severity TEXT,
            message TEXT,
            evidence TEXT,
            FOREIGN KEY (claim_id) REFERENCES claims (id) ON DELETE CASCADE
        )
    """)
    
    # 4. Audit decisions table (immutable log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT,
            auditor_id TEXT,
            decision TEXT,
            comments TEXT,
            timestamp TEXT,
            FOREIGN KEY (claim_id) REFERENCES claims (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

# Claim CRUD operations

def create_claim(claim_id: str, patient_name: str = None, policy_number: str = None, 
                 admission_date: str = None, discharge_date: str = None, 
                 total_claimed: float = 0.0):
    """Inserts a new claim skeleton into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO claims (id, patient_name, policy_number, admission_date, discharge_date, total_claimed, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
    """, (claim_id, patient_name, policy_number, admission_date, discharge_date, total_claimed, now_str, now_str))
    
    conn.commit()
    conn.close()

def update_claim_profile(claim_id: str, patient_name: str, policy_number: str, 
                         admission_date: str, discharge_date: str, total_claimed: float, 
                         profile_json: dict, risk_score: int, summary: str):
    """Updates a claim with full processed results."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    cursor.execute("""
        UPDATE claims
        SET patient_name = ?,
            policy_number = ?,
            admission_date = ?,
            discharge_date = ?,
            total_claimed = ?,
            profile_json = ?,
            risk_score = ?,
            summary = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        patient_name, policy_number, admission_date, discharge_date, total_claimed,
        json.dumps(profile_json), risk_score, summary, now_str, claim_id
    ))
    
    conn.commit()
    conn.close()

def update_claim_status(claim_id: str, status: str):
    """Updates the decision status of a claim."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    cursor.execute("""
        UPDATE claims
        SET status = ?, updated_at = ?
        WHERE id = ?
    """, (status, now_str, claim_id))
    
    conn.commit()
    conn.close()

def add_document(doc_id: str, claim_id: str, file_name: str, file_path: str, 
                 doc_type: str = "Unknown", confidence: float = 1.0, 
                 ocr_text: str = "", pages_count: int = 1):
    """Adds a document to a claim bundle."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO documents (id, claim_id, file_name, file_path, doc_type, confidence, ocr_text, pages_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, claim_id, file_name, file_path, doc_type, confidence, ocr_text, pages_count, now_str))
    
    conn.commit()
    conn.close()

def update_document_details(doc_id: str, doc_type: str, confidence: float, ocr_text: str):
    """Updates OCR and classification details of a document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE documents
        SET doc_type = ?, confidence = ?, ocr_text = ?
        WHERE id = ?
    """, (doc_type, confidence, ocr_text, doc_id))
    
    conn.commit()
    conn.close()

def save_audit_flags(claim_id: str, flags: list):
    """Deletes existing flags for a claim and inserts new ones."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clean previous audit flags
    cursor.execute("DELETE FROM audit_flags WHERE claim_id = ?", (claim_id,))
    
    # Insert new flags
    for flag in flags:
        cursor.execute("""
            INSERT INTO audit_flags (claim_id, rule_id, category, severity, message, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            claim_id, 
            flag.get("rule_id"), 
            flag.get("category"), 
            flag.get("severity"), 
            flag.get("message"), 
            flag.get("evidence", "")
        ))
        
    conn.commit()
    conn.close()

def log_decision(claim_id: str, auditor_id: str, decision: str, comments: str):
    """Saves a decision entry to the immutable decisions log and updates the claim status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    # 1. Add log entry
    cursor.execute("""
        INSERT INTO audit_decisions (claim_id, auditor_id, decision, comments, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (claim_id, auditor_id, decision, comments, now_str))
    
    # 2. Update claim status
    cursor.execute("""
        UPDATE claims
        SET status = ?, updated_at = ?
        WHERE id = ?
    """, (decision, now_str, claim_id))
    
    conn.commit()
    conn.close()

# Retrieval operations

def get_all_claims():
    """Retrieves all claims sorted by creation date descending."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM documents WHERE claim_id = c.id) as doc_count,
               (SELECT COUNT(*) FROM audit_flags WHERE claim_id = c.id) as flag_count
        FROM claims c
        ORDER BY c.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    claims = []
    for row in rows:
        d = dict(row)
        if d["profile_json"]:
            try:
                d["profile"] = json.loads(d["profile_json"])
            except:
                d["profile"] = {}
        else:
            d["profile"] = {}
        claims.append(d)
    return claims

def get_claim_details(claim_id: str):
    """Retrieves a single claim with its documents, flags, and decision history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch claim metadata
    cursor.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
    claim_row = cursor.fetchone()
    if not claim_row:
        conn.close()
        return None
        
    claim = dict(claim_row)
    if claim["profile_json"]:
        try:
            claim["profile"] = json.loads(claim["profile_json"])
        except:
            claim["profile"] = {}
    else:
        claim["profile"] = {}
        
    # Fetch documents
    cursor.execute("SELECT id, file_name, file_path, doc_type, confidence, ocr_text, pages_count, created_at FROM documents WHERE claim_id = ?", (claim_id,))
    claim["documents"] = [dict(r) for r in cursor.fetchall()]
    
    # Fetch audit flags
    cursor.execute("SELECT rule_id, category, severity, message, evidence FROM audit_flags WHERE claim_id = ?", (claim_id,))
    claim["flags"] = [dict(r) for r in cursor.fetchall()]
    
    # Fetch decision history
    cursor.execute("SELECT auditor_id, decision, comments, timestamp FROM audit_decisions WHERE claim_id = ? ORDER BY timestamp DESC", (claim_id,))
    claim["decisions"] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return claim
