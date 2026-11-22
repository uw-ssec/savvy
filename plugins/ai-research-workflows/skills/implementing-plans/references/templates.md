# Implementing Plans — Templates

## Phase Complete / Ready for Manual Verification

After a phase's automated checks pass, pause and present this, then wait for
the user's confirmation before starting the next phase. When the user asked for
several phases in one go, present it once, after the last of them, listing every
phase's manual checks. Leave the manual items unticked (`- [ ]`) here and in
the plan until the user confirms them.

```
## Phase [N] Complete - Ready for Manual Verification

### Automated Verification Results:
✅ `make test` — All 45 tests passing
✅ `pytest tests/` — 12 new tests added, all passing
✅ `mypy src/` — Type checking passed

### Manual Verification Needed:

Please perform these manual tests listed in the plan:
- [ ] [Manual step 1]
- [ ] [Manual step 2]

Let me know when manual testing is complete so I can proceed to Phase [N+1].
```

## Issue in Phase / Mismatch Report

When what you find does not match the plan, stop and present this template:

```
## Issue in Phase [N]:

**Expected (from plan):**
[What the plan says should exist]

**Found (actual situation):**
[What actually exists in the codebase]

**Why this matters:**
[Explain the impact of this mismatch]

**Possible approaches:**
1. [Option 1 with trade-offs]
2. [Option 2 with trade-offs]

How should I proceed?
```

Wait for user guidance before continuing. Let the user decide whether to adjust
the plan, proceed with original intent, or research further.

## Implementation Completion Summary

After completing all phases, present this summary:

```
# Implementation Complete

All phases of the plan have been executed.

## Summary:
- Phases completed: [N]
- Files created: [count]
- Files modified: [count]
- Tests added: [count]
- All automated verification: ✅ Passing

## Implementation documented at:
`docs/rse/specs/implement-[slug].md`

## Verification Status:
✅ Automated verification complete
⏸️ Manual verification pending (see plan for steps)

## Next Steps:
1. Complete manual verification as listed in the plan
2. Run the validating-implementations skill for systematic validation
3. Create commit
4. Create pull request
```
