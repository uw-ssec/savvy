# Validating Implementations — Report Templates

## Contents

- [Report layout](#report-layout)
- [Header and provenance](#header-and-provenance)
- [Implementation Status per Phase](#implementation-status-per-phase)
- [Automated Verification Results](#automated-verification-results)
- [Code Review Findings](#code-review-findings)
- [Manual Testing Required](#manual-testing-required)
- [Recommendations](#recommendations)
- [References](#references)
- [Closing the conversation](#closing-the-conversation)
- [Special cases](#special-cases)

## Report layout

Write the report to `docs/rse/specs/validation-<slug>.md`, where `<slug>` comes
from the plan's file name (`plan-oauth-support.md` → `validation-oauth-support.md`).
Create `docs/rse/specs/` if it does not exist. Overwrite any earlier validation
of the same plan; git history keeps earlier verdicts. Present the same content
inline, then confirm the file's path.

The file contains, in order:

1. Header and provenance, with the Overall Status and Summary
2. **Implementation Status**: per-phase completion with task-level detail
3. **Automated Verification Results**: pass/fail for each command, with root
   cause and recommendation for each failure
4. **Code Review Findings**: what matches the plan, deviations, potential issues
5. **Manual Testing Required**: actionable steps for items a human must check
6. **Recommendations**: Critical / Important / Nice to Have / Follow-Up
7. **References**: links to the plan and the implementation summary

## Header and provenance

```markdown
# Validation: [Feature Name]

> Validated against `docs/rse/specs/plan-[slug].md` / `docs/rse/specs/implement-[slug].md`
> at commit `[short-sha]` on `[YYYY-MM-DD]`.

## Overall Status: [Ready, Issues Found or Incomplete — write one]

## Summary
- Phases: [X] of [Y] fully implemented
- Automated Checks: [X] passing, [Y] failing
- Manual Testing: [X] items require human verification
- Critical Issues: [X]
- Important Issues: [Y]
```

Get the short SHA with `git rev-parse --short HEAD`. If there is no
`implement-[slug].md`, name the plan only and say so. Status rules: **Ready**
only when every check you ran passed and every criterion is met; **Issues
Found** when anything failed or is unexplained; **Incomplete** when phases are
unfinished.

## Implementation Status per Phase

```markdown
## Implementation Status

### Phase 1: [Name]
**Status:** ✅ Fully implemented | ⚠️ Partially implemented | ❌ Not started

**Details:**
- [Task 1]: ✅ Complete
- [Task 2]: ✅ Complete
- [Task 3]: ⚠️ Partially complete (details…)

### Phase 2: [Name]
[Continue for all phases…]
```

## Automated Verification Results

```markdown
## Automated Verification Results

### Passing Checks:
- ✅ `pixi run pytest` — 45 passed (expected 45)
- ✅ `pixi run mypy src/` — no errors

### Failing Checks:
- ❌ `pixi run pytest tests/test_spectrum.py::test_parseval` — 2 failed (expected 0)
  - **Error:** `AssertionError: power 0.97 != 1.00 within rtol=1e-6`
  - **Root Cause:** implementation bug — window normalisation applied twice
  - **Location:** `src/pkg/spectrum.py:34`
  - **Recommendation:** remove the second normalisation (Critical)

[No failing checks? State "All automated verification checks passed."]
```

## Code Review Findings

```markdown
## Code Review Findings

### What Matches Plan:
- [List items that match]

### Deviations from Plan:
- **Deviation 1:** [Description, with `file:line`]
  - **Reason:** [If known; otherwise "not recorded"]
  - **Impact:** [Effect on behaviour, results or complexity]
  - **Assessment:** Acceptable | Problematic

[No deviations? State "Implementation matches plan exactly."]

### Potential Issues:
- [Issue with `file:line` reference and description]

[No issues? State "No issues identified."]
```

## Manual Testing Required

```markdown
## Manual Testing Required

1. **[Test area]**
   - [Step-by-step instructions]
   - Expected: [outcome]
   - Status: pending | confirmed by the user in this session
```

## Recommendations

```markdown
## Recommendations

### Critical (Must Fix Before Merge):
- [Item]

### Important (Should Fix):
- [Item]

### Nice to Have:
- [Item]

### Follow-Up Work:
- [Item]
```

## References

End the document with relative links to the plan and implementation summary,
which sit in the same directory:

```markdown
## References

- [Plan: Feature Name](plan-[slug].md)
- [Implementation: Feature Name](implement-[slug].md)
```

## Closing the conversation

After presenting the report inline, offer next steps without acting on them:

```
Would you like me to:
1. Fix the identified issues
2. Provide more detail on any specific finding
3. Run additional verification checks
```

## Special cases

### Implementation Incomplete

```markdown
## Implementation Status: Incomplete

### Completed Phases:
- Phase 1: ✅ Complete

### Incomplete Phases:
- Phase 3: ⚠️ Partially complete (tasks 1-3 done, tasks 4-5 not started)
- Phase 4: ❌ Not started

**Recommendation:** Complete Phase 3 before validating further.
```

### No Automated Checks Defined

```markdown
## Automated Verification: No Checks Defined

The plan does not include automated verification checks. Manual validation alone
is insufficient for complex changes.

**Recommendation:** Add test commands, file-existence checks, or scripts to the
plan before re-validating.
```

### Failing Tests

Document each failure in the "Failing Checks" format above: command, error
output, root cause, location, recommendation and priority.
