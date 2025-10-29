# Requirements Document

**Project:** Bank Statement Analyzer API  
**Version:** 3.1.0-hexagonal  
**Last Updated:** 2025-10-28

## 1. Business Requirements

### 1.1 Functional Requirements
- **FR-001:** Mobile app uploads PDF bank statement to API
- **FR-002:** System extracts transactions from PDF (Thai language support)
- **FR-003:** System masks personal data (PDPA compliance)
- **FR-004:** System analyzes salary transactions with confidence scoring
- **FR-005:** API returns JSON response with analysis results
- **FR-006:** System stores original PDF in S3 bucket
- **FR-007:** System stores analysis results in PostgreSQL database
- **FR-008:** Support password-protected PDFs
- **FR-009:** Support Thai tax calculation (8 brackets)
- **FR-010:** Support SSO and PVD calculations
- **FR-011:** OCR payslip documents using dual-engine (Tesseract + Google Vision)
- **FR-012:** Extract salary data from payslip images/PDFs
- **FR-013:** Compare OCR results from multiple engines for validation
- **FR-014:** Save OCR text to file for audit/debugging

### 1.2 Non-Functional Requirements
- **NFR-001:** Response time < 2 seconds for 10-page PDF
- **NFR-002:** API availability > 99.5%
- **NFR-003:** Support 1000 concurrent requests
- **NFR-004:** All personal data must be encrypted (PDPA)
- **NFR-005:** Audit trail for all operations
- **NFR-006:** Docker containerization for all services
- **NFR-007:** Hexagonal Architecture for maintainability
- **NFR-008:** Support horizontal scaling
- **NFR-009:** OCR accuracy > 85% for Thai payslip documents
- **NFR-010:** Support both online (Google Vision) and offline (Tesseract) OCR

## 2. Technical Requirements

### 2.1 API Requirements
- **API-001:** RESTful API using FastAPI 0.115+
- **API-002:** Endpoint: POST /api/v1/analyze-upload (bank statements)
- **API-003:** Endpoint: POST /api/v1/analyze-statement-v2 (enhanced response)
- **API-004:** Endpoint: POST /api/v1/analyze-payslip (payslip OCR)
- **API-005:** Accept multipart/form-data (PDF file + parameters)
- **API-006:** Return JSON response with analysis results
- **API-007:** No file download for mobile (only JSON response)
- **API-008:** Support user_id, pdf_password, expected_gross, employer, pvd_rate parameters

### 2.2 Storage Requirements
- **STR-001:** S3 bucket for PDF storage (private, encrypted)
- **STR-002:** S3 region: ap-southeast-1 (Singapore)
- **STR-003:** S3 bucket: bank-statements-1761407671
- **STR-004:** PostgreSQL database for analysis results
- **STR-005:** Database tables: analyses, audit_logs (privacy-first design)
- **STR-006:** No transaction/statement details stored (only analysis results)
- **STR-007:** Separate S3 folder for payslip documents: payslips/{user_id}/
- **STR-008:** Save OCR text files to /app/tmp/ for debugging

### 2.3 Processing Requirements
- **PROC-001:** PDF extraction using PyMuPDF (Thai language support)
- **PROC-002:** Context-aware transaction parsing (3-line lookahead)
- **PROC-003:** PDPA masking: Thai ID, accounts, names, phones, emails, addresses
- **PROC-004:** Multi-factor salary scoring system
- **PROC-005:** Transaction clustering (±3% threshold)
- **PROC-006:** Thai progressive tax calculation
- **PROC-007:** Support KBANK, SCB, BBL, KTB, TMB statement formats
- **PROC-008:** Dual OCR: Tesseract + Google Cloud Vision API
- **PROC-009:** OCR result comparison and validation (agreement score)
- **PROC-010:** Support Thai and English language in payslip OCR

### 2.4 Security Requirements
- **SEC-001:** S3 bucket must be private (Block Public Access)
- **SEC-002:** S3 objects encrypted with AES256
- **SEC-003:** Database connections encrypted (SSL/TLS)
- **SEC-004:** Environment variables for secrets (no hardcoded credentials)
- **SEC-005:** API authentication (future: JWT tokens)
- **SEC-006:** Rate limiting (future: 100 req/min per user)
- **SEC-007:** Google Cloud credentials stored securely (service account JSON)
- **SEC-008:** OCR text files contain sensitive data - must be deleted after processing

### 2.5 Infrastructure Requirements
- **INF-001:** 3 Docker containers: web, api, db
- **INF-002:** Docker Compose for local development
- **INF-003:** PostgreSQL 15+ for database
- **INF-004:** Python 3.12+ for API
- **INF-005:** AWS credentials configured (~/.aws/config, ~/.aws/credentials)
- **INF-006:** Support deployment to AWS ECS/EC2
- **INF-007:** Tesseract OCR 5.x with tessdata-best language models
- **INF-008:** Google Cloud Vision API enabled and configured
- **INF-009:** poppler-utils for PDF to image conversion

### 2.6 OCR Requirements
- **OCR-001:** Tesseract OCR with tessdata-best (high accuracy models)
- **OCR-002:** Thai language support (tha.traineddata)
- **OCR-003:** English language support (eng.traineddata)
- **OCR-004:** Google Cloud Vision API for cloud-based OCR
- **OCR-005:** Dual-engine comparison with agreement score calculation
- **OCR-006:** Automatic engine selection based on confidence
- **OCR-007:** Pattern-based data extraction from OCR text
- **OCR-008:** Support for PDF and image formats (PNG, JPG)

## 3. Data Requirements

### 3.1 Input Data - Bank Statements
- PDF file (max 50MB)
- user_id (string, required)
- pdf_password (string, optional)
- expected_gross (float, optional)
- employer (string, optional)
- pvd_rate (float, 0.0-0.15, optional)

### 3.2 Input Data - Payslips
- PDF/Image file (max 10MB)
- user_id (string, required)
- upload_to_s3 (bool, default: true)
- save_ocr_text (bool, default: true)
- google_credentials_path (string, optional)

### 3.3 Output Data - Bank Statement Analysis
```json
{
  "success": true,
  "statement_id": "uuid",
  "user_id": "string",
  "timestamp": "20251025_123456",
  "statistics": {
    "total_transactions": 1278,
    "credit_transactions": 72,
    "debit_transactions": 1206,
    "masked_items": 33,
    "pages_processed": 17
  },
  "analysis": {
    "detected_amount": 65000.0,
    "confidence": "high|medium|low",
    "transactions_analyzed": 72,
    "clusters_found": 3,
    "matches_expected": true,
    "difference": 0.0
  }
}
```

### 3.4 Output Data - Payslip OCR
```json
{
  "success": true,
  "analysis_id": "uuid",
  "user_id": "string",
  "timestamp": "ISO8601",
  "payslip": {
    "salary": 50000.0,
    "net_salary": 42000.0,
    "employer_name": "ABC Company",
    "deductions": {
      "tax": 5000.0,
      "social_security": 750.0,
      "provident_fund": 2250.0,
      "total": 8000.0
    },
    "confidence": 0.95,
    "calculation_valid": true
  },
  "ocr_comparison": {
    "engines_used": ["tesseract", "vision"],
    "chosen_engine": "vision",
    "agreement_score": 0.92,
    "differences_count": 1
  },
  "pdf_storage_url": "s3://...",
  "ocr_text_file": "/tmp/..._payslip_ocr.txt",
  "processing_time_ms": 2500
}
```

### 3.5 Database Schema (Summary)
- **analyses**: analysis_id, user_id, detected_salary, confidence, transactions_analyzed, credit_transactions, debit_transactions, metadata (JSONB), created_at
- **audit_logs**: log_id, user_id, analysis_id, action, status, processing_time_ms, error_message, created_at

**Note:** Privacy-first design - no detailed transaction or statement data stored

## 4. Integration Requirements
- **INT-001:** AWS S3 SDK (boto3)
- **INT-002:** PostgreSQL client (psycopg2 or asyncpg)
- **INT-003:** PDF processing (PyMuPDF/fitz)
- **INT-004:** No external API calls for analysis (all local processing)
- **INT-005:** Google Cloud Vision API for payslip OCR
- **INT-006:** Tesseract OCR engine (local processing)
- **INT-007:** pdf2image library for PDF to image conversion

## 5. Acceptance Criteria
- **AC-001:** Mobile app uploads PDF → receives JSON response in < 2 seconds
- **AC-002:** PDPA masking covers all 6 pattern types
- **AC-003:** Salary detection accuracy > 85% for standard formats
- **AC-004:** System handles 1000 concurrent requests without errors
- **AC-005:** All services run in Docker containers
- **AC-006:** Zero downtime deployment capability
- **AC-007:** Payslip OCR accuracy > 85% for Thai documents
- **AC-008:** Dual OCR provides comparison metrics with agreement score
- **AC-009:** OCR text saved to file for audit purposes
- **AC-010:** Payslip PDFs uploaded to separate S3 folder

## 6. Out of Scope (Current Version)
- Real-time notifications
- Handwritten payslip recognition
- Multiple payslip pages in single request
- OCR for bank statements (only payslips)
- Multi-language support (only Thai/English)
- Mobile app development (API only)
- Admin dashboard (future: web service)
- Machine learning models (rule-based only)
- Batch processing (single file per request)

## 7. Assumptions
- Mobile app handles PDF capture/selection
- Users have valid Thai bank statements
- PDF files are text-based (not scanned images)
- Network connectivity to AWS S3
- PostgreSQL accessible from API container
