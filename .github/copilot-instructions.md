# GitHub Copilot Instructions - Bank Statement Analyzer

**CRITICAL: This is the master instruction file. Always start here.**

## Quick Start for AI Agents

Before implementing ANY task, you MUST:

1. **Read Project Documents (in order):**
   - `.github/REQUIREMENTS.md` - Understand WHAT to build
   - `.github/DESIGN.md` - Understand HOW to implement
   - `.github/tasks.json` - Check current task status

2. **Read AI Instructions (based on task type):**
   - **ALL tasks:** `.github/ai-instructions/00-START-HERE.md` (MANDATORY)
   - **Workflow questions:** `.github/ai-instructions/01-WORKFLOW.md`
   - **Coding tasks:** `.github/ai-instructions/02-ARCHITECTURE.md`
   - **Domain logic:** `.github/ai-instructions/03-DOMAIN-RULES.md`
   - **Running/Testing:** `.github/ai-instructions/04-DEVELOPMENT.md`
   - **Debugging:** `.github/ai-instructions/05-COMMON-ISSUES.md`
   - **Code standards:** `.github/ai-instructions/06-CODE-STANDARDS.md`

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

## How to Use These Instructions

### Example 1: Implementing New Feature

Task: "Add email notification feature"

**Steps:**
1. Read REQUIREMENTS.md → Find email notification requirements
2. Read DESIGN.md → Check if email service is specified
3. Read tasks.json → Check task dependencies
4. Read 00-START-HERE.md → Understand navigation
5. Read 02-ARCHITECTURE.md → Learn "Adding New Adapter" section
6. Implement: IEmailNotifier port + adapter
7. Update tasks.json → Mark task as completed

### Example 2: Fixing Bug

Task: "Fix circular import error"

**Steps:**
1. Read 05-COMMON-ISSUES.md → "Circular Import" section
2. Read 02-ARCHITECTURE.md → "Dependency Rule"
3. Fix code using dependency injection
4. Verify: No domain → infrastructure imports

### Example 3: Understanding Domain Logic

Task: "How does salary detection work?"

**Steps:**
1. Read 03-DOMAIN-RULES.md → "Salary Detection Algorithm"
2. Read DESIGN.md → Section 4: Analysis Layer
3. Check `src/infrastructure/analysis/thai_analyzer.py`

## AI Agent Verification

After reading instructions, you MUST be able to answer:

1. **What is the dependency rule?**
   - Answer: "Domain never imports from application/infrastructure"

2. **What files must NEVER be committed?**
   - Answer: "`*_mapping.json` files (contain unmasked data)"

3. **What's the maximum files to modify per task?**
   - Answer: "5 files. If more needed, break into subtasks"

4. **What format for documentation headings?**
   - Answer: "Plain text only. No emoji icons."

5. **What is the TDD cycle?**
   - Answer: "Red (write failing test) → Green (make it pass) → Refactor (improve code)"

6. **What test types are required?**
   - Answer: "Unit tests (mocked, fast) AND Integration tests (real dependencies)"

7. **When do you write tests?**
   - Answer: "BEFORE implementation (Test-First approach)"

## Announcement Required

When starting work, AI must announce:

```
"I've read the following instructions:
- REQUIREMENTS.md (Section X)
- DESIGN.md (Section Y)  
- ai-instructions/01-WORKFLOW.md
- ai-instructions/02-ARCHITECTURE.md
- ai-instructions/04-DEVELOPMENT.md (TDD section)

I understand:
- Task ID: TASK_XXX
- Dependencies: [list]
- Target files: [list]
- Test strategy: Unit tests (mocked) + Integration tests (real DB/S3)
- TDD approach: Red → Green → Refactor
- Acceptance criteria: [list]

Ready to implement."
```

## Directory Structure

```
.github/
├── copilot-instructions.md     ← You are here (Master index)
├── REQUIREMENTS.md              ← Business requirements
├── DESIGN.md                    ← Technical specifications
├── tasks.json                   ← Task tracking
└── ai-instructions/             ← Detailed guidelines
    ├── 00-START-HERE.md         ← Navigation guide
    ├── 01-WORKFLOW.md           ← Task workflow
    ├── 02-ARCHITECTURE.md       ← Code patterns
    ├── 03-DOMAIN-RULES.md       ← Business logic
    ├── 04-DEVELOPMENT.md        ← Running & testing
    ├── 05-COMMON-ISSUES.md      ← Troubleshooting
    └── 06-CODE-STANDARDS.md     ← Conventions
```

## Project Context

- **Project:** Bank Statement Analyzer (Thai banking)
- **Architecture:** Hexagonal (Ports & Adapters)
- **Language:** Python 3.10+ with Thai UTF-8 support
- **Framework:** FastAPI
- **Compliance:** PDPA (Thai data protection law)

## Critical Rules

### FORBIDDEN Actions

- ❌ Modify domain layer to import from infrastructure
- ❌ Skip updating tasks.json after completion
- ❌ Use emoji in documentation
- ❌ Commit `*_mapping.json` files
- ❌ Modify more than 5 files without breaking into subtasks
- ❌ **Write implementation before tests (violates TDD)**
- ❌ **Skip unit tests or integration tests**
- ❌ **Commit code without running tests**

### REQUIRED Actions

- ✅ Read REQUIREMENTS + DESIGN + tasks.json first
- ✅ Announce which instructions you read
- ✅ **Write tests BEFORE implementation (TDD Red-Green-Refactor)**
- ✅ **Write both unit tests AND integration tests**
- ✅ **Run tests and verify they pass before marking task complete**
- ✅ Update tasks.json after each completion
- ✅ Use dependency injection for all adapters
- ✅ Write tests for domain logic

## Getting Help

### If Instructions Are Unclear

1. State what you've read
2. State what's unclear
3. Reference specific section (e.g., "DESIGN.md Section 3.2")
4. Ask user for clarification

### If Documents Conflict

- REQUIREMENTS.md = source of truth for WHAT
- DESIGN.md = source of truth for HOW
- Ask user to resolve conflicts

## Success Criteria

A successful AI session includes:

- ✅ Correct files read (announced at start)
- ✅ Tasks completed (1-3 per session)
- ✅ Files modified (≤5 files)
- ✅ tasks.json updated
- ✅ No forbidden actions violated
- ✅ Tests pass (if applicable)

## Next Step

**READ NEXT:** `.github/ai-instructions/00-START-HERE.md` for detailed navigation guide.

---

## Quick Reference (Summary)

For detailed information, refer to the appropriate ai-instructions file:

**Architecture:** Hexagonal (Ports & Adapters)
- Domain: Pure business logic (entities, no framework dependencies)
- Application: Use cases + ports (interfaces)
- Infrastructure: Adapters (PyMuPDF, S3, PostgreSQL, Thai analyzer)
- API: FastAPI endpoints with dependency injection

**Key Principles:**
- Dependency Rule: Domain never imports from application/infrastructure
- Dependency Injection: Use DI container in `api/v1/dependencies.py`
- PDPA Compliance: Always mask personal data, never commit `*_mapping.json`
- NO ICONS/EMOJIS: Plain text only in all documentation

**Project Files:**
- 31 Python files across 4 layers
- 11 packages total (asyncpg>=0.29.0)
- Database: PostgreSQL with 2 tables (analyses, audit_logs)
- Storage: S3 for PDFs, PostgreSQL for results

**For more details:**
- Architecture patterns → 02-ARCHITECTURE.md
- Domain logic → 03-DOMAIN-RULES.md
- Running/Testing → 04-DEVELOPMENT.md
- Debugging → 05-COMMON-ISSUES.md
- Code standards → 06-CODE-STANDARDS.md
