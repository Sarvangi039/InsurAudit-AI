import os
import sys
import subprocess

def check_and_install_dependencies():
    """Checks if packages are installed, and installs them if missing."""
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "fitz": "pymupdf",
        "pydantic": "pydantic",
        "multipart": "python-multipart",
        "dotenv": "python-dotenv",
        "google.generativeai": "google-generativeai"
    }
    
    missing_packages = []
    for module_name, pip_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            missing_packages.append(pip_name)
            
    if missing_packages:
        print(f"[INFO] Missing dependencies found: {', '.join(missing_packages)}")
        print("[INFO] Installing requirements via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_packages])
            print("[SUCCESS] Dependencies successfully installed!")
        except Exception as e:
            print(f"[ERROR] Error installing dependencies: {e}")
            print("Please manually run: pip install -r requirements.txt")
            sys.exit(1)
    else:
        print("[SUCCESS] All Python dependencies are present.")

def main():
    print("=" * 60)
    print("        INSURAUDIT.AI - CLAIMS DOCUMENT AUDITOR MVP        ")
    print("=" * 60)
    
    # 1. Check/Install dependencies
    check_and_install_dependencies()
    
    # 2. Setup folders
    print("[SETUP] Setting up database and upload folders...")
    os.makedirs(os.path.join("data", "uploads"), exist_ok=True)
    os.makedirs(os.path.join("data", "processed"), exist_ok=True)
    os.makedirs("samples", exist_ok=True)
    
    # 3. Check for API Key
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("\n[CONFIG] Checking Gemini API Configuration...")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("[WARNING] GEMINI_API_KEY is not configured in .env.")
        print("  - You can paste your API key in the 'Settings' panel on the web UI dashboard,")
        print("    or set GEMINI_API_KEY in your .env file to enable vision OCR.")
        print("  - Pipeline processing will fallback to MOCK data mode if no key is supplied.")
    else:
        print("[SUCCESS] GEMINI_API_KEY is configured!")
        
    print("\n[SERVER] Launching FastAPI backend server on http://127.0.0.1:8000...")
    print("[SERVER] Press Ctrl+C to terminate the server.\n")
    
    # 4. Start Uvicorn
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
