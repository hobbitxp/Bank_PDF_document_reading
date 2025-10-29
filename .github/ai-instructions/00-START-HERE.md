# AI Instructions Navigation Guide

**READ THIS FIRST** - This file helps you navigate the instruction system.

## Purpose
This directory contains detailed guidelines for implementing the Bank Statement Analyzer project. These instructions complement the project documents (REQUIREMENTS.md, DESIGN.md, tasks.json).

## File Structure

### Core Documents (Read First)
1. **`.github/REQUIREMENTS.md`** - Business and technical requirements
2. **`.github/DESIGN.md`** - System architecture and component design
3. **`.github/tasks.json`** - Task tracking with dependencies

### AI Instructions (Read Based on Task)

**00-START-HERE.md** (This file)
- Navigation guide for all instructions
- How to use the instruction system

**01-WORKFLOW.md** (MANDATORY for ALL tasks)
- Project management workflow
- Task lifecycle (read → implement → update)
- When to update tasks.json

**02-ARCHITECTURE.md** (For coding tasks)
- Hexagonal Architecture patterns
- Dependency rules
- Adding new adapters
- Integration points

**03-DOMAIN-RULES.md** (For domain logic)
- Thai banking context
- Salary detection algorithm
- PDPA compliance rules
- Domain entity design

**04-DEVELOPMENT.md** (For running/testing)
- Running the API
- Testing strategies
- Development commands
- Project structure

**05-COMMON-ISSUES.md** (For debugging)
- Circular import errors
- Port not found issues
- S3 connection problems
- Database connection issues

**06-CODE-STANDARDS.md** (Before committing)
- Python conventions
- Type hints
- Error handling
- CLI patterns
- NO ICONS/EMOJIS POLICY

## How to Use

### Scenario 1: Starting New Task
```
1. Read tasks.json → Find your task ID
2. Read REQUIREMENTS.md → Section matching task
3. Read DESIGN.md → Component specifications
4. Read 01-WORKFLOW.md → Verify dependencies
5. Read 02-ARCHITECTURE.md → Implementation patterns
6. Implement → Write code
7. Update tasks.json → Mark completed
```

### Scenario 2: Fixing Bug
```
1. Read 05-COMMON-ISSUES.md → Find similar issue
2. Read 02-ARCHITECTURE.md → Check pattern compliance
3. Fix code
4. Test fix
```

### Scenario 3: Understanding Domain
```
1. Read 03-DOMAIN-RULES.md → Business logic section
2. Read DESIGN.md → Component relationships
3. Check source code for implementation
```

### Scenario 4: Running/Testing
```
1. Read 04-DEVELOPMENT.md → Commands section
2. Read 02-ARCHITECTURE.md → Test strategy
3. Execute tests
```

## Quick Reference

### When to Read Each File

| Task Type | Required Files | Optional Files |
|-----------|---------------|----------------|
| Implement feature | 01, 02, 03 | 04, 06 |
| Fix bug | 01, 05 | 02, 03 |
| Add adapter | 01, 02 | 03, 06 |
| Write tests | 01, 04 | 02, 06 |
| Domain logic | 01, 03 | 02, 04 |
| Code review | 06 | 02, 03 |

### Critical Rules

**FORBIDDEN:**
- ❌ Skip reading REQUIREMENTS.md, DESIGN.md, tasks.json
- ❌ Modify domain to import from infrastructure
- ❌ Use emoji in documentation
- ❌ Commit `*_mapping.json` files
- ❌ Modify >5 files without breaking into subtasks

**REQUIRED:**
- ✅ Announce which files you read
- ✅ Cite specific sections when deciding
- ✅ Update tasks.json after completion
- ✅ Follow Hexagonal Architecture rules
- ✅ Use dependency injection

## AI Agent Workflow

### Step 1: Announce Understanding
```
"I've read:
- REQUIREMENTS.md (Section X: Feature description)
- DESIGN.md (Section Y: Component specification)
- tasks.json (Task ID: TASK_XXX)
- 01-WORKFLOW.md (Task lifecycle)
- 02-ARCHITECTURE.md (Hexagonal patterns)

I understand:
- Task: [description]
- Dependencies: [list]
- Target files: [list]
- Acceptance criteria: [list]

Ready to implement."
```

### Step 2: Implement
- Follow patterns from 02-ARCHITECTURE.md
- Apply rules from 03-DOMAIN-RULES.md
- Use conventions from 06-CODE-STANDARDS.md

### Step 3: Complete
- Test using 04-DEVELOPMENT.md
- Update tasks.json per 01-WORKFLOW.md
- Verify no violations of FORBIDDEN rules

## Examples

### Example 1: Implement Email Notifier
```
Files to read:
1. REQUIREMENTS.md → Check if email feature exists
2. DESIGN.md → Check notification design
3. tasks.json → Find task ID
4. 01-WORKFLOW.md → Verify dependencies
5. 02-ARCHITECTURE.md → "Adding New Adapter" section

Implementation:
- Create IEmailNotifier port (application/ports/)
- Create SendGridNotifier adapter (infrastructure/email/)
- Register in dependencies.py
- Update tasks.json
```

### Example 2: Fix Circular Import
```
Files to read:
1. 05-COMMON-ISSUES.md → "Circular Import" section
2. 02-ARCHITECTURE.md → "Dependency Rule" section

Solution:
- Remove direct import from domain
- Use dependency injection instead
- Verify: domain → application → infrastructure
```

### Example 3: Understand Salary Detection
```
Files to read:
1. 03-DOMAIN-RULES.md → "Salary Detection Algorithm"
2. DESIGN.md → Section 4: Analysis Layer
3. Source: src/infrastructure/analysis/thai_analyzer.py

Understanding:
- Multi-factor scoring (keyword, employer, time, cluster)
- Thai tax calculation (progressive brackets)
- Confidence levels (high/medium/low)
```

## Verification Checklist

Before considering work complete, verify:

- [ ] Read correct instruction files for task type
- [ ] Announced understanding at start
- [ ] Implemented per DESIGN.md specifications
- [ ] Followed patterns from 02-ARCHITECTURE.md
- [ ] Applied rules from 03-DOMAIN-RULES.md
- [ ] Used conventions from 06-CODE-STANDARDS.md
- [ ] Updated tasks.json per 01-WORKFLOW.md
- [ ] No FORBIDDEN actions violated
- [ ] All tests pass (if applicable)

## Getting Help

If instructions are unclear:
1. State what you've read (file names + sections)
2. State what's unclear (specific question)
3. Reference specific section (e.g., "DESIGN.md Section 3.2 is ambiguous")
4. Ask user for clarification

If documents conflict:
1. REQUIREMENTS.md = source of truth for WHAT
2. DESIGN.md = source of truth for HOW
3. Ask user to resolve conflicts

## Next Steps

**For new implementation task:**
→ Read 01-WORKFLOW.md next

**For debugging task:**
→ Read 05-COMMON-ISSUES.md next

**For understanding domain:**
→ Read 03-DOMAIN-RULES.md next

**For testing:**
→ Read 04-DEVELOPMENT.md next
