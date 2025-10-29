# System Design Document

**Project:** Bank Statement Analyzer API  
**Version:** 3.0.0-hexagonal  
**Last Updated:** 2025-10-25

## 1. Architecture Overview

### 1.1 High-Level Architecture
```
┌─────────────┐
│ Mobile App  │
└──────┬──────┘
       │ HTTPS
       ↓
┌──────────────────────────────────────┐
│         Load Balancer (Future)        │
└──────────────────┬───────────────────┘
                   ↓
┌──────────────────────────────────────┐
│      API Container (FastAPI)          │
│  ┌────────────────────────────────┐  │
│  │   Hexagonal Architecture       │  │
│  │  ┌──────────────────────────┐  │  │
│  │  │     Domain Layer         │  │  │
│  │  │  (Entities, Business)    │  │  │
│  │  └──────────────────────────┘  │  │
│  │  ┌──────────────────────────┐  │  │
│  │  │  Application Layer       │  │  │
│  │  │  (Use Cases, Ports)      │  │  │
│  │  └──────────────────────────┘  │  │
│  │  ┌──────────────────────────┐  │  │
│  │  │ Infrastructure Layer     │  │  │
│  │  │ (Adapters: S3, DB, PDF)  │  │  │
│  │  └──────────────────────────┘  │  │
│  │  ┌──────────────────────────┐  │  │
│  │  │      API Layer           │  │  │
│  │  │  (FastAPI Routes)        │  │  │
│  │  └──────────────────────────┘  │  │
│  └────────────────────────────────┘  │
└──────┬───────────────────┬───────────┘
       │                   │
       ↓                   ↓
┌──────────────┐   ┌──────────────┐
│  AWS S3      │   │ PostgreSQL   │
│  (PDFs)      │   │ (Results)    │
└──────────────┘   └──────────────┘
```

### 1.2 Hexagonal Architecture Layers

**Domain Layer** (Pure Business Logic)
- Entities: Transaction, Statement, SalaryAnalysis, Payslip, PayslipDeductions
- Business rules: is_excluded(), has_keyword(), is_early_morning(), verify_calculation()
- Zero dependencies on frameworks

**Application Layer** (Use Cases + Interfaces)
- Ports: IPDFExtractor, IDataMasker, ISalaryAnalyzer, IStorage, IDatabase, IPayslipOCR
- Use Cases: AnalyzeStatementUseCase, AnalyzePayslipUseCase
- Orchestrates domain logic

**Infrastructure Layer** (External Adapters)
- PyMuPDFExtractor (PDF processing)
- RegexMasker (PDPA compliance)
- ThaiSalaryAnalyzer (Salary detection)
- S3Storage (File storage)
- PostgresDatabase (Data persistence)
- TesseractPayslipOCR (Local OCR engine)
- GoogleVisionPayslipOCR (Cloud OCR engine)
- DualOCRPayslipExtractor (Comparison service)

**API Layer** (HTTP Interface)
- FastAPI routes
- Pydantic schemas
- Dependency injection

## 2. Component Design

### 2.1 API Service (FastAPI)

**Endpoints:**
```
GET  /api/v1/health
POST /api/v1/analyze-upload       (Bank statement - legacy)
POST /api/v1/analyze-statement-v2 (Bank statement - enhanced response)
POST /api/v1/analyze-payslip      (Payslip OCR - dual engine)
POST /api/v1/analyze-s3           (Future)
```

**Request Flow:**
```
1. Receive multipart/form-data (PDF + params)
2. Save PDF to temp location
3. Extract transactions (PyMuPDF)
4. Mask personal data (Regex)
5. Analyze salary (Thai tax model)
6. Upload PDF to S3
7. Save analysis results to PostgreSQL
8. Save audit log to PostgreSQL
9. Return JSON response
10. Cleanup temp files
```

**Dependencies:**
- FastAPI 0.115+
- uvicorn (ASGI server)
- python-multipart (file uploads)
- PyMuPDF 1.26+ (PDF extraction)
- boto3 (S3 client)
- asyncpg or psycopg2 (PostgreSQL)
- pandas, openpyxl (data processing)
- pytesseract 0.3.10+ (Tesseract Python wrapper)
- Pillow 10.0.0+ (Image processing)
- pdf2image 1.16.3+ (PDF to image conversion)
- google-cloud-vision 3.7.0+ (Google Vision API)

### 2.2 Database Service (PostgreSQL)

**Schema Design:**

```sql
-- Analyses table (main results storage)
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    detected_salary DECIMAL(15, 2),
    confidence VARCHAR(20) NOT NULL,
    transactions_analyzed INTEGER NOT NULL,
    credit_transactions INTEGER,
    debit_transactions INTEGER,
    clusters_found INTEGER,
    top_candidates_count INTEGER,
    expected_gross DECIMAL(15, 2),
    matches_expected BOOLEAN,
    difference DECIMAL(15, 2),
    difference_percentage DECIMAL(5, 2),
    employer VARCHAR(255),
    pvd_rate DECIMAL(5, 4),
    extra_deductions DECIMAL(15, 2),
    pdf_filename VARCHAR(255),
    pages_processed INTEGER,
    masked_items INTEGER,
    metadata JSONB, -- Store top candidates, statistics, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_confidence (confidence),
    INDEX idx_created_at (created_at)
);

-- Audit logs table (tracking and debugging)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- 'analyze_upload', 'analyze_s3'
    status VARCHAR(50) NOT NULL, -- 'success', 'failed', 'pending'
    error_message TEXT,
    error_type VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    processing_time_ms INTEGER,
    request_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_analysis_id (analysis_id),
    INDEX idx_action (action),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

**Design Decisions:**
- **No statements/transactions tables**: Privacy-first approach, store only analysis results
- **metadata JSONB**: Flexible storage for top candidates, clusters, and statistics
- **audit_logs**: Track all operations for debugging without storing sensitive data
- **No masked_mappings**: PDPA masking done during processing, not stored

**Migration Strategy:**
- Use Alembic for version control
- Initial migration: 001_initial_schema.py
- Future migrations: incremental changes

### 2.3 Storage Service (S3)

**Bucket Structure:**
```
s3://bank-statements-1761407671/
├── pdfs/
│   └── {user_id}/
│       └── {timestamp}_{filename}.pdf
```

**S3 Usage:**
- Store only original PDF files (not JSON results)
- PDF retention: 90 days (lifecycle policy)
- No metadata files needed (all metadata in PostgreSQL)

**S3 Configuration:**
- Region: ap-southeast-1
- Encryption: AES256 (server-side)
- Versioning: Enabled
- Lifecycle: Delete after 90 days
- Access: Private only (Block Public Access)

## 3. Data Flow Design

### 3.1 Analyze Statement Flow
```
1. API receives request
   ↓
2. Validate input (file type, size, parameters)
   ↓
3. Save PDF to temp location
   ↓
4. PyMuPDFExtractor.extract(pdf_path)
   → Returns Statement entity
   ↓
5. RegexMasker.mask(statement)
   → Returns (masked_statement, mapping)
   ↓
6. ThaiSalaryAnalyzer.analyze(masked_statement)
   → Returns SalaryAnalysis entity
   ↓
7. S3Storage.upload(pdf_file, user_id)
   → Returns s3_key
   ↓
8. PostgresDatabase.save_analysis(user_id, analysis, statistics)
   → Returns analysis_id
   ↓
9. PostgresDatabase.save_audit_log(user_id, action, status, analysis_id)
   ↓
10. Build JSON response
   ↓
11. Cleanup temp files
   ↓
12. Return response to mobile
```

### 3.2 Error Handling Flow
```
Try:
    Execute main flow
Catch PDFError:
    Log error → audit_logs
    Return 400 Bad Request
Catch S3Error:
    Log error → audit_logs
    Continue (save to DB only)
    Return 200 with warning
Catch DatabaseError:
    Log error → audit_logs
    Return 500 Internal Error
Finally:
    Cleanup temp files
```

### 3.3 Payslip OCR Processing Flow (NEW)
```
1. API receives payslip PDF/image request
   ↓
2. Validate input (file type, size < 10MB)
   ↓
3. Save PDF to temp location
   ↓
4. S3Storage.upload(payslip_pdf, user_id)
   → Upload to s3://bucket/payslips/{user_id}/
   → Returns s3_url
   ↓
5. TesseractPayslipOCR.extract_payslip_data(pdf_path)
   → OCR with Tesseract + tessdata-best
   → Returns: {salary, net_salary, deductions, confidence, raw_text}
   ↓
6. GoogleVisionPayslipOCR.extract_payslip_data(pdf_path)
   → OCR with Google Cloud Vision API
   → Returns: {salary, net_salary, deductions, confidence, raw_text}
   ↓
7. DualOCRPayslipExtractor.compare_results()
   → Calculate agreement_score
   → Find differences
   → Choose best result (higher confidence/agreement)
   → Returns: {final_data, comparison, tesseract_result, vision_result}
   ↓
8. Save OCR text to file: /app/tmp/{user_id}_{timestamp}_payslip_ocr.txt
   → Contains both Tesseract and Vision results
   → For debugging and audit
   ↓
9. Create Payslip entity
   → Validate calculation (salary - deductions = net_salary)
   → Returns: Payslip domain entity
   ↓
10. Build JSON response with:
    - Payslip data (salary, net_salary, deductions)
    - OCR comparison (engines_used, chosen_engine, agreement_score)
    - S3 URL
    - OCR text file path
    - Processing time
   ↓
11. Cleanup temp files
   ↓
12. Return response to mobile
```

**Dual OCR Strategy:**
- **High Agreement (>80%):** Use Google Vision (typically more accurate)
- **Low Agreement (<80%):** Use engine with higher confidence score
- **One Engine Fails:** Use working engine
- **Both Fail:** Return error

**OCR Comparison Example:**
```
Tesseract Result:
  salary: 50,000 THB
  net_salary: 42,100 THB
  confidence: 0.75

Google Vision Result:
  salary: 50,000 THB
  net_salary: 42,000 THB
  confidence: 0.90

Agreement Score: 0.95 (95% agreement)
Chosen Engine: vision (higher confidence)
Differences: [{"field": "net_salary", "diff": 100 THB, "diff_percent": 0.24%}]
```

## 4. Deployment Design

### 4.1 Docker Compose (Development)
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/bankdb
      - AWS_REGION=ap-southeast-1
    depends_on:
      - db
    volumes:
      - ./src:/app/src
  
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=bankdb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  web:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api

volumes:
  postgres_data:
```

### 4.2 Production Deployment (Future)
- AWS ECS Fargate or EC2
- RDS PostgreSQL (managed)
- Application Load Balancer
- Auto-scaling (2-10 containers)
- CloudWatch monitoring
- Secrets Manager for credentials

## 5. Security Design

### 5.1 Data Protection
- PDF files: Encrypted at rest (S3 AES256)
- Database: Encrypted connections (SSL/TLS)
- Masked mappings: Encrypted in database
- Secrets: Environment variables only

### 5.2 Access Control
- S3: IAM user with minimal permissions
- Database: Dedicated user with limited privileges
- API: No authentication (future: JWT tokens)

### 5.3 Audit Trail
- All operations logged to audit_logs table
- Include: user_id, action, timestamp, status, error_message
- Retention: 1 year

## 6. Performance Design

### 6.1 Optimization
- Async I/O for database operations
- Connection pooling (PostgreSQL)
- Multipart streaming for large PDFs
- Parallel processing (future)

### 6.2 Scalability
- Stateless API (horizontal scaling)
- Database connection pooling
- S3 for storage (unlimited capacity)
- Load balancer for distribution

## 7. Monitoring Design (Future)

### 7.1 Metrics
- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate (%)
- PDF processing time
- Database query time

### 7.2 Logging
- Application logs (INFO level)
- Error logs (ERROR level)
- Audit logs (database)
- Access logs (nginx)

### 7.3 Alerts
- High error rate (> 5%)
- Slow response time (> 5 seconds)
- Database connection failures
- S3 upload failures
