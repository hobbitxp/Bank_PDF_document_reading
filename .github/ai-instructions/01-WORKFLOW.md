# Workflow Guidelines

**MANDATORY: Read this for ALL tasks**

## Project Management Workflow

### Critical Rule
**ALWAYS follow this workflow before starting any work**

### Step 1: Read Project Documents (in order)

1. **`.github/REQUIREMENTS.md`**
   - Understand WHAT needs to be done (business requirements)
   - Find functional requirements (FR-XXX)
   - Find non-functional requirements (NFR-XXX)
   - Identify acceptance criteria

2. **`.github/DESIGN.md`**
   - Understand HOW to implement (architecture, schemas, data flow)
   - Find component specifications
   - Check data flow diagrams
   - Review interface contracts

3. **`.github/tasks.json`**
   - Check current task status (pending/in_progress/completed)
   - Verify dependencies are completed
   - Read task description and estimated hours
   - Note files to create/modify

### Step 2: Before Starting Work

**Verification Checklist:**
- [ ] Identify which task you're working on (by task ID)
- [ ] Verify all dependencies are completed
- [ ] Read relevant sections in DESIGN.md for implementation details
- [ ] Understand the acceptance criteria from REQUIREMENTS.md
- [ ] Check files to create/modify in tasks.json
- [ ] Estimate if task needs subtasks (>5 files = subtask)
- [ ] **Plan test strategy: Unit tests + Integration tests (TDD)**

**Announcement Template:**
```
"I've read:
- REQUIREMENTS.md (Section X: [requirement])
- DESIGN.md (Section Y: [component])
- tasks.json (Task ID: [id], Dependencies: [list])

I understand:
- Task: [description]
- Files to modify: [list]
- Acceptance criteria: [criteria]
- Test strategy: [unit tests + integration tests]
- Estimated complexity: [hours]

Ready to implement."
```

### Step 3: During Work (TDD Approach)

**MANDATORY: Test-Driven Development (TDD)**

**TDD Cycle (Red-Green-Refactor):**

```
1. RED: Write failing test first
   ↓
2. GREEN: Write minimal code to pass test
   ↓
3. REFACTOR: Improve code quality
   ↓
4. REPEAT for next feature
```

**Implementation Order:**

**A. Write Tests First (RED Phase):**

1. **Unit Tests (Domain/Application Layer):**
   ```bash
   # Create test file: tests/test_<component>.py
   # Write test cases based on requirements
   # Example: tests/test_salary_analyzer.py
   ```
   
   ```python
   def test_detect_salary_with_keyword():
       """Test salary detection with 'เงินเดือน' keyword"""
       # Arrange
       transactions = [...]
       analyzer = SalaryAnalyzer()
       
       # Act
       result = analyzer.analyze(transactions)
       
       # Assert
       assert result.detected_amount == 50000.0
       assert result.confidence == "high"
   ```

2. **Integration Tests (Infrastructure Layer):**
   ```bash
   # Create: tests/test_<adapter>_integration.py
   # Mark with @pytest.mark.integration
   # Example: tests/test_database_integration.py
   ```
   
   ```python
   @pytest.mark.integration
   async def test_save_analysis_real_db(db_connection):
       """Test saving to real PostgreSQL"""
       db = PostgresDatabase(connection_string=...)
       
       result = await db.save_analysis(...)
       
       assert isinstance(result, UUID)
   ```

3. **Run Tests - Should FAIL:**
   ```bash
   # Unit tests (should fail - no implementation yet)
   pytest tests/test_<component>.py -v
   
   # Expected: FAILED (because code doesn't exist)
   ```

**B. Implement Code (GREEN Phase):**

1. **Write minimal implementation to pass tests**
2. **Focus on making tests pass, not perfection**
3. **Run tests frequently:**
   ```bash
   # After each change
   pytest tests/test_<component>.py -v
   ```

**C. Refactor (REFACTOR Phase):**

1. **Improve code quality without breaking tests**
2. **Apply design patterns**
3. **Optimize performance**
4. **Verify tests still pass:**
   ```bash
   pytest tests/ -v
   ```

**Implementation Rules:**

1. **File Limit:**
   - Modify ≤5 files per task
   - If >5 files needed, break into subtasks
   - Update tasks.json with new subtasks

2. **Test Coverage Requirements:**
   - **Domain Layer:** 100% unit test coverage (pure logic)
   - **Application Layer:** 90%+ unit test coverage (use cases)
   - **Infrastructure Layer:** Integration tests for all adapters
   - **API Layer:** E2E tests for critical endpoints

3. **Test Types Required:**

   **Unit Tests (Fast, No I/O):**
   - Domain entities and value objects
   - Application use cases (with mocked ports)
   - Pure functions and algorithms
   - Run: `pytest tests/ -v -m "not integration"`

   **Integration Tests (Slower, Real Dependencies):**
   - Database adapters (PostgreSQL)
   - Storage adapters (S3)
   - PDF extractors (PyMuPDF)
   - Run: `pytest tests/ -v -m integration`
   - **Requires:** Docker services running

4. **Incremental Progress:**
   - Write test → Implement → Verify → Commit
   - Test after each change
   - Update tasks.json notes field with test results

5. **Dependency Injection:**
   - Never import concrete implementations in domain
   - Always use ports (interfaces)
   - Register in `api/v1/dependencies.py`

**Example TDD Workflow:**

```bash
# Task: Implement salary detection algorithm

# Step 1: Write failing test
cat > tests/test_salary_detector.py << 'EOF'
def test_detect_salary_from_transactions():
    detector = SalaryDetector()
    transactions = [
        {"amount": 50000, "description": "เงินเดือน"},
        {"amount": 100, "description": "ค่าอาหาร"}
    ]
    result = detector.detect(transactions)
    assert result == 50000.0
EOF

# Step 2: Run test (should FAIL)
pytest tests/test_salary_detector.py -v
# ❌ FAILED: ModuleNotFoundError: No module named 'salary_detector'

# Step 3: Create minimal implementation
cat > src/domain/services/salary_detector.py << 'EOF'
class SalaryDetector:
    def detect(self, transactions):
        return 50000.0  # Hardcoded to pass test
EOF

# Step 4: Run test (should PASS)
pytest tests/test_salary_detector.py -v
# ✅ PASSED

# Step 5: Add more test cases
# Step 6: Refactor implementation
# Step 7: Verify all tests still pass
```

### Step 4: After Completing Work

**Before Marking Task Complete:**

1. **Run All Tests:**
   ```bash
   # Unit tests (must pass)
   pytest tests/ -v -m "not integration"
   
   # Integration tests (if dependencies available)
   pytest tests/ -v -m integration
   
   # Full test suite
   pytest tests/ -v
   ```

2. **Verify Test Coverage:**
   ```bash
   # Check coverage
   pytest tests/ --cov=src --cov-report=term-missing
   
   # Minimum requirements:
   # - Domain: 100% coverage
   # - Application: 90% coverage
   # - Infrastructure: 70% coverage (integration tests)
   ```

3. **Check Code Quality:**
   ```bash
   # No lint errors
   # All type hints present
   # Docstrings complete
   ```

**Update `.github/tasks.json`:**

```json
{
  "id": 7,
  "title": "Task Title",
  "status": "completed",           // ← Change from "pending"
  "completed_date": "2025-01-15",  // ← Add completion date
  "priority": "high",
  "dependencies": [6],
  "estimated_hours": 6,
  "files_to_create": [...],
  "files_to_modify": [...],
  "notes": "✅ Created X. ✅ Implemented Y. ✅ Tests: 12 passed. ✅ Coverage: 95%"  // ← Add test results
}
```

**Verification Checklist:**
- [ ] Implementation matches DESIGN.md specifications
- [ ] All requirements from REQUIREMENTS.md are satisfied
- [ ] Files listed in tasks.json are created/modified
- [ ] **Unit tests written and passing**
- [ ] **Integration tests written (if applicable)**
- [ ] **Test coverage meets minimum requirements**
- [ ] No FORBIDDEN actions violated
- [ ] tasks.json updated with "completed" status
- [ ] Completion date added
- [ ] Notes field updated with test results

### Step 5: If Blocked or Need Clarification

**Decision Tree:**

```
Problem encountered?
  ↓
Check REQUIREMENTS.md for acceptance criteria
  ↓
Still unclear?
  ↓
Check DESIGN.md for technical specifications
  ↓
Still unclear?
  ↓
Check 05-COMMON-ISSUES.md for similar problems
  ↓
Still unclear?
  ↓
Ask user with context:
  - What you've read (file + section)
  - What's unclear (specific question)
  - What you've tried (debugging steps)
```

**Question Template:**
```
"I've read:
- REQUIREMENTS.md (Section X: [relevant part])
- DESIGN.md (Section Y: [relevant part])
- 05-COMMON-ISSUES.md ([issue type])

Issue: [describe problem]

Ambiguity: [what's unclear]

Attempted solutions:
1. [tried X]
2. [tried Y]

Question: [specific question]"
```

## Document Hierarchy

```
REQUIREMENTS.md (What to build - Business requirements)
    ↓
DESIGN.md (How to build - Technical architecture)
    ↓
tasks.json (When to build - Task tracking)
    ↓
ai-instructions/*.md (Guidelines for implementation)
    ↓
Implementation (Your code changes)
    ↓
Update tasks.json (Mark as completed)
```

**Authority:**
- REQUIREMENTS.md = Source of truth for WHAT
- DESIGN.md = Source of truth for HOW
- tasks.json = Source of truth for WHEN

**Conflict Resolution:**
- If REQUIREMENTS + DESIGN conflict → Ask user
- If DESIGN + code conflict → DESIGN wins
- If tasks.json + code conflict → tasks.json wins

## Task Lifecycle

### State Diagram
```
pending → in_progress → completed
   ↓           ↓            ↓
blocked    paused      verified
```

### State Definitions

**pending:**
- Task not yet started
- Dependencies may be incomplete
- No code changes made

**in_progress:**
- Task currently being worked on
- Some code changes made
- Not ready for verification

**blocked:**
- Task cannot proceed
- Dependency incomplete or issue found
- Requires user intervention

**paused:**
- Task temporarily suspended
- Code changes committed but incomplete
- Will resume later

**completed:**
- All code changes made
- Tests pass
- tasks.json updated
- Ready for verification

**verified:**
- User confirmed task complete
- All acceptance criteria met
- Can proceed to dependent tasks

### Updating Task Status

**Move to in_progress:**
```json
{
  "id": 8,
  "status": "in_progress",
  "started_date": "2025-01-15",
  "notes": "Started implementing database integration"
}
```

**Move to blocked:**
```json
{
  "id": 8,
  "status": "blocked",
  "blocked_reason": "Dependency Task 7 incomplete",
  "blocked_date": "2025-01-15"
}
```

**Move to completed:**
```json
{
  "id": 8,
  "status": "completed",
  "completed_date": "2025-01-15",
  "notes": "✅ All files modified. ✅ Tests pass. ✅ Verified."
}
```

## Task Breakdown Guidelines

### When to Break into Subtasks

**Break if ANY of these apply:**
- Task requires >5 file modifications
- Estimated hours >8
- Multiple independent components
- Can be parallelized
- Complex with multiple acceptance criteria

**Example: Task Too Large**
```json
{
  "id": 10,
  "title": "Implement complete authentication system",
  "estimated_hours": 16,
  "files_to_modify": [
    "src/domain/user.py",
    "src/application/ports/auth.py",
    "src/application/use_cases/login.py",
    "src/application/use_cases/register.py",
    "src/infrastructure/auth/jwt_adapter.py",
    "src/infrastructure/auth/bcrypt_adapter.py",
    "src/api/v1/routes/auth.py",
    "src/api/v1/schemas.py",
    "tests/unit/test_auth.py",
    "tests/integration/test_auth.py"
  ]
}
```

**Break into subtasks:**
```json
{
  "id": 10,
  "title": "Authentication System",
  "subtasks": [
    {
      "id": 10.1,
      "title": "User domain entity",
      "estimated_hours": 2,
      "files_to_modify": ["src/domain/user.py"]
    },
    {
      "id": 10.2,
      "title": "Auth ports",
      "estimated_hours": 3,
      "files_to_modify": [
        "src/application/ports/auth.py",
        "src/application/ports/password_hasher.py"
      ]
    },
    {
      "id": 10.3,
      "title": "Login use case",
      "estimated_hours": 4,
      "files_to_modify": [
        "src/application/use_cases/login.py",
        "tests/unit/test_login.py"
      ]
    }
  ]
}
```

### Task Dependencies

**Valid dependency chain:**
```
Task 1 (Domain entities)
  ↓
Task 2 (Application ports)
  ↓
Task 3 (Infrastructure adapters)
  ↓
Task 4 (API routes)
  ↓
Task 5 (Integration tests)
```

**Invalid dependency (circular):**
```
Task 1 depends on Task 2
Task 2 depends on Task 3
Task 3 depends on Task 1  ← FORBIDDEN
```

**Checking dependencies:**
```json
{
  "id": 8,
  "dependencies": [7],  // Task 7 must be completed
  "status": "pending"
}
```

**Before starting Task 8:**
1. Read tasks.json
2. Find Task 7
3. Verify Task 7 status = "completed"
4. If not completed → Mark Task 8 as "blocked"

## Common Workflow Patterns

### Pattern 1: New Feature Implementation
```
1. Read REQUIREMENTS.md → Find FR-XXX
2. Read DESIGN.md → Find component specs
3. Read tasks.json → Check dependencies
4. Create domain entity (if needed)
5. Create application port (interface)
6. Create infrastructure adapter (implementation)
7. Register in dependencies.py
8. Create API route
9. Write tests
10. Update tasks.json
```

### Pattern 2: Bug Fix
```
1. Read 05-COMMON-ISSUES.md → Find similar issue
2. Read DESIGN.md → Check affected components
3. Identify root cause
4. Fix code
5. Run tests
6. Update tasks.json notes (if bug was a task)
```

### Pattern 3: Refactoring
```
1. Read DESIGN.md → Verify current architecture
2. Read 02-ARCHITECTURE.md → Check patterns
3. Plan refactoring (which files affected)
4. If >5 files → Break into subtasks
5. Refactor incrementally
6. Run tests after each change
7. Update tasks.json
```

## Success Criteria

A successful task completion includes:

**Code Quality:**
- ✅ Follows Hexagonal Architecture (02-ARCHITECTURE.md)
- ✅ Follows domain rules (03-DOMAIN-RULES.md)
- ✅ Follows code standards (06-CODE-STANDARDS.md)
- ✅ No FORBIDDEN actions

**Documentation:**
- ✅ tasks.json updated with "completed" status
- ✅ Completion date added
- ✅ Notes field summarizes work
- ✅ No emoji in comments/docs

**Testing:**
- ✅ Unit tests pass (if applicable)
- ✅ Integration tests pass (if applicable)
- ✅ Manual testing done

**Verification:**
- ✅ Matches DESIGN.md specifications
- ✅ Satisfies REQUIREMENTS.md criteria
- ✅ All files in tasks.json created/modified
- ✅ No regressions introduced

## Anti-Patterns to Avoid

**❌ Skipping Document Reading**
```
Bad: Start coding immediately without reading REQUIREMENTS.md
Good: Read REQUIREMENTS → DESIGN → tasks.json → Implement
```

**❌ Modifying Too Many Files**
```
Bad: Modify 10 files in one task
Good: Break into 2-3 subtasks (≤5 files each)
```

**❌ Forgetting to Update tasks.json**
```
Bad: Complete work but leave status = "pending"
Good: Update status = "completed" + add notes
```

**❌ Not Checking Dependencies**
```
Bad: Start Task 8 when Task 7 is incomplete
Good: Verify dependencies first, mark as "blocked" if needed
```

**❌ Implementing Without Specification**
```
Bad: Guess how to implement based on task title
Good: Read DESIGN.md for exact specifications
```

## Quick Reference

### Before Starting
- [ ] Read REQUIREMENTS.md section
- [ ] Read DESIGN.md section
- [ ] Read tasks.json entry
- [ ] Verify dependencies complete
- [ ] Announce understanding

### During Work
- [ ] Follow Hexagonal Architecture
- [ ] Modify ≤5 files
- [ ] Test after each change
- [ ] Use dependency injection

### After Completion
- [ ] Update tasks.json status
- [ ] Add completion date
- [ ] Add notes summary
- [ ] Verify tests pass
- [ ] Verify no FORBIDDEN actions

## Next Steps

**For architecture patterns:**
→ Read 02-ARCHITECTURE.md

**For domain logic:**
→ Read 03-DOMAIN-RULES.md

**For running/testing:**
→ Read 04-DEVELOPMENT.md

**For debugging:**
→ Read 05-COMMON-ISSUES.md

**For code standards:**
→ Read 06-CODE-STANDARDS.md
