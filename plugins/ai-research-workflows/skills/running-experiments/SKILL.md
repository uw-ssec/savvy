---
name: running-experiments
description: >-
  Use when the best technical approach is genuinely uncertain and two or three
  candidate libraries, designs or implementations should be built and measured
  head-to-head before committing. Triggers: should I use X or Y, prototype both,
  compare approaches, benchmark before
  committing, which is faster on our data, A/B two implementations. Not for
  surveying existing tools or papers (use researching).
metadata:
  capability-network: read
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Running Experiments

An optional step for genuinely uncertain decisions: build 2-3 distinct
approaches as real code, measure them under the same conditions, and recommend
one from the evidence.

## Iron Law: an experiment is real measured code, or it is not an experiment

Every approach you compare must be **actually built and run**. Never estimate
or "fill in" an approach's result, not even the one everyone is "sure" is
slower. One side measured and the other assumed is an opinion, never an
experiment. If you cannot build an approach, or the user asks you not to run
anything, say so, label the claim an *unverified assumption*, and offer to run
the real comparison.

| Thought | Reality |
|---|---|
| "We both know X is slower" / "I'll estimate it" | Then confirming is cheap. Build and measure it. |
| "I measured A; B is an assumption, still an experiment" | Half-measured is not an experiment. Measure B or retitle it. |
| "One run is enough" | One run is noise. Repeat and report the spread. |
| "B failed, leave it out" | Failures are data. Record what failed and why. |

Default mode: Collaborative (protocol: `ai-research-workflows:using-research-workflows`).

## When NOT to experiment

When the codebase already has a pattern (JWT everywhere), the decision is
low-risk, or being wrong is cheap, say **no experiment is needed** and follow
the pattern.

## Process

| Step | Do |
|---|---|
| 1. Context | No question given? Ask what to compare and why. Read related `docs/rse/specs/{research,plan}-*.md` (legacy `.agents/`) **completely**, or say they were not found. State the measurable question. |
| 2. Hypothesis | 2-3 **architecturally distinct** approaches ("JWT HS256 vs RS256" is a configuration difference, not an experiment), with success criteria for each. |
| 3. Isolate | Prototypes go in `.experiments/<slug>/` (or an `experiment-<slug>` branch on a clean tree), never in `src/`. |
| 4. Measure | Real commands, same input. Run each benchmark **several times and report the spread**, fix seeds, hold environment constant, record Python and library versions per `ai-research-workflows:ensuring-reproducibility`. |
| 5. Record | Successes and failures for every approach, with metrics and complexity. |
| 6. Recommend | Comparison matrix; recommendation citing measurements; why not the others; conditions where an alternative wins. |
| 7. Document | Copy `assets/experiment-template.md`, keep **every section heading** (Hypothesis, Comparison Matrix, Recommendation, Conditions...), fill each; save as `docs/rse/specs/experiment-<slug>.md`. |
| 8. Present | Brief summary; ask how to proceed. |

```bash
mkdir -p .experiments/<slug> && python .experiments/<slug>/bench.py
```

Read `references/running-the-comparison.md` before step 1 (context,
benchmarking, recording, cleanup) and `references/reporting.md` at step 7
(template, chat summary).

## Before you finish

- [ ] Every compared approach built and run; if not, the document is an unverified comparison, not an experiment
- [ ] Timings repeated with spread; seeds, input and environment fixed and recorded
- [ ] Failures recorded; prototype location stated in the document
- [ ] Document saved from the template; next: `ai-research-workflows:planning-implementations`
