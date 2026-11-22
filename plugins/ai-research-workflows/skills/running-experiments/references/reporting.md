# Reporting an experiment

Detail for steps 7-8 of `running-experiments`.

## The experiment document (step 7)

1. Derive a slug from the experiment question (lowercase, hyphenated).
2. Copy `assets/experiment-template.md` and keep its headings as they are
   (readers and tools look for them by name). Fill every section: goal,
   hypothesis, approaches, setup (environment with versions, test data,
   constraints), each experiment's code with its file path, the commands run
   and their output, observations (positive and negative), the comparison
   matrix, key insights, the recommendation, conditions for alternatives, and
   next steps.
3. Link the research and plan documents you read in Related Documents.
4. State where the prototype code lives (`.experiments/<slug>/` or the
   `experiment-<slug>` branch) under References, Code Files Tested.
5. Put verbose raw output in the appendix rather than dropping it.
6. Anything you could not build or run is written as an unverified assumption,
   never as a measured result. If any compared approach was not built and run,
   title the document "Unverified comparison: ..." instead of "Experiment: ...",
   set **Status:** to Incomplete, and say which approach is unmeasured.
7. Save to `docs/rse/specs/experiment-<slug>.md`, creating `docs/rse/specs/` if
   needed.

## The chat summary (step 8)

Keep it short and end by asking how to proceed. For an unverified comparison,
start with "Unverified comparison" instead of "Experiment Complete" and offer
to run the missing approach.

```
# Experiment Complete: [Topic]

Documented at `docs/rse/specs/experiment-[slug].md`.
Prototypes: `.experiments/[slug]/` (kept; say if you want them removed).

Approaches: [Approach 1] / [Approach 2] / [Approach 3]

Key findings: [2-3 bullets, with the measured numbers and their spread]

Recommendation: Use [Approach] because [primary reason].
Trade-offs accepted: [list]

Would you like to proceed, or explore further?
```

A chosen approach goes on to `ai-research-workflows:planning-implementations`
(or `ai-research-workflows:iterating-plans` when a plan already exists). To make
it reproducible, use `ai-research-workflows:ensuring-reproducibility`.
